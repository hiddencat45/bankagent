"""Unified task loop: actual bank + HTTP, only model choices are scripted."""
import json
import pytest
from bankagent.banking import bank_backend
from bankagent.banking.bank_types import TrustedContext
from test_query_loop import Scripted, call, answer, client_for, CTX
from test_api_http import login, chat, decision


def prepare(amount='40', person='张伟', ident='p1'):
    return call('prepare_transfer', {'recipient_name': person, 'amount': amount}, ident)


def pending(out):
    return out[0][1]['thread_id'], next(d for n, d in out if n == 'interrupt')


def receipts(out):
    return [d['payload'] for n, d in out if n == 'card' and d['type'] == 'result']


def balance():
    return bank_backend.get_balance(context=CTX)['data']['balance_minor']


def test_read_prepare_execute_recheck_and_replay():
    model = Scripted(call('get_balance', {}), prepare(),
                     call('query_transactions', {'period': '本月'}, 'q2'), answer('转账已完成，记录如下。'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='先查余额，够的话给张伟40元，之后查记录')
        assert receipts(first)[0]['data']['balance_minor'] == 500000
        assert balance() == 500000
        thread, intr = pending(first)
        done = decision(c, auth, thread, intr)
        assert done[-1][1]['status'] == 'COMPLETED'
        rows = receipts(done)
        transfer = next(r for r in rows if r['operation'] == 'TRANSFER')
        assert transfer['status'] == 'COMPLETED'
        assert balance() == 496000
        assert bank_backend.get_balance(context=TrustedContext('user-002', 'account-002', 'r'))['data']['balance_minor'] == 44000
        assert any(t.get('transfer_id') == transfer['data']['transfer_id'] for t in rows[-1]['data']['transactions'])
        assert decision(c, auth, thread, intr) == done
        assert balance() == 496000
        tools = [m for m in model.requests[2] if m['role'] == 'tool']
        assert json.loads(tools[-1]['content'])['status'] == 'COMPLETED'


@pytest.mark.parametrize('latest,following,expected', [
    ('改成30元', prepare('30', ident='p2'), 'AWAITING_CONFIRMATION'),
    ('不转了', call('cancel_task', {}, 'cancel'), 'REJECTED'),
    ('先看余额', call('get_balance', {}, 'balance'), 'COMPLETED'),
])
def test_pending_latest_message_invalidates_old_confirmation(latest, following, expected):
    model = Scripted(prepare(), following, answer('余额见回执。'), answer('已完成。'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='转40给张伟')
        thread, intr = pending(first)
        latest_out = chat(c, auth, thread_id=thread, message=latest)
        assert latest_out[-1][1]['status'] == expected
        assert balance() == 500000
        stale = c.post('/agent/chat', headers=auth, json={'thread_id': thread,
            'resume': {'challenge_id': intr['challenge_id'], 'decision': 'approve'}})
        assert stale.status_code == 409
        if expected == 'AWAITING_CONFIRMATION':
            _, new = pending(latest_out)
            decision(c, auth, thread, new)
            assert balance() == 497000


def test_query_does_not_discard_draft_and_continuation_needs_new_confirmation():
    model = Scripted(prepare(), call('get_balance', {}, 'b'), answer('尚未转账。'),
                     prepare(ident='p2'), call('query_transactions', {'period': '本月'}, 'q'), answer('记录已核对。'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='给张伟四十元')
        thread, _ = pending(first)
        chat(c, auth, thread_id=thread, message='先看余额')
        again = chat(c, auth, thread_id=thread, message='继续原来的转账')
        assert balance() == 500000
        decision(c, auth, *pending(again))
        assert balance() == 496000


def test_missing_information_then_continue():
    model = Scripted(call('prepare_transfer', {'amount': '40'}, 'p'), prepare(ident='p2'), answer('已执行。'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='转四十块')
        assert first[-1][1]['status'] == 'NEEDS_CLARIFICATION'
        second = chat(c, auth, thread_id=first[0][1]['thread_id'], message='给张伟')
        decision(c, auth, *pending(second))
        assert balance() == 496000
        assert any(m['role'] == 'tool' for m in model.requests[1])


def test_execution_failure_stops_dependent_queries(monkeypatch):
    model = Scripted(prepare(), call('query_transactions', {'period': '本月'}, 'q'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='转完查记录')
        monkeypatch.setattr(bank_backend, 'execute_transfer', lambda **kwargs: {
            'operation': 'TRANSFER', 'status': 'FAILED', 'data': None, 'error_code': 'INTERNAL'})
        out = decision(c, auth, *pending(first))
        assert out[-1][1]['status'] == 'FAILED'
        assert len(model.requests) == 1
        assert balance() == 500000


def test_second_write_has_separate_confirmation_and_idempotency():
    model = Scripted(prepare(), prepare(ident='p2'), answer('两笔已办理。'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='分别转两笔40，每笔单独确认')
        second = decision(c, auth, *pending(first))
        assert balance() == 496000
        assert second[-1][1]['status'] == 'AWAITING_CONFIRMATION'
        done = decision(c, auth, *pending(second))
        assert done[-1][1]['status'] == 'COMPLETED'
        assert balance() == 492000
        decision(c, auth, *pending(second))
        assert balance() == 492000


def test_cancel_confirmation_drops_dependencies():
    model = Scripted(prepare())
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='给张伟40然后查流水')
        out = decision(c, auth, *pending(first), value='reject')
        assert out[-1][1]['status'] == 'REJECTED'
        assert balance() == 500000
        assert not c.app.state.service.runtime.query_agent._tasks


@pytest.mark.parametrize('fields', [{'recipient_name': '张伟', 'amount': '40', 'authorized': 'true'},
                                   {'recipient_name': '张伟', 'amount': '40', 'user_id': 'user-002'}])
def test_model_cannot_supply_authority(fields):
    with client_for(Scripted(call('prepare_transfer', fields))) as c:
        out = chat(c, login(c), message='执行转账')
        assert out[-1][1]['status'] == 'FAILED'
        assert balance() == 500000

def test_model_failure_after_commit_preserves_receipt_and_does_not_retry_payment():
    model = Scripted(prepare(), RuntimeError('model offline'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='转后查询')
        done = decision(c, auth, *pending(first))
        assert balance() == 496000
        assert len([r for r in receipts(done) if r['operation'] == 'TRANSFER']) == 1
        assert any('后续查询未完成' in d.get('text', '') for _, d in done)
        decision(c, auth, *pending(first))
        assert balance() == 496000


def test_expired_task_never_resumes_a_write_without_a_new_confirmation():
    from datetime import timedelta
    model = Scripted(prepare(), call('get_balance', {}, 'b'), answer('余额。'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='给张伟40元')
        agent = c.app.state.service.runtime.query_agent
        for task in agent._tasks.values():
            task['expires_at'] = agent.clock() - timedelta(seconds=1)
        out = chat(c, auth, thread_id=pending(first)[0], message='先查余额')
        assert out[-1][1]['status'] == 'COMPLETED'
        assert balance() == 500000

def test_existing_card_query_continues_without_language_reparse():
    model = Scripted(call('query_cards', {}, 'cards'), answer('卡片见回执。'))
    with client_for(model) as c:
        out = chat(c, login(c), message='列出我的银行卡')
        assert out[-1][1]['status'] == 'COMPLETED'
        assert receipts(out)[-1]['operation'] == 'QUERY_CARDS'
        assert len(model.requests) == 2


def test_consumption_filters_survive_confirmation_pause():
    model = Scripted(call('query_expenses', {'inherit': False, 'period': '本月', 'category': '餐饮'}, 'q1'),
                     prepare(), call('query_expenses', {'inherit': True}, 'q2'), answer('复查消费，转账不计入消费。'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='看本月餐饮，再给张伟40，之后再看这类消费')
        out = decision(c, auth, *pending(first))
        assert out[-1][1]['status'] == 'COMPLETED'
        assert receipts(out)[-1]['data']['total_minor'] == 12000
        assert balance() == 496000

def test_post_payment_card_query_keeps_confirmation_replay_valid():
    model = Scripted(prepare(), call('query_cards', {}, 'cards'), answer('转账完成，卡片如下。'))
    with client_for(model) as c:
        auth = login(c)
        first = chat(c, auth, message='转40给张伟，然后查银行卡')
        out = decision(c, auth, *pending(first))
        assert receipts(out)[-1]['operation'] == 'QUERY_CARDS'
        assert decision(c, auth, *pending(first)) == out
        assert balance() == 496000
