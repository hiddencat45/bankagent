from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from test_api_http import login
from test_bank_forms import form


def pending(c, h, amount='1200'):
    out = form(c, h, 'TRANSFER', recipient_name='张伟', amount=amount)
    card = next(d['payload'] for e, d in out if e == 'card' and d.get('type') == 'confirm')
    return {'thread_id': out[0][1]['thread_id'], 'challenge_id': card['challenge_id']}


def approve(c, h, ref, otp=None):
    resume = {'challenge_id': ref['challenge_id'], 'decision': 'approve'}
    if otp is not None:
        resume['otp'] = otp
    return c.post('/agent/chat', headers=h, json={'thread_id': ref['thread_id'], 'resume': resume})


def balance(c, h):
    return c.get('/bank/accounts', headers=h).json()['accounts'][0]['balance_minor']


def test_demo_verify_wrong_code_then_success_and_replay(tmp_path):
    with TestClient(create_app(demo=True, database_path=tmp_path/'a.sqlite3'), base_url='http://localhost') as c:
        h = login(c)
        ref = pending(c, h)
        assert approve(c, h, ref).json()['code'] == 'DEMO_AUTH_EXPIRED'
        info = c.post('/demo/verification', headers=h, json=ref).json()
        code = info['demo_code']
        assert len(code) == 6 and info['threshold_minor'] == 100000
        wrong = '000000' if code != '000000' else '111111'
        assert approve(c, h, ref, wrong).json()['code'] == 'DEMO_AUTH_INVALID'
        assert balance(c, h) == 500000
        assert approve(c, h, ref, code).status_code == 200
        assert balance(c, h) == 380000
        assert approve(c, h, ref).status_code == 200
        assert balance(c, h) == 380000
        # Authentication input is not included in model/graph checkpoints.
        snapshot = c.app.state.service.graph.get_state({'configurable': {'thread_id': ref['thread_id']}})
        assert 'otp' not in snapshot.values
        assert c.post('/demo/verification', headers=h, json=ref).status_code == 409


def test_demo_verify_lock_cancel_and_ownership():
    with TestClient(create_app(demo=True), base_url='http://localhost') as c:
        h = login(c)
        ref = pending(c, h)
        other = login(c)
        assert c.post('/demo/verification', headers=other, json=ref).status_code in {403, 404}
        code = c.post('/demo/verification', headers=h, json=ref).json()['demo_code']
        wrong = '000000' if code != '000000' else '111111'
        for _ in range(3):
            assert approve(c, h, ref, wrong).json()['code'] == 'DEMO_AUTH_INVALID'
        assert c.post('/demo/verification', headers=h, json=ref).json()['code'] == 'DEMO_AUTH_LOCKED'
        assert approve(c, h, ref, code).json()['code'] == 'DEMO_AUTH_LOCKED'
        cancelled = c.post('/agent/chat', headers=h, json={'thread_id': ref['thread_id'],
            'resume': {'challenge_id': ref['challenge_id'], 'decision': 'reject'}})
        assert cancelled.status_code == 200 and balance(c, h) == 500000
        assert approve(c, h, ref, code).status_code == 409


def test_demo_verify_expiry():
    now = [datetime(2026,10,18,12,tzinfo=timezone(timedelta(hours=8)))]
    with TestClient(create_app(demo=True, clock=lambda:now[0]), base_url='http://localhost') as c:
        h = login(c)
        ref = pending(c,h)
        code = c.post('/demo/verification',headers=h,json=ref).json()['demo_code']
        now[0] += timedelta(minutes=6)
        assert approve(c,h,ref,code).status_code == 409
        assert balance(c,h) == 500000


def test_changed_request_invalidates_authentication():
    from test_query_loop import Scripted, client_for
    from test_task_loop import prepare
    from test_api_http import chat
    with client_for(Scripted(prepare('1200'), prepare('30', ident='p2'))) as c:
        h = login(c)
        out = chat(c, h, message='给张伟转1200元')
        intr = next(d for e, d in out if e == 'interrupt')
        ref = {'thread_id':out[0][1]['thread_id'], 'challenge_id':intr['challenge_id']}
        code = c.post('/demo/verification', headers=h, json=ref).json()['demo_code']
        changed = c.post('/agent/chat', headers=h, json={'thread_id':ref['thread_id'], 'message':'改成30元'})
        assert changed.status_code == 200
        assert approve(c, h, ref, code).status_code == 409
        assert balance(c, h) == 500000
        assert c.post('/demo/verification', headers=h, content='broken').status_code == 400


@pytest.mark.parametrize('kwargs', [{'demo':False}, {'demo':True,'allow_lan':True}])
def test_verification_unavailable_outside_local_demo(kwargs):
    with TestClient(create_app(**kwargs),base_url='http://localhost') as c:
        assert c.post('/demo/verification',json={}).status_code == 404
