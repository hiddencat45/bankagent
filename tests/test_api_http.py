"""HTTP 层使用真实主图/内存账本；不以假银行结果替代集成。"""
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from bankagent.agent.agent_security import SG_TZ


@pytest.fixture
def client(monkeypatch):
    from bankagent.agent.scenarios import bills
    monkeypatch.setattr(bills, '_clock', bills._clock)
    app = create_app(demo=True, clock=lambda: datetime(2026, 10, 18, 12, tzinfo=SG_TZ))
    with TestClient(app, base_url='http://localhost') as c:
        yield c


def login(c):
    r = c.post('/demo/session')
    assert r.status_code == 200
    return {'Authorization': 'Bearer ' + r.json()['token']}


def chat(c, auth, **payload):
    response = c.post('/agent/chat', headers=auth, json=payload)
    assert response.status_code == 200, response.text
    assert response.headers['content-type'].startswith('text/event-stream')
    out = []
    for frame in response.text.strip().split('\n\n'):
        name, data = frame.split('\n')
        out.append((name.removeprefix('event: '), json.loads(data.removeprefix('data: '))))
    assert out[0][0] == 'status'
    assert out[-1][0] == 'done'
    for _, data in out:
        assert {k: data[k] for k in ('thread_id', 'request_id', 'mode')} == {
            k: out[0][1][k] for k in ('thread_id', 'request_id', 'mode')}
    return out


def confirmation(c, auth, amount=300):
    out = chat(c, auth, message=f'给张伟转 {amount} 元')
    card = next(data for name, data in out if name == 'card' and data['type'] == 'confirm')
    intr = next(data for name, data in out if name == 'interrupt')
    assert intr['challenge_id'] == card['payload']['challenge_id']
    assert card['payload']['recipient'] == '张伟'
    assert card['payload']['amount_minor'] == amount * 100
    return out[0][1]['thread_id'], intr


def decision(c, auth, thread, intr, value='approve', **extra):
    return chat(c, auth, thread_id=thread, resume={'challenge_id': intr['challenge_id'], 'decision': value, **extra})


def result(out):
    return next(data['payload'] for name, data in out if name == 'card' and data['type'] == 'result')


def test_read_balance_and_bills_have_actual_results(client):
    auth = login(client)
    out = chat(client, auth, message='查询余额')
    assert result(out)['data'] == {'balance_minor': 500000, 'currency': 'CNY'}
    assert 'daily_transfer_total_minor' not in repr(out)
    out = chat(client, auth, message='本月账单')
    evidence = next(data['payload']['data'] for name, data in out if name == 'card' and data['type'] == 'evidence')
    assert evidence['total_minor'] == 100000
    assert evidence['anomalies'][0]['evidence'] == ['txn-005', 'txn-006']


def test_transfer_confirm_replay_and_balance(client):
    auth = login(client)
    thread, intr = confirmation(client, auth)
    assert result(chat(client, auth, message='余额'))['data']['balance_minor'] == 500000
    out = decision(client, auth, thread, intr)
    assert out[0][1]['request_id'] == intr['request_id']
    assert result(out)['data']['remaining_balance_minor'] == 470000
    replay = decision(client, auth, thread, intr)
    assert result(replay) == result(out)
    assert result(chat(client, auth, message='余额'))['data']['balance_minor'] == 470000
    denied = client.post('/agent/chat', headers=auth, json={'thread_id': thread, 'resume': {'challenge_id': intr['challenge_id'], 'decision': 'reject'}})
    assert denied.status_code == 409
    assert denied.json()['code'] == 'CHALLENGE_INVALID'


def test_reject_and_red_auth_fail_closed(client):
    auth = login(client)
    thread, intr = confirmation(client, auth)
    out = decision(client, auth, thread, intr, 'reject')
    assert result(out)['error_code'] == 'USER_CANCELLED'
    thread, intr = confirmation(client, auth, 1500)
    assert intr['kind'] == 'STRONG_AUTH'
    denied = client.post('/agent/chat', headers=auth, json={'thread_id': thread, 'resume': {'challenge_id': intr['challenge_id'], 'decision': 'approve'}})
    assert denied.status_code == 409
    assert result(chat(client, auth, message='余额'))['data']['balance_minor'] == 500000
    assert result(decision(client, auth, thread, intr, 'reject'))['error_code'] == 'USER_CANCELLED'


def test_no_cross_session_resume_or_busy_replacement(client):
    auth = login(client)
    thread, intr = confirmation(client, auth)
    busy = client.post('/agent/chat', headers=auth, json={'thread_id': thread, 'message': '余额'})
    assert busy.status_code == 409
    outsider = login(client)
    r = client.post('/agent/chat', headers=outsider, json={'thread_id': thread, 'resume': {'challenge_id': intr['challenge_id'], 'decision': 'approve'}})
    assert r.status_code == 404
    assert result(decision(client, auth, thread, intr))['data']['remaining_balance_minor'] == 470000


def test_reset_invalidates_all_old_credentials_and_state(client):
    auth = login(client)
    thread, intr = confirmation(client, auth)
    assert client.post('/demo/reset', headers=auth).json() == {'status': 'COMPLETED'}
    r = client.post('/agent/chat', headers=auth, json={'thread_id': thread, 'resume': {'challenge_id': intr['challenge_id'], 'decision': 'approve'}})
    assert r.status_code == 401
    fresh = login(client)
    r = client.post('/agent/chat', headers=fresh, json={'thread_id': thread, 'message': '余额'})
    assert r.status_code == 404
    assert result(chat(client, fresh, message='余额'))['data']['balance_minor'] == 500000


@pytest.mark.parametrize('payload, code', [
    ({'message': '余额', 'authorized': True}, 'UNTRUSTED_FIELD'),
    ({'resume': {'challenge_id': 'x', 'decision': []}}, 'INVALID_REQUEST'),
    ({'resume': {'challenge_id': 'x', 'decision': 'approve'}}, 'INVALID_REQUEST'),
])
def test_invalid_request_is_json_before_stream(client, payload, code):
    r = client.post('/agent/chat', headers=login(client), json=payload)
    assert r.status_code == 400
    assert r.json()['code'] == code
    assert r.headers['content-type'].startswith('application/json')


def test_health_checks_backend_and_local_session_guards(client, monkeypatch):
    assert client.get('/health').json() == {'status': 'ok', 'mode': 'offline', 'backend': 'ok', 'model': 'not_configured'}
    monkeypatch.setattr('bankagent.api.server.get_balance', lambda **kw: (_ for _ in ()).throw(RuntimeError('private detail')))
    r = client.get('/health')
    assert r.json()['status'] == 'degraded'
    assert 'private detail' not in r.text
    assert client.post('/demo/session', headers={'Origin': 'https://other.example'}).status_code == 403
    assert client.post('/demo/session', json={'user_id': 'other'}).status_code == 400
    with TestClient(create_app(), base_url='http://localhost') as disabled:
        assert disabled.post('/demo/session').status_code == 404


def test_stream_failure_is_sanitized_and_releases_run(client, monkeypatch):
    from bankagent.agent.scenarios import REGISTRY
    def broken(*args, **kwargs):
        raise RuntimeError('private detail')
    auth = login(client)
    monkeypatch.setattr(REGISTRY.get('bills'), 'execute', broken)
    out = chat(client, auth, message='本月账单')
    assert any(name == 'error' for name, _ in out)
    assert out[-1][1]['status'] == 'FAILED'
    assert 'private detail' not in repr(out)
    assert result(chat(client, auth, message='余额'))['data']['balance_minor'] == 500000


def test_busy_service_rejects_reset_and_request(client):
    auth = login(client)
    gate = client.app.state.service.running
    gate.acquire()
    try:
        assert client.post('/agent/chat', headers=auth, json={'message': '余额'}).status_code == 409
        assert client.post('/demo/reset', headers=auth).status_code == 409
    finally:
        gate.release()


def test_expired_challenge_and_tampered_params_cannot_resume(client):
    auth = login(client)
    service = client.app.state.service
    thread, intr = confirmation(client, auth)
    cfg = {'configurable': {'thread_id': thread}}
    state = service.graph.get_state(cfg).values
    service.graph.update_state(cfg, {'params': {**state['params'], 'amount_minor': 30100}})
    r = client.post('/agent/chat', headers=auth, json={'thread_id': thread, 'resume': {'challenge_id': intr['challenge_id'], 'decision': 'approve'}})
    assert r.status_code == 409
    assert r.json()['code'] == 'CHALLENGE_STATE_MISMATCH'
    service.graph.update_state(cfg, {'params': state['params']})
    old_clock = service.clock
    service.challenges._clock = lambda: old_clock() + timedelta(minutes=6)
    r = client.post('/agent/chat', headers=auth, json={'thread_id': thread, 'resume': {'challenge_id': intr['challenge_id'], 'decision': 'approve'}})
    assert r.status_code == 409
    assert result(chat(client, auth, message='余额'))['data']['balance_minor'] == 500000


def test_authentication_input_never_enters_checkpoint(client):
    import secrets
    auth = login(client)
    thread, intr = confirmation(client, auth, 1500)
    service = client.app.state.service
    transient = secrets.token_urlsafe(24)
    service.demo_verification_enabled = False
    service.authenticate = lambda context, value: value == transient and context.request_id == intr['request_id']
    out = decision(client, auth, thread, intr, otp=transient)
    assert result(out)['data']['remaining_balance_minor'] == 350000
    history = repr(list(service.graph.get_state_history({'configurable': {'thread_id': thread}})))
    assert transient not in history
    assert transient not in repr(out)
    assert 'authorization_ref' not in history
    assert 'idempotency_key' not in history


def test_resume_after_graph_failure_keeps_same_authorization(client, monkeypatch):
    auth = login(client)
    thread, intr = confirmation(client, auth)
    service = client.app.state.service
    original = service.graph.stream
    def broken(*args, **kwargs):
        raise RuntimeError('private detail')
        yield
    monkeypatch.setattr(service.graph, 'stream', broken)
    failed = decision(client, auth, thread, intr)
    assert failed[-1][1]['status'] == 'FAILED'
    record = service.challenges.lookup(intr['challenge_id'])
    monkeypatch.setattr(service.graph, 'stream', original)
    out = decision(client, auth, thread, intr)
    assert result(out)['data']['remaining_balance_minor'] == 470000
    assert service.challenges.lookup(intr['challenge_id'])['idempotency_key'] == record['idempotency_key']


def test_actual_inflight_graph_blocks_other_requests_and_reset(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    auth = login(client)
    entered, proceed = threading.Event(), threading.Event()
    service = client.app.state.service
    original = service.graph.stream
    def slow(*args, **kwargs):
        entered.set()
        assert proceed.wait(timeout=5)
        yield from original(*args, **kwargs)
    monkeypatch.setattr(service.graph, 'stream', slow)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(chat, client, auth, message='余额')
        try:
            assert entered.wait(timeout=3)
            busy = client.post('/agent/chat', headers=auth, json={'message': '余额'})
            assert busy.status_code == 409
            assert busy.json()['code'] == 'RUN_BUSY'
            assert client.post('/demo/reset', headers=auth).status_code == 409
        finally:
            proceed.set()
        assert result(future.result(timeout=5))['data']['balance_minor'] == 500000

# ---------------------------------------------------------------------------
# 局域网开关：显式降级，默认关闭
# ---------------------------------------------------------------------------


def test_non_local_host_is_rejected_by_default():
    """默认只认回环地址：把链接发给别人是打不开的。"""
    with TestClient(create_app(demo=True), base_url='http://10.1.2.3:8021') as lan:
        assert lan.get('/health').status_code == 403
        assert lan.get('/health').json()['message'] == '仅允许本地同源演示。'


def test_non_local_host_allowed_only_when_explicitly_enabled():
    """设了 BANKAGENT_DEMO_ALLOW_LAN 才放宽，且只放宽 host。"""
    with TestClient(create_app(demo=True, allow_lan=True), base_url='http://10.1.2.3:8021') as lan:
        assert lan.get('/health').status_code == 200


def test_allow_lan_keeps_same_origin_check():
    """放行局域网不等于放行跨站：origin 与 host 不一致仍然拒绝。"""
    with TestClient(create_app(demo=True, allow_lan=True), base_url='http://10.1.2.3:8021') as lan:
        blocked = lan.get('/health', headers={'origin': 'http://evil.example'})
        assert blocked.status_code == 403


def test_allow_lan_does_not_open_a_non_demo_app():
    """allow_lan 只放宽「谁能进来」，不放宽「是不是演示模式」。"""
    with TestClient(create_app(demo=False, allow_lan=True), base_url='http://10.1.2.3:8021') as lan:
        assert lan.post('/demo/session').status_code == 404


def test_local_access_still_works_with_allow_lan():
    with TestClient(create_app(demo=True, allow_lan=True), base_url='http://localhost') as local:
        assert local.get('/health').status_code == 200