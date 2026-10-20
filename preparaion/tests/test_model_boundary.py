"""供应商未选定时，用测试内模型替身验证边界，绝不冒充真实模型验收。"""
from copy import deepcopy
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from agent_security import SG_TZ
from agent_understanding import CandidateInterpreter, UnderstandingError
from api.server import create_app
from scenarios import REGISTRY
from test_api_http import chat, login, result, decision


def transfer(**slots):
    return {'scenario': 'transfer', 'intent': 'TRANSFER', 'candidate_params': slots}


class StubModel:
    def __init__(self, output):
        self.output, self.requests, self.available = output, [], True

    def predict(self, request):
        self.requests.append(deepcopy(request))
        if isinstance(self.output, Exception):
            raise self.output
        return deepcopy(self.output)

    def health(self):
        return self.available


@pytest.fixture
def model_client(monkeypatch):
    from scenarios import bills
    monkeypatch.setattr(bills, '_clock', bills._clock)
    model = StubModel(transfer(recipient_name='张伟', amount='300'))
    app = create_app(demo=True, clock=lambda: datetime(2026, 10, 18, 12, tzinfo=SG_TZ), candidate_model=model)
    with TestClient(app, base_url='http://localhost') as client:
        yield client, model, login(client)


def test_model_candidate_uses_real_resolve_risk_confirmation_and_execution(model_client):
    c, model, auth = model_client
    out = chat(c, auth, message='替我给张伟汇去三百元')
    assert all(d['mode'] == 'model' for _, d in out)
    assert out[-1][1]['status'] == 'AWAITING_CONFIRMATION'
    intr = next(d for n, d in out if n == 'interrupt')
    done = decision(c, auth, intr['thread_id'], intr)
    assert result(done)['data']['remaining_balance_minor'] == 470000
    assert len(model.requests) == 1  # 恢复不重新理解用户请求。


def test_model_followup_prompt_contains_only_allowlisted_candidate_context(model_client):
    c, model, auth = model_client
    model.output = transfer(recipient_name='张伟')
    first = chat(c, auth, message='我想给张伟一笔钱')
    assert first[-1][1]['status'] == 'NEEDS_CLARIFICATION'
    model.output = transfer(amount='300')
    out = chat(c, auth, thread_id=first[0][1]['thread_id'], message='三百元')
    assert out[-1][1]['status'] == 'AWAITING_CONFIRMATION'
    request = model.requests[-1]
    assert request['pending'] == {'scenario': 'transfer', 'intent': 'TRANSFER',
        'candidate_params': {'recipient_name': '张伟'}, 'missing_fields': ['amount']}
    text = repr(model.requests)
    for forbidden in ('user_id', 'account_id', 'request_id', 'contact_id', 'challenge_id',
                      'operation_hash', 'authorization_ref', 'idempotency_key', 'risk_level', 'expires_at', 'balance_minor'):
        assert forbidden not in text
    assert auth['Authorization'].removeprefix('Bearer ') not in text


@pytest.mark.parametrize('field', ['user_id', 'account_id', 'request_id', 'contact_id', 'authorized',
                                  'risk_level', 'operation_hash', 'challenge_id', 'result', 'params',
                                  'idempotency_key', 'authorization_ref', 'daily_transfer_total_minor'])
@pytest.mark.parametrize('nested', [False, True])
def test_model_cannot_supply_trusted_fields(model_client, field, nested):
    c, model, auth = model_client
    model.output = transfer(recipient_name='张伟', amount='300')
    target = model.output['candidate_params'] if nested else model.output
    target[field] = 'untrusted'
    out = chat(c, auth, message='给张伟转300元')
    error = next(d for n, d in out if n == 'error')
    assert error['code'] == 'MODEL_OUTPUT_INVALID'
    assert out[-1][1]['status'] == 'FAILED'
    assert not any(n == 'interrupt' for n, _ in out)


@pytest.mark.parametrize('output', [None, [], 'raw model text', {},
    {'scenario': [], 'intent': 'TRANSFER', 'candidate_params': {}},
    {'scenario': 'missing', 'intent': 'TRANSFER', 'candidate_params': {}},
    {'scenario': 'bills', 'intent': 'TRANSFER', 'candidate_params': {}},
    transfer(amount=300), transfer(amount=300.0), transfer(amount=True),
    transfer(amount={}), transfer(amount=['300']), transfer(amount=''), transfer(amount='3' * 257),
    transfer(unknown='x'),
])
def test_bad_model_output_fails_without_falling_back_to_keyword_rules(model_client, output):
    c, model, auth = model_client
    model.output = output
    out = chat(c, auth, message='给张伟转300元')
    assert next(d for n, d in out if n == 'error')['code'] == 'MODEL_OUTPUT_INVALID'
    assert out[-1][1]['status'] == 'FAILED'
    assert all(d['mode'] == 'model' for _, d in out)
    assert not any(n == 'interrupt' for n, _ in out)


@pytest.mark.parametrize('error', [TimeoutError('private provider detail'), RuntimeError('private provider detail')])
def test_model_failure_is_sanitized_and_does_not_switch_mode(model_client, error):
    c, model, auth = model_client
    model.output = error
    out = chat(c, auth, message='给张伟转300元')
    assert next(d for n, d in out if n == 'error')['code'] == 'MODEL_UNAVAILABLE'
    assert out[-1][1]['status'] == 'FAILED'
    assert 'private provider detail' not in repr(out)
    assert all(d['mode'] == 'model' for _, d in out)
    service = c.app.state.service
    assert 'private provider detail' not in repr(list(service.graph.get_state_history(
        {'configurable': {'thread_id': out[0][1]['thread_id']}})))


@pytest.mark.parametrize('text', ['不要给张伟转300元', '给张伟转300元，不要执行', '是否给张伟转300元'])
def test_valid_model_write_still_cannot_override_negative_message(model_client, text):
    c, model, auth = model_client
    out = chat(c, auth, message=text)
    assert out[-1][1]['status'] == 'NEEDS_CLARIFICATION'
    assert not any(n == 'interrupt' for n, _ in out)


def test_model_mode_health_and_reset_preserve_server_configuration(model_client):
    c, model, auth = model_client
    assert c.get('/health').json()['model'] == 'ok'
    assert c.post('/demo/session').json()['mode'] == 'model'
    model.available = False
    assert c.get('/health').json() == {'status': 'degraded', 'mode': 'model', 'backend': 'ok', 'model': 'unavailable'}
    assert c.post('/demo/reset', headers=auth).status_code == 200
    assert c.app.state.service.runtime.mode == 'model'
    assert c.app.state.service.runtime.interpreter.model is model


def test_empty_candidate_means_clarify_not_arbitrary_write(model_client):
    c, model, auth = model_client
    model.output = {'scenario': None, 'intent': None, 'candidate_params': {}}
    out = chat(c, auth, message='替我处理一下')
    assert out[-1][1]['status'] == 'NEEDS_CLARIFICATION'
    assert not any(n == 'interrupt' for n, _ in out)


def test_schema_validation_is_independent_of_accidental_trusted_slot_declaration(monkeypatch):
    declaration = REGISTRY.get('transfer').intents['TRANSFER']
    monkeypatch.setitem(declaration, 'slots', {**declaration['slots'], 'authorized': ''})
    model = StubModel(transfer(authorized='true'))
    interpreter = CandidateInterpreter(model, REGISTRY)
    with pytest.raises(UnderstandingError) as caught:
        interpreter.predict('任意消息', None)
    assert caught.value.code == 'MODEL_OUTPUT_INVALID'

    assert 'authorized' not in repr(model.requests)


@pytest.mark.parametrize('amount', ['300.001', '1,000', '1e3', '-300', '300万'])
def test_model_candidates_still_use_python_amount_validation(model_client, amount):
    c, model, auth = model_client
    model.output = transfer(recipient_name='张伟', amount=amount)
    out = chat(c, auth, message='给张伟转一笔钱')
    assert out[-1][1]['status'] == 'REJECTED'
    assert not any(n == 'interrupt' for n, _ in out)


def test_model_multiround_keeps_topic_change_and_user_isolation(model_client):
    c, model, auth = model_client
    model.output = transfer(recipient_name='张伟')
    first = chat(c, auth, message='我要给张伟一笔钱')
    model.output = {'scenario': 'bills', 'intent': 'BILLS_QUERY', 'candidate_params': {'period': '本月'}}
    query = chat(c, auth, thread_id=first[0][1]['thread_id'], message='还是查一下账单')
    assert result(query)['data']['total_minor'] == 100000
    assert not c.app.state.service.runtime._clarify_tasks
    model.output = transfer(amount='300')
    out = chat(c, auth, message='三百元')
    assert model.requests[-1]['pending'] is None
    assert out[-1][1]['status'] == 'NEEDS_CLARIFICATION'


def test_health_exception_reports_degraded_without_provider_detail(model_client, monkeypatch):
    c, model, auth = model_client
    def unavailable():
        raise RuntimeError('private provider detail')
    monkeypatch.setattr(model, 'health', unavailable)
    response = c.get('/health')
    assert response.json()['model'] == 'unavailable'
    assert response.json()['status'] == 'degraded'
    assert 'private provider detail' not in response.text
