"""Complete ledger flow with real graph/SQLite; no provider or personal ledger."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from desktop.client import query_result
from test_api_http import chat, decision, login, result
from test_lifecycle_api import submit


def select(client, auth, account):
    response = client.post('/bank/account-session', headers=auth, json={'account_ref': account})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['token']}


def receiver_session(client):
    # Test-only trusted issuer. This is NOT a public demo identity switch.
    session = client.app.state.service.sessions.issue(user_id='user-002', account_id='account-002')
    return {'Authorization': 'Bearer ' + session.token}


def test_complete_funds_chain_and_service_restart(tmp_path):
    path = tmp_path / 'chain.sqlite3'
    def service():
        return TestClient(create_app(demo=True, database_path=path), base_url='http://localhost')
    def balance(client, auth):
        return result(chat(client, auth, message='查询余额'))['data']['balance_minor']
    def bills(client, auth):
        return result(chat(client, auth, message='本月账单'))
    def used(client, auth):
        return result(chat(client, auth, message='查询限额「链路卡」'))['data']['used_today_minor']
    def pay(client, auth, amount):
        return result(submit(client, auth, f'使用「链路卡」在商户「演示超市」刷卡支付{amount}元，分类「购物」'))

    with service() as client:
        primary = login(client)
        account = result(submit(client, primary, '开户「链路账户」'))['data']['account_id']
        sender = select(client, primary, account)
        receiver = receiver_session(client)
        assert balance(client, sender) == 100000
        assert balance(client, receiver) == 40000
        issued = result(submit(client, sender, '办理借记卡「链路卡」'))
        assert issued['data']['status'] == 'PENDING_ACTIVATION'
        assert pay(client, sender, '60')['error_code'] == 'CARD_NOT_ACTIVE'
        assert balance(client, sender) == 100000
        submit(client, sender, '激活「链路卡」')
        submit(client, sender, '设置限额「链路卡」单笔60元，每日100元')
        assert pay(client, sender, '60.01')['error_code'] == 'CARD_SINGLE_LIMIT_EXCEEDED'
        assert pay(client, sender, '60')['data']['remaining_balance_minor'] == 94000
        submit(client, sender, '冻结链路卡')
        assert pay(client, sender, '1')['error_code'] == 'CARD_NOT_ACTIVE'
        assert used(client, sender) == 6000
        # Frozen card does not freeze the account; transfer cannot consume card quota.
        frames = chat(client, sender, message='给张伟转40元')
        assert balance(client, receiver) == 40000  # Still awaiting confirmation.
        signal = next(data for kind, data in frames if kind == 'interrupt')
        thread = frames[0][1]['thread_id']
        transferred = result(decision(client, sender, thread, signal))
        assert transferred['status'] == 'COMPLETED'
        assert result(decision(client, sender, thread, signal)) == transferred
        assert balance(client, sender) == 90000
        assert balance(client, receiver) == 44000
        assert used(client, sender) == 6000
        submit(client, sender, '解冻链路卡')
        assert used(client, sender) == 6000
        assert pay(client, sender, '40.01')['error_code'] == 'CARD_DAILY_LIMIT_EXCEEDED'
        assert pay(client, sender, '40')['data']['remaining_balance_minor'] == 86000
        assert used(client, sender) == 10000
        assert pay(client, sender, '0.01')['error_code'] == 'CARD_DAILY_LIMIT_EXCEEDED'
        sender_bill, receiver_bill = bills(client, sender), bills(client, receiver)
        assert sender_bill['data']['total_minor'] == 10000
        assert receiver_bill['data']['total_minor'] == 0
        outgoing = next(t for t in sender_bill['data']['transactions'] if t['kind'] == 'TRANSFER_OUT')
        incoming = next(t for t in receiver_bill['data']['transactions'] if t['kind'] == 'TRANSFER_IN')
        assert outgoing['transfer_id'] == incoming['transfer_id'] == transferred['data']['transfer_id']
        assert outgoing['related_transaction_id'] == incoming['transaction_id']
        assert incoming['related_transaction_id'] == outgoing['transaction_id']
        assert outgoing['amount_minor'] == incoming['amount_minor'] == 4000
        assert outgoing['transfer_id'] in query_result(sender_bill)
        assert incoming['transaction_id'] in query_result(sender_bill)
        assert 'counterparty_account_id' not in outgoing
        assert len(sender_bill['data']['transactions']) == 4  # opening, two payments, one transfer
        assert balance(client, primary) == 500000
        for payload in ({'user_id': 'user-002'}, {'customer_id': 'user-002'}):
            assert client.post('/demo/session', json=payload).status_code == 400
        assert client.post('/bank/account-session', headers=sender,
                           json={'account_ref': 'account-002'}).status_code == 403

    with service() as client:
        sender = select(client, login(client), account)
        receiver = receiver_session(client)
        assert balance(client, sender) == 86000
        assert balance(client, receiver) == 44000
        assert used(client, sender) == 10000
        assert bills(client, sender) == sender_bill
        assert bills(client, receiver) == receiver_bill
        assert client.get('/bank/accounts', headers=primary).status_code == 401

    # A fresh interpreter also reads the same ledger, not a cached service state.
    script = '''
import json, sys
from datetime import date
from bankagent.banking.bank_backend import BankBackend
from bankagent.banking.bank_types import TrustedContext
from bankagent.banking.data.generator import build_demo_data
b = BankBackend(data_factory=build_demo_data, database_path=sys.argv[1])
rows = []
for user, account in [('user-001', sys.argv[2]), ('user-002', 'account-002')]:
    ctx = TrustedContext(user, account, 'reopen')
    rows.append([b.get_balance(context=ctx)['data']['balance_minor'],
        b.query_bills(context=ctx, start=date(2026,10,1), end=date(2026,11,1))['data']])
print(json.dumps(rows))
'''
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')}
    reopened = subprocess.run([sys.executable, '-c', script, str(path), account],
                              env=env, capture_output=True, text=True, timeout=20, check=True)
    assert json.loads(reopened.stdout) == [[86000, sender_bill['data']], [44000, receiver_bill['data']]]


def test_old_transactions_have_no_invented_links():
    with TestClient(create_app(demo=True), base_url='http://localhost') as client:
        bill = result(chat(client, login(client), message='本月账单'))
        original = deepcopy(bill)
        assert all('transfer_id' not in row for row in bill['data']['transactions'])
        assert '关联流水' not in query_result(bill)
        assert bill == original
