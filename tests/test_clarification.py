"""同一真实 HTTP 会话内补槽，不新增公开请求字段或复用旧执行参数。"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from bankagent.agent.agent_security import SG_TZ
from test_api_http import chat, login, result, decision


@pytest.fixture
def conversation(monkeypatch):
    from bankagent.agent.scenarios import bills
    monkeypatch.setattr(bills, '_clock', bills._clock)
    now = [datetime(2026, 10, 18, 12, tzinfo=SG_TZ)]
    app = create_app(demo=True, clock=lambda: now[0])
    with TestClient(app, base_url='http://localhost') as client:
        yield client, login(client), now


def follow(c, auth, first, text):
    return chat(c, auth, thread_id=first[0][1]['thread_id'], message=text)


def confirm(out):
    assert out[-1][1]['status'] == 'AWAITING_CONFIRMATION'
    return next(d['payload'] for name, d in out if name == 'card' and d['type'] == 'confirm')


@pytest.mark.parametrize('reply', ['300 元', '300', '金额是300元', '金额改为300元'])
def test_only_missing_amount_completes_and_requires_new_confirmation(conversation, reply):
    c, auth, _ = conversation
    first = chat(c, auth, message='给张伟转钱')
    assert first[-1][1]['status'] == 'NEEDS_CLARIFICATION'
    second = follow(c, auth, first, reply)
    assert confirm(second)['amount_minor'] == 30000
    assert confirm(second)['recipient'] == '张伟'
    assert first[0][1]['request_id'] != second[0][1]['request_id']
    assert result(chat(c, auth, message='余额'))['data']['balance_minor'] == 500000
    intr = next(d for name, d in second if name == 'interrupt')
    assert result(decision(c, auth, intr['thread_id'], intr))['data']['remaining_balance_minor'] == 470000


@pytest.mark.parametrize('reply', ['李娜', '改成李娜', '给李娜', '给李娜转钱'])
def test_recipient_correction_resolves_fresh_contact_and_keeps_only_candidate_amount(conversation, reply):
    c, auth, _ = conversation
    first = chat(c, auth, message='给王五转 300 元')
    assert first[-1][1]['status'] == 'NEEDS_CLARIFICATION'
    second = follow(c, auth, first, reply)
    assert confirm(second)['recipient'] == '李娜'
    intr = next(d for name, d in second if name == 'interrupt')
    state = c.app.state.service.graph.get_state({'configurable': {'thread_id': intr['thread_id']}}).values
    assert state['params']['contact_id'] == 'contact-002'
    assert result(decision(c, auth, intr['thread_id'], intr))['data']['recipient'] == '李娜'


def test_change_recipient_while_amount_missing_then_supply_amount(conversation):
    c, auth, _ = conversation
    first = chat(c, auth, message='给张伟转钱')
    second = follow(c, auth, first, '改成李娜')
    assert second[-1][1]['status'] == 'NEEDS_CLARIFICATION'
    assert confirm(follow(c, auth, second, '300元'))['recipient'] == '李娜'


@pytest.mark.parametrize('topic', ['查余额', '本月账单'])
def test_topic_change_discards_pending_transfer(conversation, topic):
    c, auth, _ = conversation
    first = chat(c, auth, message='给张伟转钱')
    query = follow(c, auth, first, topic)
    assert query[-1][1]['status'] == 'COMPLETED'
    final = follow(c, auth, first, '300元')
    assert final[-1][1]['status'] == 'REJECTED'
    assert not any(n == 'interrupt' for n, _ in final)


@pytest.mark.parametrize('text', ['取消', '算了', '不要转了', '今天天气怎么样', '好的'])
def test_cancel_or_unclear_reply_cannot_revive_old_candidates(conversation, text):
    c, auth, _ = conversation
    first = chat(c, auth, message='给张伟转钱')
    second = follow(c, auth, first, text)
    assert not any(n == 'interrupt' for n, _ in second)
    third = follow(c, auth, first, '300元')
    assert third[-1][1]['status'] == 'REJECTED'


@pytest.mark.parametrize('reply', ['300.001元', '1,000元', '1e3元', '-300元', '300万元', '明天300元可以吗'])
def test_followup_never_truncates_or_guesses_amount(conversation, reply):
    c, auth, _ = conversation
    first = chat(c, auth, message='给张伟转钱')
    out = follow(c, auth, first, reply)
    assert not any(n == 'interrupt' for n, _ in out)
    assert result(chat(c, auth, message='余额'))['data']['balance_minor'] == 500000


def test_deadline_not_renewed_by_corrections(conversation):
    c, auth, now = conversation
    first = chat(c, auth, message='给张伟转钱')
    now[0] += timedelta(minutes=29)
    second = follow(c, auth, first, '改成李娜')
    now[0] += timedelta(minutes=1)
    out = follow(c, auth, second, '300元')
    assert out[-1][1]['status'] == 'REJECTED'


def test_candidates_do_not_cross_thread_session_or_reset(conversation):
    c, auth, _ = conversation
    first = chat(c, auth, message='给张伟转钱')
    assert chat(c, auth, message='300元')[-1][1]['status'] == 'REJECTED'
    outsider = login(c)
    r = c.post('/agent/chat', headers=outsider, json={'thread_id': first[0][1]['thread_id'], 'message': '300元'})
    assert r.status_code == 404
    assert c.post('/demo/reset', headers=auth).status_code == 200
    assert not c.app.state.service.runtime._clarify_tasks


def test_explicit_restart_clears_old_candidate_amount(conversation):
    c, auth, _ = conversation
    first = chat(c, auth, message='给王五转 300 元')
    second = follow(c, auth, first, '重新给李娜转钱')
    assert second[-1][1]['status'] == 'NEEDS_CLARIFICATION'
    assert not any(n == 'interrupt' for n, _ in second)


def test_pending_metadata_is_owned_and_cannot_be_mutated_via_snapshot(conversation):
    c, auth, _ = conversation
    out = chat(c, auth, message='给张伟转钱')
    thread = out[0][1]['thread_id']
    rt = c.app.state.service.runtime
    assert rt.pending_task('user-002', 'account-001', thread) is None
    assert rt.pending_task('user-001', 'account-002', thread) is None
    saved = rt.pending_task('user-001', 'account-001', thread)
    saved['candidate_params']['recipient_name'] = '李娜'
    assert confirm(follow(c, auth, out, '300元'))['recipient'] == '张伟'
