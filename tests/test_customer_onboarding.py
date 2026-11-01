"""New fictional identity and first account commit together under existing confirmation."""
import sqlite3
import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from bankagent.banking import bank_backend as bank
from bankagent.agent.scenarios import REGISTRY
from test_api_http import login, result, chat
from test_bank_forms import form, confirm, UnavailableModel
from test_demo_customers import switch


def customers(c, auth):
    return c.get('/demo/customers', headers=auth).json()['customers']


def new_customer(c, auth):
    return form(c, auth, 'CREATE_DEMO_CUSTOMER', customer_name='小林', account_name='首账户')


def test_create_first_account_issue_activate_and_restart(tmp_path):
    path = tmp_path / 'onboarding.sqlite3'
    model = UnavailableModel()
    with TestClient(create_app(demo=True, database_path=path, candidate_model=model,
                              query_model=model, phraser=model), base_url='http://localhost') as c:
        auth = login(c)
        pending = new_customer(c, auth)
        assert len(customers(c, auth)) == 2
        card = next(d['payload'] for e, d in pending if e == 'card' and d['type'] == 'confirm')
        assert (card['display_name'], card['account_name'], card['opening_credit_minor']) == ('小林', '首账户', 0)
        assert confirm(c, auth, pending, 'reject')[-1][1]['status'] == 'REJECTED'
        assert len(customers(c, auth)) == 2
        pending = new_customer(c, auth)
        created = result(confirm(c, auth, pending))
        assert result(confirm(c, auth, pending)) == created
        ref, account = created['data']['customer_ref'], created['data']['account_id']
        assert len(customers(c, auth)) == 3
        assert c.get('/bank/accounts', headers=auth).json()['accounts'][0]['balance_minor'] == 500000
        assert c.post('/bank/account-session', headers=auth, json={'account_ref': account}).status_code == 403
        selected = switch(c, auth, ref)
        assert c.get('/bank/accounts', headers=selected).json()['accounts'] == [
            {'account_ref': account, 'display_name': '首账户', 'balance_minor': 0, 'currency': 'CNY', 'transfer_card': None}]
        def write(action, **fields):
            return result(confirm(c, selected, form(c, selected, action, **fields)))
        issued = write('ISSUE_DEBIT_CARD', display_name='首卡')
        assert issued['data']['status'] == 'PENDING_ACTIVATION'
        payment = dict(card_name='首卡', merchant='演示商店', amount='1', category='购物')
        assert write('PAY_BY_CARD', **payment)['error_code'] == 'CARD_NOT_ACTIVE'
        assert write('ACTIVATE_DEBIT_CARD', card_name='首卡')['data']['status'] == 'ACTIVE'
        assert write('SIMULATE_CARD_DEPOSIT', card_name='首卡', amount='1000')['status'] == 'COMPLETED'
        assert write('PAY_BY_CARD', **payment)['data']['remaining_balance_minor'] == 99900
        assert model.calls == 0
    with TestClient(create_app(demo=True, database_path=path), base_url='http://localhost') as c:
        auth = login(c)
        selected = switch(c, auth, ref)
        assert result(chat(c, selected, message='查询余额'))['data']['balance_minor'] == 99900
        cards = result(chat(c, selected, message='我的卡片'))['data']['cards']
        assert cards[0]['card_id'] == issued['data']['card_id'] and cards[0]['status'] == 'ACTIVE'
        rows = c.get('/bank/bills', headers=selected).json()['data']['transactions']
        assert len(rows) == 2 and sum(t['amount_minor'] for t in rows if t['kind'] == 'INCOME') == 100000
        restored = switch(c, selected, 'primary')
        assert result(chat(c, restored, message='查询余额'))['data']['balance_minor'] == 500000


@pytest.mark.parametrize('after_commit', [False, True])
def test_creation_failure_retry_keeps_one_customer_account_and_credit(tmp_path, monkeypatch, after_commit):
    with TestClient(create_app(demo=True, database_path=tmp_path / 'retry.sqlite3'), base_url='http://localhost') as c:
        auth = login(c)
        pending = new_customer(c, auth)
        if after_commit:
            owner, name = REGISTRY.get('onboarding'), 'execute'
        else:
            owner, name = bank._configured()._store, 'save'
        original, attempts = getattr(owner, name), []
        def fail_once(*args, **kwargs):
            reply = original(*args, **kwargs)
            attempts.append(True)
            if len(attempts) == 1:
                raise sqlite3.OperationalError('injected failure')
            return reply
        monkeypatch.setattr(owner, name, fail_once)
        assert confirm(c, auth, pending)[-1][1]['status'] == 'FAILED'
        assert len(customers(c, auth)) == (3 if after_commit else 2)
        completed = result(confirm(c, auth, pending))
        assert completed['status'] == 'COMPLETED'
        assert result(confirm(c, auth, pending)) == completed
        assert len(customers(c, auth)) == 3
        selected = switch(c, auth, completed['data']['customer_ref'])
        assert len(c.get('/bank/bills', headers=selected).json()['data']['transactions']) == 0


@pytest.mark.parametrize('demo,lan', [(False, False), (True, True)])
def test_creation_disabled_outside_local_demo(demo, lan):
    with TestClient(create_app(demo=demo, allow_lan=lan), base_url='http://localhost') as c:
        session = c.app.state.service.sessions.issue(user_id='user-001', account_id='account-001')
        auth = {'Authorization': 'Bearer ' + session.token}
        assert result(confirm(c, auth, new_customer(c, auth)))['error_code'] == 'DEMO_CREATION_DISABLED'
        assert bank.demo_customer_choices() == {}


def test_creation_cannot_accept_identity_or_create_without_authorization():
    with TestClient(create_app(demo=True), base_url='http://localhost') as c:
        auth = login(c)
        body = {'action': 'CREATE_DEMO_CUSTOMER', 'fields': {'customer_name': '小林', 'account_name': '首账户'}}
        for key in ('user_id', 'customer_ref', 'account_id', 'balance_minor'):
            assert c.post('/bank/form', headers=auth, json={**body,
                'fields': {**body['fields'], key: 'forged'}}).status_code == 400
        from bankagent.banking.bank_types import TrustedContext
        denied = bank.create_demo_customer(context=TrustedContext('user-001', 'account-001', 'r'),
                                          customer_name='小林', account_name='首账户')
        assert denied['error_code'] == 'AUTHORIZATION_REQUIRED'
        assert len(customers(c, auth)) == 2
