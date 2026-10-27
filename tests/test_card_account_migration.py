import sqlite3
import pytest
from copy import deepcopy
from datetime import datetime, timezone
from bankagent.banking.storage import SQLiteStore
from bankagent.banking.data.generator import build_demo_data
from bankagent.banking.bank_backend import BankBackend
from bankagent.banking.bank_types import TrustedContext


def test_split_preserves_money_receipts_history_limits_and_is_idempotent(tmp_path):
    data = build_demo_data()
    data['cards']['card-002']['account_id'] = 'account-001'
    del data['accounts']['account-card-card-002']
    data['cards']['card-extra'] = {'account_id':'account-001','display_name':'第三卡','status':'ACTIVE'}
    data['cards']['card-002']['daily_limit_minor'] = 9000
    data['accounts']['account-001']['balance_minor'] -= 1200
    data['transactions'].append({'transaction_id':'past-card-payment','account_id':'account-001',
        'occurred_at':'2026-10-18T10:00:00+08:00','kind':'EXPENSE','amount_minor':1200,
        'category':'购物','merchant':'旧商户','subscription_id':None,'card_id':'card-002'})
    history = deepcopy(data['transactions'])
    receipts = {('user-001','account-001','old-request'): (('PAY_BY_CARD','old-fingerprint'),
        {'operation':'PAY_BY_CARD','status':'COMPLETED','data':{'transaction_id':'past-card-payment'},'error_code':None})}
    encoded, saved = SQLiteStore.encode(data, receipts)
    path = tmp_path/'old.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE bank_state (id INTEGER PRIMARY KEY,version INTEGER,data TEXT,receipts TEXT,created_at TEXT)')
        db.execute('INSERT INTO bank_state VALUES(1,2,?,?,?)',(encoded,saved,datetime.now(timezone.utc).isoformat()))
    store = SQLiteStore(path,build_demo_data())
    with store.connection() as db:
        after, done = store.load(db)
        assert db.execute('SELECT version FROM bank_state').fetchone()[0] == 3
    assert after['accounts']['account-001']['balance_minor'] == 498800
    assert after['cards']['card-001']['account_id'] == 'account-001'
    assert after['accounts']['account-card-card-002']['balance_minor'] == 0
    assert after['accounts']['account-card-card-extra']['balance_minor'] == 0
    assert after['transactions'] == history and done == receipts
    assert after['cards']['card-002']['daily_limit_minor'] == 9000
    assert sum(a['balance_minor'] for a in after['accounts'].values()) == sum(a['balance_minor'] for a in data['accounts'].values())
    again = SQLiteStore(path,build_demo_data())
    with again.connection() as db:
        assert again.load(db) == (after, done)
    bank = BankBackend(data_factory=build_demo_data,database_path=path,
        clock=lambda: datetime.fromisoformat('2026-10-18T12:00:00+08:00'))
    limits = bank.query_card_limits(context=TrustedContext('user-001','account-card-card-002','check'),card_id='card-002')
    assert limits['data']['used_today_minor'] == 1200


def test_migration_collision_rolls_back_without_resetting_original_state(tmp_path):
    data = build_demo_data()
    data['cards']['card-002']['account_id'] = 'account-001'
    # An existing independent account must never be overwritten by the migration.
    encoded, receipts = SQLiteStore.encode(data, {})
    path = tmp_path/'collision.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE bank_state (id INTEGER PRIMARY KEY,version INTEGER,data TEXT,receipts TEXT,created_at TEXT)')
        db.execute('INSERT INTO bank_state VALUES(1,2,?,?,?)', (encoded, receipts, datetime.now(timezone.utc).isoformat()))
    with pytest.raises(ValueError, match='migration collision'):
        SQLiteStore(path, build_demo_data())
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT version,data,receipts FROM bank_state').fetchone() == (2, encoded, receipts)
