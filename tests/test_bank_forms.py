"""Forms bypass language models but share the real graph, confirmation and ledger."""
import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from desktop.client import parse_stream
from test_api_http import chat, decision, login, result
from test_funds_chain import select
from test_api_transfer_retry import interrupt_once


def form(client, auth, action, **fields):
    response = client.post('/bank/form', headers=auth, json={'action': action, 'fields': fields})
    assert response.status_code == 200, response.text
    return parse_stream(response.content)


def confirm(client, auth, frames, choice='approve'):
    assert frames[-1][1]['status'] in {'AWAITING_CONFIRMATION', 'AWAITING_AUTHENTICATION'}
    signal = next(data for kind, data in frames if kind == 'interrupt')
    return decision(client, auth, frames[0][1]['thread_id'], signal, choice)


class UnavailableModel:
    def __init__(self):
        self.calls = 0
    def fail(self, *args, **kwargs):
        self.calls += 1
        raise RuntimeError('model unavailable')
    predict = complete_tools = phrase = fail
    def health(self):
        return False


def test_all_forms_work_without_any_model_and_ai_reads_same_ledger(tmp_path):
    model = UnavailableModel()
    path = tmp_path / 'forms.sqlite3'
    with TestClient(create_app(demo=True, candidate_model=model, query_model=model,
                              phraser=model, database_path=path), base_url='http://localhost') as c:
        auth = login(c)
        def write(action, **fields):
            return result(confirm(c, auth, form(c, auth, action, **fields)))
        account = write('OPEN_ACCOUNT', display_name='冻结「家用」账户')['data']['account_id']
        auth = select(c, auth, account)
        name = '冻结「家用」卡'  # Literal form value, never an instruction.
        assert write('ISSUE_DEBIT_CARD', display_name=name)['data']['status'] == 'PENDING_ACTIVATION'
        assert write('ACTIVATE_DEBIT_CARD', card_name=name)['data']['status'] == 'ACTIVE'
        payment = dict(card_name=name, merchant='商户「转账」', amount='12.30', category='购物')
        assert write('PAY_BY_CARD', **payment)['data']['remaining_balance_minor'] == 98770
        write('FREEZE_CARD', card_name=name)
        assert write('PAY_BY_CARD', **payment)['error_code'] == 'CARD_NOT_ACTIVE'
        write('UNFREEZE_CARD', card_name=name)
        write('SET_CARD_LIMITS', card_name=name, single_limit='10', daily_limit='20')
        assert result(form(c, auth, 'QUERY_CARD_LIMITS', card_name=name))['data']['used_today_minor'] == 1230
        assert write('PAY_BY_CARD', **payment)['error_code'] == 'CARD_SINGLE_LIMIT_EXCEEDED'
        assert write('TRANSFER', recipient_name='张伟', amount='40')['data']['remaining_balance_minor'] == 94770
        assert model.calls == 0
    with TestClient(create_app(demo=True, database_path=path), base_url='http://localhost') as c:
        auth = select(c, login(c), account)
        assert result(chat(c, auth, message='查询余额'))['data']['balance_minor'] == 94770
        bill = result(chat(c, auth, message='本月账单'))['data']
        assert bill['total_minor'] == 1230 and len(bill['transactions']) == 3


@pytest.mark.parametrize('entry', ['form', 'chat'])
def test_same_confirmation_cancel_binding_replay_and_balance(entry):
    with TestClient(create_app(demo=True), base_url='http://localhost') as c:
        auth = login(c)
        def request():
            return form(c, auth, 'TRANSFER', recipient_name='张伟', amount='40') if entry == 'form' else chat(c, auth, message='给张伟转40元')
        pending = request()
        assert c.get('/bank/accounts', headers=auth).json()['accounts'][0]['balance_minor'] == 500000
        assert confirm(c, auth, pending, 'reject')[-1][1]['status'] == 'REJECTED'
        pending = request()
        signal = next(d for e, d in pending if e == 'interrupt')
        thread = pending[0][1]['thread_id']
        assert c.post('/agent/chat', headers=auth, json={'thread_id': thread,
            'resume': {'challenge_id': signal['challenge_id'], 'decision': 'approve',
                       'params': {'amount_minor': 1}}}).status_code == 400
        assert c.post('/bank/form', headers=auth, json={'action': 'TRANSFER',
            'fields': {'recipient_name': '张伟', 'amount': '1'}}).status_code == 409
        paid = result(confirm(c, auth, pending))
        assert result(confirm(c, auth, pending)) == paid
        assert paid['data']['remaining_balance_minor'] == 496000
        assert result(chat(c, auth, message='查询余额'))['data']['balance_minor'] == 496000


@pytest.mark.parametrize('after_write', [False, True])
def test_form_uses_existing_failed_execution_recovery(monkeypatch, after_write):
    with TestClient(create_app(demo=True), base_url='http://localhost') as c:
        auth = login(c)
        pending = form(c, auth, 'TRANSFER', recipient_name='张伟', amount='40')
        attempts, _ = interrupt_once(monkeypatch, after_write=after_write)
        assert confirm(c, auth, pending)[-1][1]['status'] == 'FAILED'
        assert result(confirm(c, auth, pending))['data']['remaining_balance_minor'] == 496000
        assert attempts[0] == attempts[1]
        assert len([t for t in c.get('/bank/bills', headers=auth).json()['data']['transactions']
                    if t['kind'] == 'TRANSFER_OUT']) == 1


@pytest.mark.parametrize('body', [None, [], {}, {'action': 'DELETE_ALL', 'fields': {}},
    {'action': 'OPEN_ACCOUNT', 'fields': {'display_name': '账户', 'user_id': 'user-002'}},
    {'action': 'ACTIVATE_DEBIT_CARD', 'fields': {'card_id': 'card-003'}},
    {'action': 'OPEN_ACCOUNT', 'fields': {'display_name': '账户'}, 'authorized': True},
    {'action': 'OPEN_ACCOUNT', 'fields': {'display_name': ['账户']}},
    {'action': 'PAY_BY_CARD', 'fields': {'card_name': '卡', 'merchant': '商店', 'amount': 1.2}}])
def test_form_rejects_unknown_fields_or_trusted_identity(body):
    with TestClient(create_app(demo=True), base_url='http://localhost') as c:
        auth = login(c)
        assert c.post('/bank/form', headers=auth, json=body).status_code == 400
        assert c.get('/bank/accounts', headers=auth).json()['accounts'][0]['balance_minor'] == 500000


def test_form_red_risk_and_foreign_entities_cannot_bypass_authorization():
    with TestClient(create_app(demo=True), base_url='http://localhost') as c:
        auth = login(c)
        assert c.post('/bank/form', json={'action': 'OPEN_ACCOUNT', 'fields': {'display_name': '账户'}}).status_code == 401
        unknown = form(c, auth, 'PAY_BY_CARD', card_name='不存在的卡', merchant='商店', amount='1')
        assert not any(e == 'interrupt' for e, _ in unknown)
        pending = form(c, auth, 'TRANSFER', recipient_name='张伟', amount='3000')
        assert pending[-1][1]['status'] == 'AWAITING_AUTHENTICATION'
        signal = next(d for e, d in pending if e == 'interrupt')
        assert c.post('/agent/chat', headers=auth, json={'thread_id': pending[0][1]['thread_id'],
            'resume': {'challenge_id': signal['challenge_id'], 'decision': 'approve'}}).status_code == 409
        assert c.get('/bank/accounts', headers=auth).json()['accounts'][0]['balance_minor'] == 500000
