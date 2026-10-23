"""真实注册器、图、挑战表、后端与HTTP/SSE的订阅链路。"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from api.server import create_app
from agent_security import SG_TZ
from bank_backend import configure_backend
from bank_types import TrustedContext
from data.generator import build_demo_data
from scenarios import REGISTRY, subscription
from test_api_http import chat, login, result, decision


@pytest.fixture
def service(monkeypatch):
    from scenarios import bills
    monkeypatch.setattr(bills, '_clock', bills._clock)
    now = [datetime(2026, 10, 18, 12, tzinfo=SG_TZ)]
    with TestClient(create_app(demo=True, clock=lambda: now[0]), base_url='http://localhost') as client:
        yield client, login(client), now


def pending(client, auth, name='演示订阅'):
    out = chat(client, auth, message=f'暂停{name}的代扣')
    assert out[-1][1]['status'] == 'AWAITING_CONFIRMATION', out
    card = next(d['payload'] for event, d in out if event == 'card' and d['type'] == 'confirm')
    assert card['operation'] == 'PAUSE_SUBSCRIPTION'
    assert card['display_name'] == name and card['target_status'] == 'PAUSED'
    assert not {'subscription_id', 'user_id', 'authorized', 'authorization_ref'} & set(card)
    return out[0][1]['thread_id'], next(d for event, d in out if event == 'interrupt')


def test_registered_scene_resolves_only_backend_owned_names(service):
    ctx = TrustedContext('user-001', 'account-001', 'resolve')
    assert subscription.resolve({'subscription_name': '演示订阅'}, ctx) == {'subscription_id': 'subscription-001'}
    with pytest.raises(ValueError):
        subscription.resolve({'subscription_id': 'subscription-001'}, ctx)
    assert subscription.resolve({'subscription_name': 'unknown'}, ctx) == {}
    with pytest.raises(PermissionError):
        subscription.resolve({'subscription_name': '演示订阅'}, TrustedContext('user-002', 'account-001', 'other'))
    card = subscription.confirmation(operation='PAUSE_SUBSCRIPTION', params={'subscription_id': 'subscription-001'},
        candidate_params={'subscription_name': '演示订阅'}, context=ctx)
    assert card == {'display_name': '演示订阅', 'current_status': 'ACTIVE', 'target_status': 'PAUSED'}


def test_bill_evidence_to_subscription_confirm_pause_and_history(service):
    client, auth, _ = service
    bills = result(chat(client, auth, message='本月账单'))['data']
    before = result(chat(client, auth, message='查询订阅'))['data']
    assert before['total_minor'] == 23000
    assert before['subscriptions'][0]['paid_minor'] == 5000
    assert bills['anomalies'][0]['evidence'] == [p['transaction_id'] for p in before['subscriptions'][0]['payments']]
    thread, intr = pending(client, auth)
    assert result(chat(client, auth, message='查询订阅'))['data']['subscriptions'][0]['status'] == 'ACTIVE'
    cancelled = decision(client, auth, thread, intr, value='reject')
    assert cancelled[-1][1]['status'] == 'REJECTED'
    assert result(chat(client, auth, message='查询订阅'))['data'] == before
    thread, intr = pending(client, auth)
    completed = result(decision(client, auth, thread, intr))
    assert completed['data']['status'] == 'PAUSED' and completed['data']['changed'] is True
    assert result(decision(client, auth, thread, intr)) == completed
    after = result(chat(client, auth, message='查询订阅'))['data']
    assert after['total_minor'] == before['total_minor']
    assert after['subscriptions'][0]['payments'] == before['subscriptions'][0]['payments']
    assert result(chat(client, auth, message='本月账单'))['data'] == bills
    assert result(chat(client, auth, message='余额'))['data']['balance_minor'] == 500000
    assert client.post('/demo/reset', headers=auth).status_code == 200
    new_auth = login(client)
    assert result(chat(client, new_auth, message='查询订阅'))['data'] == before


@pytest.mark.parametrize('message', ['暂停', '暂停这个代扣', '不要暂停演示订阅', '查询订阅并暂停演示订阅'])
def test_ambiguous_missing_negative_and_multiple_requests_never_write(service, message):
    client, auth, _ = service
    out = chat(client, auth, message=message)
    assert out[-1][1]['status'] in {'NEEDS_CLARIFICATION', 'REJECTED'}
    assert not any(event == 'interrupt' for event, _ in out)
    assert result(chat(client, auth, message='查询订阅'))['data']['subscriptions'][0]['status'] == 'ACTIVE'


def test_duplicate_names_are_not_resolved_to_first_record():
    data = build_demo_data()
    data['subscriptions']['subscription-002']['display_name'] = '演示订阅'
    configure_backend(data_factory=lambda: data)
    assert subscription.resolve({'subscription_name': '演示订阅'}, TrustedContext('user-001', 'account-001', 'same-name')) == {}


@pytest.mark.parametrize('after_write', [False, True])
def test_original_confirmation_can_recover_subscription_write_failure(service, monkeypatch, after_write):
    client, auth, _ = service
    thread, intr = pending(client, auth)
    original = REGISTRY.get('subscription').execute
    attempts = []
    def flaky(operation, params, context):
        if operation == 'PAUSE_SUBSCRIPTION':
            attempts.append(context)
            if len(attempts) == 1:
                if after_write:
                    original(operation, params, context)
                raise RuntimeError('private subscription failure')
        return original(operation, params, context)
    monkeypatch.setattr(REGISTRY.get('subscription'), 'execute', flaky)
    first = decision(client, auth, thread, intr)
    assert first[-1][1]['status'] == 'FAILED'
    assert 'private subscription failure' not in repr(first)
    recovered = result(decision(client, auth, thread, intr))
    assert recovered['data']['changed'] is True
    assert len(attempts) == 2 and attempts[0] == attempts[1]
    assert result(chat(client, auth, message='查询订阅'))['data']['subscriptions'][0]['status'] == 'PAUSED'
