"""Task 2: actual payment facts, network-failed model, cancellation and editing."""
import httpx
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from bankagent.agent.model_providers import OpenAICompatibleModel, ProviderConfig
from bankagent.agent.agent_phrasing import ResponsePhraser
from test_bank_forms import form, confirm
from test_api_http import chat, login, result


def test_payment_survives_model_connection_failure_and_old_confirmation_is_dead(tmp_path):
    attempts = []
    def disconnected(request):
        attempts.append(True)
        raise httpx.ConnectError('offline', request=request)
    model = OpenAICompatibleModel(ProviderConfig(api_key='test-only-placeholder'),
                                  transport=httpx.MockTransport(disconnected))
    path = tmp_path / 'payment.sqlite3'
    with TestClient(create_app(demo=True, database_path=path, candidate_model=model,
                              query_model=model, phraser=ResponsePhraser(model)), base_url='http://localhost') as c:
        auth = login(c)
        assert chat(c, auth, message='查询余额')[-1][1]['status'] == 'FAILED'
        assert attempts
        failures = len(attempts)
        opened = result(confirm(c, auth, form(c, auth, 'OPEN_ACCOUNT', display_name='消费账户')))
        account = opened['data']['account_id']
        switched = c.post('/bank/account-session', headers=auth, json={'account_ref':account})
        auth = {'Authorization':'Bearer ' + switched.json()['token']}
        name = '冻结转账卡'
        for action, fields in [('ISSUE_DEBIT_CARD', {'display_name': name}),
                               ('ACTIVATE_DEBIT_CARD', {'card_name': name})]:
            assert result(confirm(c, auth, form(c, auth, action, **fields)))['status'] == 'COMPLETED'
        payment = dict(card_name=name, merchant='转账冻结商店', amount='12.30', category='购物')
        old = form(c, auth, 'PAY_BY_CARD', **payment)
        assert c.get('/bank/accounts', headers=auth).json()['accounts'][-1]['balance_minor'] == 100000
        assert confirm(c, auth, old, 'reject')[-1][1]['status'] == 'REJECTED'
        payment['amount'] = '8.50'
        changed = form(c, auth, 'PAY_BY_CARD', **payment)
        signal = next(d for e, d in old if e == 'interrupt')
        assert c.post('/agent/chat', headers=auth, json={'thread_id': old[0][1]['thread_id'],
            'resume': {'challenge_id': signal['challenge_id'], 'decision': 'approve'}}).status_code == 409
        paid = result(confirm(c, auth, changed))
        assert paid['data']['remaining_balance_minor'] == 99150
        assert result(confirm(c, auth, changed)) == paid
        rows = c.get('/bank/bills', headers=auth).json()['data']['transactions']
        payments = [r for r in rows if r['merchant'] == payment['merchant']]
        assert len(payments) == 1 and payments[0]['amount_minor'] == 850
        assert len(attempts) == failures  # No model call in prepare/cancel/execute/replay.
    with TestClient(create_app(demo=True, database_path=path), base_url='http://localhost') as c:
        auth = login(c)
        switched = c.post('/bank/account-session', headers=auth, json={'account_ref':account})
        auth = {'Authorization':'Bearer ' + switched.json()['token']}
        assert result(chat(c, auth, message='查询余额'))['data']['balance_minor'] == 99150
        assert result(chat(c, auth, message='本月账单'))['data'] == c.get('/bank/bills', headers=auth).json()['data']
