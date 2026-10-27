from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from test_api_http import chat, decision, login, result


def submit(client, auth, message, approve=True):
    frames = chat(client, auth, message=message)
    assert frames[-1][1]['status'] == 'AWAITING_CONFIRMATION', frames
    signal = next(data for kind, data in frames if kind == 'interrupt')
    return decision(client, auth, frames[0][1]['thread_id'], signal, 'approve' if approve else 'reject')


def test_account_session_lifecycle(tmp_path):
    with TestClient(create_app(demo=True, database_path=tmp_path / 'bank.sqlite3'), base_url='http://localhost') as c:
        auth = login(c)
        assert len(c.get('/bank/accounts', headers=auth).json()['accounts']) == 1
        assert submit(c, auth, '开户「测试账户」', False)[-1][1]['status'] == 'REJECTED'
        assert len(c.get('/bank/accounts', headers=auth).json()['accounts']) == 1
        opened = result(submit(c, auth, '开户「消费账户」'))
        assert opened['status'] == 'COMPLETED'
        ref = opened['data']['account_id']
        assert c.post('/bank/account-session', headers=auth, json={'account_ref': 'account-002'}).status_code == 403
        switched = c.post('/bank/account-session', headers=auth, json={'account_ref': ref})
        assert switched.status_code == 200
        auth2 = {'Authorization': 'Bearer ' + switched.json()['token']}
        assert result(chat(c, auth2, message='查询余额'))['data']['balance_minor'] == 100000
        assert result(submit(c, auth2, '办理借记卡「生活卡」'))['data']['status'] == 'PENDING_ACTIVATION'
        assert chat(c, auth2, message='解冻生活卡')[-1][1]['status'] == 'REJECTED'
        assert result(submit(c, auth2, '激活「生活卡」'))['data']['status'] == 'ACTIVE'
        payment = '使用「生活卡」在商户「演示超市」刷卡支付12.30元，分类「购物」'
        assert result(submit(c, auth2, payment))['data']['remaining_balance_minor'] == 98770
        submit(c, auth2, '冻结生活卡')
        assert result(submit(c, auth2, payment))['error_code'] == 'CARD_NOT_ACTIVE'
        submit(c, auth2, '解冻生活卡')
        assert result(submit(c, auth2, payment))['data']['remaining_balance_minor'] == 97540
        assert result(chat(c, auth, message='查询余额'))['data']['balance_minor'] == 500000


def test_account_switch_rejects_pending_and_foreign_thread():
    with TestClient(create_app(demo=True), base_url='http://localhost') as c:
        auth = login(c)
        frames = chat(c, auth, message='开户「新账户」')
        switch = lambda: c.post('/bank/account-session', headers=auth, json={'account_ref': 'account-001'})
        assert switch().status_code == 409
        signal = next(data for kind, data in frames if kind == 'interrupt')
        decision(c, auth, frames[0][1]['thread_id'], signal, 'reject')
        auth2 = {'Authorization': 'Bearer ' + switch().json()['token']}
        assert c.post('/agent/chat', headers=auth2, json={'thread_id': frames[0][1]['thread_id'],
            'message': '查询余额'}).status_code == 404
        assert c.get('/bank/accounts').status_code == 401


def test_invalid_payment_and_account_selection_cannot_write():
    with TestClient(create_app(demo=True), base_url='http://localhost') as c:
        auth = login(c)
        for message in ['使用「日常消费卡」在商户「商店」刷卡支付1.234元',
                        '激活「不存在的卡」', '不要开户「新账户」']:
            out = chat(c, auth, message=message)
            assert out[-1][1]['status'] in {'REJECTED', 'NEEDS_CLARIFICATION'}
            assert not any(e == 'interrupt' for e, _ in out)
        for body in ({'account_ref': 'account-001', 'user_id': 'user-002'}, {'account_ref': None}, []):
            assert c.post('/bank/account-session', headers=auth, json=body).status_code == 400
        assert result(chat(c, auth, message='查询余额'))['data']['balance_minor'] == 500000


def test_bilateral_transfer_and_limits_through_agent(tmp_path):
    with TestClient(create_app(demo=True, database_path=tmp_path / 'bank.sqlite3'), base_url='http://localhost') as c:
        auth = login(c)
        submit(c, auth, '给张伟转40元')
        # Receiver identity is issued only by this trusted test harness, not public input.
        receiver = c.app.state.service.sessions.issue(user_id='user-002', account_id='account-002')
        receiver_auth = {'Authorization': 'Bearer ' + receiver.token}
        assert result(chat(c, receiver_auth, message='查询余额'))['data']['balance_minor'] == 44000
        bill = result(chat(c, receiver_auth, message='本月账单'))['data']
        assert bill['total_minor'] == 0 and any(t['kind'] == 'TRANSFER_IN' for t in bill['transactions'])
        own = result(submit(c, auth, '开户「储蓄账户」'))['data']['account_id']
        submit(c, auth, '给储蓄账户转50元')
        row = next(a for a in c.get('/bank/accounts', headers=auth).json()['accounts'] if a['account_ref'] == own)
        assert row['balance_minor'] == 105000
        assert submit(c, auth, '设置限额「日常消费卡」单笔10元，每日20元', False)[-1][1]['status'] == 'REJECTED'
        assert result(chat(c, auth, message='查询限额「日常消费卡」'))['data']['single_limit_minor'] == 500000
        submit(c, auth, '设置限额「日常消费卡」单笔10元，每日20元')
        pay = result(submit(c, auth, '使用「日常消费卡」在商户「商店」刷卡支付11元'))
        assert pay['error_code'] == 'CARD_SINGLE_LIMIT_EXCEEDED'
