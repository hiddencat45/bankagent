import secrets
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from test_bank_forms import form, confirm
from test_api_http import result


def test_register_open_card_logout_and_restart(tmp_path):
    path = tmp_path / 'bank.sqlite3'
    password = secrets.token_urlsafe(24)
    def login(c):
        reply = c.post('/auth/login', json={'username':'alice', 'password':password})
        assert reply.status_code == 200, reply.text
        return {'Authorization': 'Bearer ' + reply.json()['token']}
    with TestClient(create_app(database_path=path, local_login=True), base_url='http://localhost') as c:
        assert c.post('/demo/session', json={}).status_code == 404
        assert c.get('/bank/accounts').status_code == 401
        assert c.post('/auth/register', json={'username':'alice', 'display_name':'张伟', 'password':password}).status_code == 200
        auth = login(c)
        assert c.get('/bank/accounts', headers=auth).json()['accounts'] == []
        pending = form(c, auth, 'OPEN_ACCOUNT', display_name='日常账户')
        opened = result(confirm(c, auth, pending))
        assert opened['status'] == 'COMPLETED', opened
        assert result(confirm(c, auth, pending)) == opened
        account = opened['data']['account_id']
        switched = c.post('/bank/account-session', headers=auth, json={'account_ref':account})
        auth = {'Authorization': 'Bearer ' + switched.json()['token']}
        for action, fields in [('ISSUE_DEBIT_CARD', {'display_name':'日常卡'}), ('ACTIVATE_DEBIT_CARD', {'card_name':'日常卡'})]:
            assert result(confirm(c, auth, form(c, auth, action, **fields)))['status'] == 'COMPLETED'
        result(confirm(c, auth, form(c, auth, 'OPEN_ACCOUNT', display_name='储蓄账户')))
        pending = form(c, auth, 'TRANSFER', recipient_name='储蓄账户', amount='30')
        signal = next(d for e, d in pending if e == 'interrupt')
        payload = {'thread_id':pending[0][1]['thread_id'], 'resume':{
            'challenge_id':signal['challenge_id'], 'decision':'approve'}}
        assert c.post('/agent/chat', headers=auth, json=payload).status_code == 409
        pin = f'{secrets.randbelow(1000000):06d}'
        assert c.post('/auth/payment-password', headers=auth, json={
            'login_password':password, 'payment_password':pin}).status_code == 200
        payload['resume']['otp'] = 'wrong'
        assert c.post('/agent/chat', headers=auth, json=payload).status_code == 401
        payload['resume']['otp'] = pin
        from desktop.client import parse_stream
        paid = result(parse_stream(c.post('/agent/chat', headers=auth, json=payload).content))
        assert paid['status'] == 'COMPLETED'
        assert result(parse_stream(c.post('/agent/chat', headers=auth, json=payload).content)) == paid
        assert c.post('/auth/logout', headers=auth, json={}).status_code == 200
        assert c.get('/bank/accounts', headers=auth).status_code == 401
    with TestClient(create_app(database_path=path, local_login=True), base_url='http://localhost') as c:
        auth = login(c)
        accounts = c.get('/bank/accounts', headers=auth).json()['accounts']
        assert len(accounts) == 2 and [a['balance_minor'] for a in accounts] == [97000, 103000]
        assert c.post('/bank/account-session', headers=auth, json={'account_ref':'account-002'}).status_code == 403
