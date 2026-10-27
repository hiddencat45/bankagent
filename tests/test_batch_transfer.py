"""Atomic batch acceptance: scripted model, real authorization/ledger/HTTP/SQLite."""
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from bankagent.api.server import create_app
from bankagent.banking import bank_backend
from bankagent.banking.bank_types import TrustedContext, WriteContext
from bankagent.banking.storage import SQLiteStore
from test_api_http import login, chat, decision
from test_query_loop import Scripted, call, answer, CLOCK
from test_task_loop import pending, receipts
from desktop.client import business_confirmation, query_result


def batch(amount='40', other='25', ident='b1', rows=None):
    return call('prepare_batch_transfer', {'items': rows if rows is not None else [
        {'recipient_name': '张伟', 'amount': amount}, {'recipient_name': '李娜', 'amount': other}]}, ident)


def app(model, path=None, authenticate=None):
    return TestClient(create_app(demo=True, clock=CLOCK, query_model=model, database_path=path,
                                 authenticate=authenticate), base_url='http://localhost')


def balances():
    return [bank_backend.get_balance(context=TrustedContext(f'user-00{i}', f'account-00{i}', 'check'))['data']['balance_minor'] for i in (1, 2, 3)]


def history(c, auth):
    response = c.get('/bank/transfer-batches', headers=auth)
    assert response.status_code == 200
    return response.json()


def batch_result(out):
    return next(row for row in receipts(out) if row['operation'] == 'BATCH_TRANSFER')


def test_all_success_single_confirmation_lost_response_repeat_and_restart(tmp_path):
    path = tmp_path / 'bank.sqlite3'
    model = Scripted(batch(), call('query_transfer_batches', {}, 'r'), answer('实际回执如下。'))
    with app(model, path) as c:
        auth = login(c)
        before = balances()
        first = chat(c, auth, message='给张伟40元，李娜25元，一起确认后查回执')
        card = business_confirmation(first)
        assert len([n for n, _ in first if n == 'interrupt']) == 1
        assert card['total_minor'] == 6500 and '张伟' in card['summary'] and '李娜' in card['summary']
        assert '全有或全无' in card['summary']
        assert balances() == before
        # The first response can be lost after commit; resubmit the exact decision.
        first_response = decision(c, auth, *pending(first))
        again = decision(c, auth, *pending(first))
        assert first_response == again
        actual = batch_result(again)
        assert actual['data']['committed'] is True
        assert balances() == [493500, before[1] + 4000, before[2] + 2500]
        assert len(actual['data']['items']) == 2
        record = history(c, auth)
        assert record['data']['receipts'] == [actual]
        assert '成功' in query_result(record)
        bills = c.get('/bank/bills', headers=auth).json()['data']['transactions']
        assert len([r for r in bills if r.get('batch_id') == actual['data']['batch_id']]) == 2
    with app(None, path) as restarted:
        auth = login(restarted)
        assert history(restarted, auth) == record
        assert '张伟' in query_result(history(restarted, auth)) and '流水' in query_result(record)
        assert balances()[0] == 493500
        assert restarted.get('/bank/transfer-batches').status_code == 401
        second = restarted.post('/demo/customer-session', headers=auth, json={'customer_ref': 'zhang-wei'})
        other_auth = {'Authorization': 'Bearer ' + second.json()['token']}
        assert history(restarted, other_auth)['data']['receipts'] == []


    # A fresh child process also exposes the same persisted receipt over actual HTTP.
    from desktop.app import LocalService
    from desktop.client import QueryClient
    from test_desktop import offline_env
    service = LocalService(env={**offline_env(), 'BANKAGENT_DB_PATH': str(path)})
    try:
        client = QueryClient(service.start())
        client.connect()
        visible = client.transfer_batches()
        assert actual['data']['batch_id'] in visible
        assert '张伟' in visible and '李娜' in visible and '成功' in visible
    finally:
        service.close()


def test_second_insufficient_rejects_whole_batch_and_persists_rejection(tmp_path):
    path = tmp_path / 'rejected.sqlite3'
    with app(Scripted(batch('4000', '2000')), path, authenticate=lambda *a: True) as c:
        auth = login(c)
        before = balances()
        first = chat(c, auth, message='给张伟4000，李娜2000')
        assert first[-1][1]['status'] == 'AWAITING_AUTHENTICATION'
        out = decision(c, auth, *pending(first))
        result = batch_result(out)
        assert result['status'] == 'REJECTED' and result['error_code'] == 'INSUFFICIENT_BALANCE'
        assert [r['status'] for r in result['data']['items']] == ['NOT_EXECUTED', 'FAILED']
        assert balances() == before
        assert '全部款项均未扣除' in query_result(result)
        assert decision(c, auth, *pending(first)) == out
        assert not any(t.get('batch_id') for t in c.get('/bank/bills', headers=auth).json()['data']['transactions'])
    with app(None, path) as c:
        assert history(c, login(c))['data']['receipts'] == [result]
        assert balances() == before


def test_cancel_and_modified_list_never_reuse_approval():
    model = Scripted(batch(), batch('30', ident='b2'))
    with app(model) as c:
        auth = login(c)
        before = balances()
        first = chat(c, auth, message='张伟40李娜25')
        revised = chat(c, auth, thread_id=pending(first)[0], message='张伟改成30，李娜不变')
        assert business_confirmation(revised)['total_minor'] == 5500
        stale = c.post('/agent/chat', headers=auth, json={'thread_id': pending(first)[0],
                       'resume': {'challenge_id': pending(first)[1]['challenge_id'], 'decision': 'approve'}})
        assert stale.status_code == 409
        out = decision(c, auth, *pending(revised), value='reject')
        assert all(r['status'] == 'NOT_EXECUTED' for r in batch_result(out)['data']['items'])
        assert balances() == before and history(c, auth)['data']['receipts'] == []


def test_only_missing_item_is_asked_then_preserves_complete_list():
    model = Scripted(batch(rows=[{'recipient_name': '张伟', 'amount': '40'}, {'amount': '25'}]), batch(ident='b2'))
    with app(model) as c:
        auth = login(c)
        first = chat(c, auth, message='给张伟40，另一个人25')
        text = ' '.join(d.get('text', '') for _, d in first)
        assert first[-1][1]['status'] == 'NEEDS_CLARIFICATION'
        assert '第2项' in text and '第1项' not in text
        second = chat(c, auth, thread_id=first[0][1]['thread_id'], message='另一个是李娜')
        assert business_confirmation(second)['total_minor'] == 6500
        assert any('第2项' in (m.get('content') or '') for m in model.requests[1])
        assert balances()[0] == 500000


def test_batch_cannot_bypass_high_risk_authentication():
    with app(Scripted(batch('600', '500'))) as c:
        auth = login(c)
        first = chat(c, auth, message='张伟600李娜500')
        assert business_confirmation(first)['risk_level'] == 'RED'
        out = c.post('/agent/chat', headers=auth, json={'thread_id': pending(first)[0],
            'resume': {'challenge_id': pending(first)[1]['challenge_id'], 'decision': 'approve'}})
        assert out.status_code == 409 and balances()[0] == 500000


@pytest.mark.parametrize('after_save', [False, True])
def test_sqlite_save_failure_leaves_no_partial_ledger_and_safe_retry(tmp_path, monkeypatch, after_save):
    model = Scripted(batch(), answer('整批回执如下。'))
    with app(model, tmp_path / 'rollback.sqlite3') as c:
        auth = login(c)
        before = balances()
        first = chat(c, auth, message='张伟40李娜25')
        original = SQLiteStore.save
        def fail(self, db, data, completed):
            if after_save:
                original(self, db, data, completed)
            raise OSError('injected transaction failure')
        monkeypatch.setattr(SQLiteStore, 'save', fail)
        failed = decision(c, auth, *pending(first))
        assert failed[-1][1]['status'] == 'FAILED'
        monkeypatch.setattr(SQLiteStore, 'save', original)
        assert balances() == before and history(c, auth)['data']['receipts'] == []
        done = decision(c, auth, *pending(first))
        assert batch_result(done)['data']['committed']
        assert balances()[0] == 493500
        decision(c, auth, *pending(first))
        assert balances()[0] == 493500


def test_batch_backend_rejects_parameter_tampering_and_replays_after_restart(tmp_path):
    path = tmp_path / 'bound.sqlite3'
    with app(Scripted(batch(), answer('已完成。')), path) as c:
        auth = login(c)
        first = chat(c, auth, message='张伟40李娜25')
        service = c.app.state.service
        rec = service.challenges.lookup(pending(first)[1]['challenge_id'])
        ctx = WriteContext(rec['user_id'], rec['account_id'], rec['request_id'],
                           authorization_ref=rec['challenge_id'], idempotency_key=rec['idempotency_key'])
        assert bank_backend.execute_transfer_batch(context=ctx, **rec['params'])['status'] == 'REJECTED'
        done = decision(c, auth, *pending(first))
        actual = batch_result(done)
    with app(None, path):
        assert bank_backend.execute_transfer_batch(context=ctx, **rec['params']) == actual
        changed = deepcopy(rec['params'])
        changed['items'][1]['amount_minor'] += 1
        assert bank_backend.execute_transfer_batch(context=ctx, **changed)['error_code'] == 'IDEMPOTENCY_CONFLICT'
        assert balances()[0] == 493500

def test_risk_increases_after_confirmation_rejects_every_item():
    from test_task_loop import prepare
    model = Scripted(batch('100', '100'), prepare('900', ident='single'), answer('单笔完成。'))
    with app(model) as c:
        auth = login(c)
        first = chat(c, auth, message='张伟100李娜100')
        assert business_confirmation(first)['risk_level'] == 'YELLOW'
        single = chat(c, auth, message='另给张伟900元')
        decision(c, auth, *pending(single))
        before_batch = balances()
        result = batch_result(decision(c, auth, *pending(first)))
        assert result['error_code'] == 'REAUTHORIZATION_REQUIRED'
        assert balances() == before_batch
        assert all(row['status'] != 'COMPLETED' for row in result['data']['items'])


@pytest.mark.parametrize('change', [lambda row: row.update(total_minor=1),
                                   lambda row: row.update(atomic=False),
                                   lambda row: row['items'][0].update(amount_minor=-1)])
def test_desktop_rejects_inconsistent_batch_confirmation(change):
    with app(Scripted(batch())) as c:
        first = chat(c, login(c), message='张伟40李娜25')
        row = next(d['payload'] for n, d in first if n == 'card' and d['type'] == 'confirm')
        change(row)
        with pytest.raises(ValueError):
            business_confirmation(first)
        assert balances()[0] == 500000


def test_concurrent_approval_cannot_pay_batch_twice():
    from concurrent.futures import ThreadPoolExecutor
    with app(Scripted(batch(), answer('完成。'))) as c:
        auth = login(c)
        first = chat(c, auth, message='张伟40李娜25')
        thread, intr = pending(first)
        def approve():
            return c.post('/agent/chat', headers=auth, json={'thread_id': thread,
                'resume': {'challenge_id': intr['challenge_id'], 'decision': 'approve'}}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: approve(), range(2)))
        assert 200 in statuses and set(statuses) <= {200, 409}
        assert balances()[0] == 493500
        assert len(history(c, auth)['data']['receipts']) == 1


@pytest.mark.parametrize('persistent', [False, True])
def test_exception_during_second_post_cannot_publish_first(tmp_path, monkeypatch, persistent):
    path = tmp_path / 'post.sqlite3' if persistent else None
    with app(Scripted(batch()), path) as c:
        auth = login(c)
        before = balances()
        first = chat(c, auth, message='张伟40李娜25')
        original = bank_backend.BankBackend._post_transfer
        count = []
        def broken(self, *args, **kwargs):
            count.append(1)
            if len(count) == 2:
                raise OSError('second staged posting failed')
            return original(self, *args, **kwargs)
        monkeypatch.setattr(bank_backend.BankBackend, '_post_transfer', broken)
        out = decision(c, auth, *pending(first))
        assert out[-1][1]['status'] == 'FAILED'
        assert balances() == before and history(c, auth)['data']['receipts'] == []
        assert not any(t.get('batch_id') for t in c.get('/bank/bills', headers=auth).json()['data']['transactions'])

def test_batch_does_not_accept_non_string_idempotency_key():
    with app(None):
        ctx = WriteContext('user-001', 'account-001', 'request', authorization_ref='unknown', idempotency_key=True)
        result = bank_backend.execute_transfer_batch(context=ctx, items=[
            {'contact_id': 'contact-001', 'amount_minor': 4000, 'currency': 'CNY'},
            {'contact_id': 'contact-002', 'amount_minor': 2500, 'currency': 'CNY'}])
        assert result['error_code'] == 'AUTHORIZATION_INVALID'
        assert balances()[0] == 500000
