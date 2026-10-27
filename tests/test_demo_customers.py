"""Public fixed-choice demo switching, never arbitrary trusted identity input."""
import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from test_api_http import chat, decision, login, result
from test_lifecycle_api import submit


def switch(client, auth, reference):
    response = client.post('/demo/customer-session', headers=auth, json={'customer_ref': reference})
    assert response.status_code == 200, response.text
    return {'Authorization': 'Bearer ' + response.json()['token']}


def test_transfer_switch_receive_return_and_reopen(tmp_path):
    path = tmp_path / 'demo.sqlite3'
    for first in (True, False):
        with TestClient(create_app(demo=True, database_path=path), base_url='http://localhost') as client:
            auth = login(client)
            independent = login(client)
            menu = client.get('/demo/customers', headers=auth).json()
            assert menu['current_customer_ref'] == 'primary'
            assert {r['customer_ref'] for r in menu['customers']} == {'primary', 'zhang-wei'}
            assert 'user_id' not in str(menu) and 'account_id' not in str(menu)
            if first:
                transfer = result(submit(client, auth, '给张伟转40元'))
                transfer_id = transfer['data']['transfer_id']
            old_thread = chat(client, auth, message='查询余额')[0][1]['thread_id']
            # Keep the previous account-session token to verify the entire lineage is revoked.
            account_auth = {'Authorization': 'Bearer ' + client.post('/bank/account-session',
                headers=auth, json={'account_ref': 'account-001'}).json()['token']}
            receiver = switch(client, account_auth, 'zhang-wei')
            for old in (auth, account_auth):
                assert client.get('/bank/accounts', headers=old).status_code == 401
                assert client.get('/bank/bills', headers=old).status_code == 401
            assert client.get('/bank/accounts', headers=independent).status_code == 200
            assert client.post('/agent/chat', headers=receiver,
                json={'thread_id': old_thread, 'message': '查询余额'}).status_code == 404
            assert result(chat(client, receiver, message='查询余额'))['data']['balance_minor'] == 44000
            bill = result(chat(client, receiver, message='本月账单'))['data']
            assert client.get('/bank/bills', headers=receiver).json()['data'] == bill
            incoming = next(t for t in bill['transactions'] if t['kind'] == 'TRANSFER_IN')
            assert incoming['transfer_id'] == transfer_id and incoming['amount_minor'] == 4000
            assert bill['total_minor'] == 0
            assert client.post('/bank/account-session', headers=receiver,
                json={'account_ref': 'account-001'}).status_code == 403
            restored = switch(client, receiver, 'primary')
            assert client.get('/bank/accounts', headers=receiver).status_code == 401
            assert result(chat(client, restored, message='查询余额'))['data']['balance_minor'] == 496000


def test_pending_in_earlier_account_session_blocks_switch():
    with TestClient(create_app(demo=True), base_url='http://localhost') as client:
        auth = login(client)
        other = {'Authorization': 'Bearer ' + client.post('/bank/account-session', headers=auth,
            json={'account_ref': 'account-001'}).json()['token']}
        pending = chat(client, auth, message='给张伟转40元')
        assert client.post('/demo/customer-session', headers=other,
            json={'customer_ref': 'zhang-wei'}).status_code == 409
        signal = next(data for kind, data in pending if kind == 'interrupt')
        decision(client, auth, pending[0][1]['thread_id'], signal, 'reject')
        receiver = switch(client, other, 'zhang-wei')
        assert result(chat(client, receiver, message='查询余额'))['data']['balance_minor'] == 40000
        assert client.post('/agent/chat', headers=receiver, json={
            'thread_id': pending[0][1]['thread_id'], 'resume': {
                'challenge_id': signal['challenge_id'], 'decision': 'approve'}}).status_code == 404


@pytest.mark.parametrize('payload', [None, [], {}, {'user_id': 'user-002'},
    {'customer_ref': 'user-002'}, {'customer_ref': 'missing'}, {'customer_ref': []},
    {'customer_ref': 'zhang-wei', 'user_id': 'user-001'},
    {'customer_ref': 'zhang-wei', 'account_id': 'account-001'}])
def test_switch_rejects_identity_injection(payload):
    with TestClient(create_app(demo=True), base_url='http://localhost') as client:
        auth = login(client)
        assert client.post('/demo/customer-session', headers=auth, json=payload).status_code == 400
        assert client.get('/demo/customers', headers=auth).json()['current_customer_ref'] == 'primary'


@pytest.mark.parametrize('demo,remote', [(False, False), (True, True)])
def test_customer_routes_are_local_demo_only(demo, remote):
    with TestClient(create_app(demo=demo, allow_lan=True), base_url='http://localhost',
                    client=('192.0.2.1' if remote else 'testclient', 123)) as client:
        assert client.get('/demo/customers').status_code == 404
        assert client.post('/demo/customer-session', json={'customer_ref': 'primary'}).status_code == 404


def test_customer_routes_require_session_and_available_target(monkeypatch):
    with TestClient(create_app(demo=True), base_url='http://localhost') as client:
        assert client.get('/demo/customers').status_code == 401
        assert client.post('/demo/customer-session', json={'customer_ref': 'primary'}).status_code == 401
        auth = login(client)
        monkeypatch.setattr('bankagent.api.server.get_balance', lambda **kw: {'status': 'REJECTED'})
        assert client.post('/demo/customer-session', headers=auth,
            json={'customer_ref': 'zhang-wei'}).status_code == 403
        assert client.get('/demo/customers', headers=auth).json()['current_customer_ref'] == 'primary'
