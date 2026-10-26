"""Persistence uses temporary databases, never the user's desktop ledger."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone, date
import sqlite3
import os
from pathlib import Path
import subprocess
import sys

import pytest

from bankagent.banking.bank_backend import BankBackend
from bankagent.banking.bank_types import TrustedContext, WriteContext
from bankagent.banking.data.generator import build_demo_data
from bankagent.agent.agent_security import compute_operation_hash

NOW = datetime(2026, 10, 18, 12, tzinfo=timezone(timedelta(hours=8)))
QUERY = TrustedContext('user-001', 'account-001', 'query')


def backend(path, records=None):
    return BankBackend(data_factory=build_demo_data, database_path=path,
        lookup_authorization=(records or {}).get, operation_hash=compute_operation_hash,
        clock=lambda: NOW)


def grant(request='r1', operation='TRANSFER', params=None):
    params = params or {'contact_id': 'contact-001', 'amount_minor': 4000, 'currency': 'CNY'}
    ctx = WriteContext('user-001', 'account-001', request, 'auth-' + request, 'key-' + request)
    record = dict(user_id=ctx.user_id, account_id=ctx.account_id, request_id=request,
        idempotency_key=ctx.idempotency_key, operation=operation, params=params,
        decision='APPROVED', challenge_id='challenge-' + request, risk_level='YELLOW',
        expires_at=NOW + timedelta(minutes=5),
        operation_hash=compute_operation_hash(QUERY.__class__(ctx.user_id, ctx.account_id, request), operation, params))
    return ctx, {ctx.authorization_ref: record}


def transfer(bank, ctx, amount=4000):
    return bank.execute_transfer(context=ctx, contact_id='contact-001', amount_minor=amount)


def test_reopen_keeps_ledger_and_receipt_without_reauthorizing(tmp_path):
    path = tmp_path / 'bank.sqlite3'
    ctx, records = grant()
    first = transfer(backend(path, records), ctx)
    assert first['status'] == 'COMPLETED'
    reopened = backend(path)  # No pending authorizations survive restart.
    assert reopened.get_balance(context=QUERY)['data']['balance_minor'] == 496000
    assert transfer(reopened, ctx) == first
    assert transfer(reopened, ctx, 5000)['error_code'] == 'IDEMPOTENCY_CONFLICT'
    assert transfer(reopened, replace(ctx, idempotency_key='new-key'))['error_code'] == 'AUTHORIZATION_INVALID'
    bills = reopened.query_bills(context=QUERY, start=date(2026, 10, 1), end=date(2026, 11, 1))
    assert len([t for t in bills['data']['transactions'] if t['kind'] == 'TRANSFER_OUT']) == 1
    # Transfers must not break subscription history queries.
    assert reopened.query_subscriptions(context=QUERY, start=date(2026, 10, 1),
        end=date(2026, 11, 1))['status'] == 'COMPLETED'


def test_two_instances_serialize_duplicate_and_distinct_writes(tmp_path):
    path = tmp_path / 'bank.sqlite3'
    ctx, records = grant()
    ctx2, records2 = grant('r2')
    records.update(records2)
    a, b = backend(path, records), backend(path, records)
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda bank: transfer(bank, ctx), [a, b]))
    assert replies[0] == replies[1]
    assert transfer(b, ctx2)['status'] == 'COMPLETED'
    assert a.get_balance(context=QUERY)['data']['balance_minor'] == 492000


def test_failed_commit_rolls_back_ledger_and_receipts(tmp_path, monkeypatch):
    path = tmp_path / 'bank.sqlite3'
    ctx, records = grant()
    bank = backend(path, records)
    save = bank._store.save
    def fail(db, data, completed):
        save(db, data, completed)
        raise sqlite3.OperationalError('injected disk failure')
    monkeypatch.setattr(bank._store, 'save', fail)
    with pytest.raises(sqlite3.OperationalError):
        transfer(bank, ctx)
    reopened = backend(path, records)
    assert reopened.get_balance(context=QUERY)['data']['balance_minor'] == 500000
    assert transfer(reopened, ctx)['status'] == 'COMPLETED'
    assert reopened.get_balance(context=QUERY)['data']['balance_minor'] == 496000


@pytest.mark.parametrize('operation,params,method,collection,key,field,expected', [
    ('FREEZE_CARD', {'card_id': 'card-001'}, 'freeze_card', 'cards', 'card-001', 'status', 'FROZEN'),
    ('PAUSE_SUBSCRIPTION', {'subscription_id': 'sub-001'}, 'pause_subscription', 'subscriptions', 'sub-001', 'status', 'PAUSED'),
])
def test_nonfinancial_state_and_reset_persist(tmp_path, operation, params, method, collection, key, field, expected):
    path = tmp_path / 'bank.sqlite3'
    ctx, records = grant(operation=operation, params=params)
    first = getattr(backend(path, records), method)(context=ctx, **params)
    reopened = backend(path)
    assert reopened._data[collection][key][field] == expected
    assert getattr(reopened, method)(context=ctx, **params) == first
    reopened.reset_demo_data()
    fresh = backend(path)
    assert fresh._data == build_demo_data()
    assert not fresh._completed


def test_unknown_database_not_overwritten(tmp_path):
    path = tmp_path / 'bank.sqlite3'
    backend(path)
    with sqlite3.connect(path) as db:
        db.execute('UPDATE bank_state SET version=99')
    before = path.read_bytes()
    with pytest.raises(ValueError, match='version'):
        backend(path)
    assert path.read_bytes() == before


def test_existing_empty_database_not_silently_reseeded(tmp_path):
    path = tmp_path / 'bank.sqlite3'
    path.touch()
    with pytest.raises(ValueError, match='schema'):
        backend(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []


def test_business_clock_anchor_survives_restart(tmp_path):
    from bankagent.banking.storage import SQLiteStore
    path = tmp_path / 'bank.sqlite3'
    store = SQLiteStore(path, build_demo_data())
    with sqlite3.connect(path) as db:
        db.execute('UPDATE bank_state SET created_at=?',
                   ((datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),))
    reopened = SQLiteStore(path, build_demo_data())
    assert reopened.business_now().date() == date(2026, 10, 20)


def test_process_crash_before_commit_keeps_previous_snapshot(tmp_path):
    path = tmp_path / 'bank.sqlite3'
    ctx, records = grant()
    receipt = transfer(backend(path, records), ctx)
    script = '''
import os, sys
from bankagent.banking.storage import SQLiteStore
from bankagent.banking.data.generator import build_demo_data
store = SQLiteStore(sys.argv[1], build_demo_data())
with store.connection() as db:
    data, completed = store.load(db)
    data['accounts']['account-001']['balance_minor'] = 0
    store.save(db, data, {})
    os._exit(7)
'''
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    result = subprocess.run([sys.executable, '-c', script, str(path)], env=env,
                            capture_output=True, timeout=20)
    assert result.returncode == 7
    reopened = backend(path)
    assert reopened.get_balance(context=QUERY)['data']['balance_minor'] == 496000
    assert transfer(reopened, ctx) == receipt
