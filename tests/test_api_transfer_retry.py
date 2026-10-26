"""原授权下重试真实账本写入：执行前失败与落账后响应丢失。"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from bankagent.agent.agent_security import SG_TZ
from bankagent.agent.scenarios import REGISTRY
from test_api_http import chat, login, confirmation, decision, result


class SessionHeaders(dict):
    def __repr__(self):
        return "<ephemeral session headers>"


@pytest.fixture
def recovery(monkeypatch):
    from bankagent.agent.scenarios import bills
    monkeypatch.setattr(bills, '_clock', bills._clock)
    now = [datetime(2026, 10, 18, 12, tzinfo=SG_TZ)]
    with TestClient(create_app(demo=True, clock=lambda: now[0]), base_url='http://localhost') as c:
        yield c, SessionHeaders(login(c)), now


def transfers(c, auth):
    out = chat(c, auth, message='本月账单')
    return [row for row in result(out)['data']['transactions'] if row['kind'] == 'TRANSFER_OUT']


def interrupt_once(monkeypatch, *, after_write=False, structured=False):
    spec = REGISTRY.get('transfer')
    original = spec.execute
    attempts, committed = [], []
    def flaky(operation, params, context):
        attempts.append(context)
        if len(attempts) == 1:
            if after_write:
                committed.append(original(operation, params, context))
            if structured:
                return {'operation': 'TRANSFER', 'status': 'FAILED', 'data': None, 'error_code': 'INTERNAL'}
            raise RuntimeError('private transient diagnostic')
        return original(operation, params, context)
    monkeypatch.setattr(spec, 'execute', flaky)
    return attempts, committed


@pytest.mark.parametrize('after_write', [False, True])
@pytest.mark.parametrize('structured', [False, True])
def test_retry_recovers_with_same_authorization_and_never_debits_twice(recovery, monkeypatch, after_write, structured):
    c, auth, _ = recovery
    thread, intr = confirmation(c, auth)
    store = c.app.state.service.challenges
    before = store.lookup(intr['challenge_id'])
    attempts, committed = interrupt_once(monkeypatch, after_write=after_write, structured=structured)
    failed = decision(c, auth, thread, intr)
    assert failed[-1][1]['status'] == 'FAILED'
    assert 'private transient diagnostic' not in repr(failed)
    assert len(transfers(c, auth)) == int(after_write)
    recovered = decision(c, auth, thread, intr)
    assert recovered[-1][1]['status'] == 'COMPLETED'
    outcome = result(recovered)
    assert outcome['data']['remaining_balance_minor'] == 470000
    assert recovered[0][1]['request_id'] == intr['request_id']
    assert len(attempts) == 2 and attempts[0] == attempts[1]
    assert store.lookup(intr['challenge_id'])['idempotency_key'] == before['idempotency_key']
    assert len(transfers(c, auth)) == 1
    if after_write:
        assert outcome == committed[0]
    replay = decision(c, auth, thread, intr)
    assert result(replay) == outcome
    assert len(attempts) == 2  # 成功结果重放不再进入执行节点。
    assert len(transfers(c, auth)) == 1
    assert 'private transient diagnostic' not in repr(recovered)


@pytest.mark.parametrize('after_write', [False, True])
def test_retry_after_expiry_only_recovers_prior_success_never_creates_new_debit(recovery, monkeypatch, after_write):
    c, auth, now = recovery
    thread, intr = confirmation(c, auth)
    interrupt_once(monkeypatch, after_write=after_write)
    assert decision(c, auth, thread, intr)[-1][1]['status'] == 'FAILED'
    now[0] += timedelta(minutes=6)
    out = decision(c, auth, thread, intr)
    assert out[-1][1]['status'] == ('COMPLETED' if after_write else 'REJECTED')
    assert len(transfers(c, auth)) == int(after_write)
    if not after_write:
        assert result(out)['error_code'] == 'AUTHORIZATION_INVALID'


@pytest.mark.parametrize('tamper', ['params', 'decision', 'revoked', 'session'])
def test_failed_transfer_retry_keeps_existing_security_checks(recovery, monkeypatch, tamper):
    c, auth, _ = recovery
    thread, intr = confirmation(c, auth)
    attempts, _ = interrupt_once(monkeypatch)
    assert decision(c, auth, thread, intr)[-1][1]['status'] == 'FAILED'
    service = c.app.state.service
    selected_auth, chosen = auth, 'approve'
    if tamper == 'params':
        cfg = {'configurable': {'thread_id': thread}}
        state = service.graph.get_state(cfg).values
        service.graph.update_state(cfg, {'params': {**state['params'], 'amount_minor': 30100}})
    elif tamper == 'decision':
        chosen = 'reject'
    elif tamper == 'revoked':
        service.challenges.invalidate_all()
    else:
        selected_auth = login(c)
    response = c.post('/agent/chat', headers=selected_auth, json={'thread_id': thread,
        'resume': {'challenge_id': intr['challenge_id'], 'decision': chosen}})
    assert response.status_code == (404 if tamper == 'session' else 409)
    assert len(attempts) == 1
    assert transfers(c, auth) == []


def test_business_rejection_is_replayed_without_reexecution(recovery, monkeypatch):
    c, auth, _ = recovery
    thread, intr = confirmation(c, auth)
    spec = REGISTRY.get('transfer')
    calls = []
    def reject(*args):
        calls.append(True)
        return {'operation': 'TRANSFER', 'status': 'REJECTED', 'data': None, 'error_code': 'INSUFFICIENT_BALANCE'}
    monkeypatch.setattr(spec, 'execute', reject)
    first = decision(c, auth, thread, intr)
    assert result(first)['status'] == 'REJECTED'
    assert result(decision(c, auth, thread, intr)) == result(first)
    assert len(calls) == 1
    assert transfers(c, auth) == []


def test_red_retry_reuses_prior_strong_auth_without_reauthentication(recovery, monkeypatch):
    c, auth, _ = recovery
    auth_calls = []
    def verified(context, transient):
        auth_calls.append(context.request_id)
        return True  # 测试内独立认证替身，不作为运行时认证能力。
    c.app.state.service.authenticate = verified
    thread, intr = confirmation(c, auth, amount=1500)
    attempts, _ = interrupt_once(monkeypatch)
    assert decision(c, auth, thread, intr)[-1][1]['status'] == 'FAILED'
    out = decision(c, auth, thread, intr)
    assert result(out)['data']['remaining_balance_minor'] == 350000
    assert len(attempts) == 2 and attempts[0] == attempts[1]
    assert len(auth_calls) == 1
    assert len(transfers(c, auth)) == 1


def test_retry_scheduling_survives_another_graph_stream_failure(recovery, monkeypatch):
    c, auth, _ = recovery
    thread, intr = confirmation(c, auth)
    attempts, _ = interrupt_once(monkeypatch)
    assert decision(c, auth, thread, intr)[-1][1]['status'] == 'FAILED'
    graph = c.app.state.service.graph
    original = graph.stream
    def broken(*args, **kwargs):
        raise RuntimeError('transient graph outage')
        yield
    with monkeypatch.context() as transient:
        transient.setattr(graph, 'stream', broken)
        assert decision(c, auth, thread, intr)[-1][1]['status'] == 'FAILED'
    assert graph.get_state({'configurable': {'thread_id': thread}}).next
    out = decision(c, auth, thread, intr)
    assert result(out)['data']['remaining_balance_minor'] == 470000
    assert len(attempts) == 2
    assert len(transfers(c, auth)) == 1


def test_retry_does_not_repeat_intent_resolution_or_initial_risk_planning(recovery, monkeypatch):
    c, auth, _ = recovery
    thread, intr = confirmation(c, auth)
    attempts, _ = interrupt_once(monkeypatch)
    assert decision(c, auth, thread, intr)[-1][1]['status'] == 'FAILED'
    def unexpected(*args, **kwargs):
        raise AssertionError('retry must not re-plan the operation')
    with monkeypatch.context() as planning:
        for method in ('match_intents', 'resolve_params', 'evaluate_risk'):
            planning.setattr(REGISTRY, method, unexpected)
        out = decision(c, auth, thread, intr)
        assert result(out)['data']['remaining_balance_minor'] == 470000
    assert len(attempts) == 2
    cfg = {'configurable': {'thread_id': thread}}
    state = c.app.state.service.graph.get_state(cfg).values
    assert state['response'].startswith('已向')
    assert '尚未确认' not in state['response']
    history = repr(list(c.app.state.service.graph.get_state_history(cfg)))
    assert attempts[0].idempotency_key not in history
    assert 'authorization_ref' not in history


def test_reset_invalidates_a_failed_operation_before_retry(recovery, monkeypatch):
    c, auth, _ = recovery
    thread, intr = confirmation(c, auth)
    attempts, _ = interrupt_once(monkeypatch)
    assert decision(c, auth, thread, intr)[-1][1]['status'] == 'FAILED'
    assert c.post('/demo/reset', headers=auth).status_code == 200
    body = {'thread_id': thread, 'resume': {'challenge_id': intr['challenge_id'], 'decision': 'approve'}}
    assert c.post('/agent/chat', headers=auth, json=body).status_code == 401
    fresh = login(c)
    assert c.post('/agent/chat', headers=fresh, json=body).status_code == 404
    assert len(attempts) == 1
    assert transfers(c, fresh) == []


def test_real_tcp_recovers_original_transaction_after_committed_response_loss(recovery, monkeypatch):
    import socket
    import threading
    import time
    import httpx
    import uvicorn
    c, _, _ = recovery
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(c.app, log_level='error', access_log=False))
    worker = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    worker.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started:
            assert worker.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=5, trust_env=False) as network:
            auth = SessionHeaders(login(network))
            thread, intr = confirmation(network, auth)
            attempts, committed = interrupt_once(monkeypatch, after_write=True)
            assert decision(network, auth, thread, intr)[-1][1]['status'] == 'FAILED'
            recovered = decision(network, auth, thread, intr)
            assert result(recovered) == committed[0]
            assert result(recovered)['data']['remaining_balance_minor'] == 470000
            assert result(decision(network, auth, thread, intr)) == committed[0]
            assert len(attempts) == 2
            assert len(transfers(network, auth)) == 1
    finally:
        server.should_exit = True
        worker.join(timeout=5)
        sock.close()
        assert not worker.is_alive()


def test_retry_still_rechecks_current_daily_risk_in_backend(recovery, monkeypatch):
    c, auth, _ = recovery
    thread, intr = confirmation(c, auth, amount=300)
    interrupt_once(monkeypatch)
    assert decision(c, auth, thread, intr)[-1][1]['status'] == 'FAILED'
    other_thread, other_intr = confirmation(c, auth, amount=900)
    assert result(decision(c, auth, other_thread, other_intr))['status'] == 'COMPLETED'
    retried = decision(c, auth, thread, intr)
    assert result(retried)['error_code'] == 'REAUTHORIZATION_REQUIRED'
    assert result(retried)['status'] == 'REJECTED'
    assert result(chat(c, auth, message='余额'))['data']['balance_minor'] == 410000
    assert len(transfers(c, auth)) == 1
