from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import sqlite3
import pytest
from bankagent.banking.bank_backend import BankBackend
from bankagent.banking.bank_types import TrustedContext
from bankagent.banking.data.generator import build_demo_data
from bankagent.banking.storage import SQLiteStore
from bankagent.agent.agent_security import compute_operation_hash
from test_account_lifecycle import setup, NOW


def transfer_args(contact='contact-001', amount=4000):
    return dict(contact_id=contact, amount_minor=amount, currency='CNY')


def test_double_entry_concurrent_replay_and_receiving_query(setup):
    bank, grant, records = setup
    params = transfer_args()
    ctx = grant('TRANSFER', params)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda b: b.execute_transfer(context=ctx, **params), [bank(), bank()]))
    assert results[0] == results[1] and results[0]['status'] == 'COMPLETED'
    state = bank()._data
    assert state['accounts']['account-001']['balance_minor'] == 496000
    assert state['accounts']['account-002']['balance_minor'] == 44000
    assert sum(a['balance_minor'] for a in state['accounts'].values()) == 540000
    pair = [t for t in state['transactions'] if t.get('transfer_id') == results[0]['data']['transfer_id']]
    assert len(pair) == 2 and {t['kind'] for t in pair} == {'TRANSFER_IN', 'TRANSFER_OUT'}
    assert pair[0]['related_transaction_id'] == pair[1]['transaction_id']
    assert pair[1]['related_transaction_id'] == pair[0]['transaction_id']
    assert {t['balance_after_minor'] for t in pair} == {496000, 44000}
    q = TrustedContext('user-002', 'account-002', 'q')
    bills = bank().query_bills(context=q, start=date(2026, 10, 1), end=date(2026, 11, 1))['data']
    assert bills['total_minor'] == 0 and any(t['kind'] == 'TRANSFER_IN' for t in bills['transactions'])
    assert bank().get_balance(context=TrustedContext('user-001', 'account-002', 'q'))['status'] == 'REJECTED'
    records.clear()
    assert bank().execute_transfer(context=ctx, **params) == results[0]


def test_transfer_to_own_account_uses_same_ledger(setup):
    bank, grant, _ = setup
    b = bank()
    opened = b.open_account(context=grant('OPEN_ACCOUNT', {'display_name': '储蓄账户'}), display_name='储蓄账户')
    account = opened['data']['account_id']
    q = TrustedContext('user-001', 'account-001', 'q')
    matches = b.find_contacts(context=q, name='储蓄账户')
    params = transfer_args(matches[0]['contact_id'])
    assert b.execute_transfer(context=grant('TRANSFER', params), **params)['status'] == 'COMPLETED'
    assert bank()._data['accounts'][account]['balance_minor'] == 4000
    reverse = b.find_contacts(context=TrustedContext('user-001', account, 'q'), name='默认演示账户')
    assert reverse == [{'contact_id': 'own:account-001', 'display_name': '默认演示账户'}]
    assert sum(a['balance_minor'] for a in bank()._data['accounts'].values()) == 540000


def test_transfer_disk_failure_rolls_back_both_sides(setup, monkeypatch):
    from copy import deepcopy
    bank, grant, _ = setup
    b, params = bank(), transfer_args()
    before = deepcopy(b._data)
    ctx = grant('TRANSFER', params)
    save = b._store.save
    def fail(db, data, completed):
        save(db, data, completed)
        raise sqlite3.OperationalError('disk failure')
    monkeypatch.setattr(b._store, 'save', fail)
    with pytest.raises(sqlite3.OperationalError):
        b.execute_transfer(context=ctx, **params)
    assert bank()._data == before  # Includes persisted card numbers from the migration.
    assert bank()._completed == {}
    assert bank().execute_transfer(context=ctx, **params)['status'] == 'COMPLETED'


@pytest.mark.parametrize('target', [None, 'missing', 'account-001'])
def test_unbound_or_self_recipient_cannot_debit(setup, target):
    _, grant, records = setup
    seed = build_demo_data()
    seed['contacts']['contact-001']['recipient_account_id'] = target
    b = BankBackend(data_factory=lambda: seed, lookup_authorization=records.get,
                    operation_hash=compute_operation_hash, clock=lambda: NOW)
    params = transfer_args()
    assert b.execute_transfer(context=grant('TRANSFER', params), **params)['error_code'] == 'RECIPIENT_ACCOUNT_INVALID'
    assert b._data == seed


def test_card_limits_boundary_new_day_and_transfer_independence(setup):
    bank, grant, _ = setup
    b = bank()
    limits = dict(card_id='card-001', single_limit_minor=6000, daily_limit_minor=10000)
    b.set_card_limits(context=grant('SET_CARD_LIMITS', limits), **limits)
    def pay(amount):
        params = dict(card_id='card-001', amount_minor=amount, merchant='商店', category='购物')
        return b.pay_by_card(context=grant('PAY_BY_CARD', params), **params)
    assert pay(6001)['error_code'] == 'CARD_SINGLE_LIMIT_EXCEEDED'
    assert pay(6000)['status'] == 'COMPLETED'
    assert pay(4001)['error_code'] == 'CARD_DAILY_LIMIT_EXCEEDED'
    assert pay(4000)['status'] == 'COMPLETED'
    q = TrustedContext('user-001', 'account-001', 'q')
    assert bank().query_card_limits(context=q, card_id='card-001')['data']['used_today_minor'] == 10000
    assert b.query_card_limits(context=TrustedContext('user-001', 'account-card-card-002', 'q'), card_id='card-002')['data']['used_today_minor'] == 0
    b._clock = lambda: NOW + timedelta(days=1)
    assert b.query_card_limits(context=q, card_id='card-001')['data']['used_today_minor'] == 0
    b._clock = lambda: NOW
    limits.update(single_limit_minor=0, daily_limit_minor=0)
    b.set_card_limits(context=grant('SET_CARD_LIMITS', limits), **limits)
    assert pay(1)['error_code'] == 'CARD_SINGLE_LIMIT_EXCEEDED'
    params = transfer_args()
    assert b.execute_transfer(context=grant('TRANSFER', params), **params)['status'] == 'COMPLETED'


def test_concurrent_payments_respect_daily_limit(setup):
    bank, grant, _ = setup
    limits = dict(card_id='card-001', single_limit_minor=6000, daily_limit_minor=10000)
    bank().set_card_limits(context=grant('SET_CARD_LIMITS', limits), **limits)
    params = dict(card_id='card-001', amount_minor=6000, merchant='商店', category='购物')
    calls = [(bank(), grant('PAY_BY_CARD', params)) for _ in range(2)]
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda c: c[0].pay_by_card(context=c[1], **params), calls))
    assert sorted(r['status'] for r in replies) == ['COMPLETED', 'REJECTED']
    assert bank()._data['accounts']['account-001']['balance_minor'] == 494000


def test_limit_updates_require_owned_card_and_valid_authorization(setup):
    bank, grant, records = setup
    params = dict(card_id='card-003', single_limit_minor=1000, daily_limit_minor=2000)
    assert bank().set_card_limits(context=grant('SET_CARD_LIMITS', params), **params)['error_code'] == 'CARD_NOT_ACCESSIBLE'
    params['card_id'] = 'card-001'
    ctx = grant('SET_CARD_LIMITS', params)
    records.clear()
    assert bank().set_card_limits(context=ctx, **params)['error_code'] == 'AUTHORIZATION_INVALID'
    assert bank()._data == build_demo_data()


def test_v1_upgrade_preserves_old_outgoing_and_receipt(tmp_path, setup):
    _, grant, records = setup
    params = transfer_args()
    ctx = grant('TRANSFER', params)
    seed = build_demo_data()
    seed['accounts'].pop('account-003')
    for contact in seed['contacts'].values():
        contact.pop('recipient_account_id')
    seed['accounts']['account-001']['balance_minor'] -= 4000
    seed['transactions'].append(dict(transaction_id='old', account_id='account-001',
        occurred_at=NOW.isoformat(), kind='TRANSFER_OUT', amount_minor=4000,
        category='转账', merchant=None, subscription_id=None))
    receipt = dict(operation='TRANSFER', status='COMPLETED', error_code=None,
        data=dict(transaction_id='old', recipient='张伟', amount_minor=4000, currency='CNY', remaining_balance_minor=496000))
    key = (ctx.user_id, ctx.account_id, ctx.idempotency_key)
    saved = {key: ((ctx.request_id, 'TRANSFER', 'contact-001', 4000, 'CNY'), receipt)}
    path = tmp_path / 'legacy.sqlite3'
    store = SQLiteStore(path, seed)
    with store.connection() as db:
        store.save(db, seed, saved)
        db.execute('UPDATE bank_state SET version=1')
    for _ in range(2):
        b = BankBackend(data_factory=build_demo_data, database_path=path, lookup_authorization=records.get,
                        operation_hash=compute_operation_hash, clock=lambda: NOW)
        assert b._data['accounts']['account-002']['balance_minor'] == 40000
        assert b._data['accounts']['account-003']['balance_minor'] == 0
        assert len(b._data['transactions']) == len(seed['transactions'])
        assert b.execute_transfer(context=ctx, **params) == receipt
    with store.connection() as db:
        assert db.execute('SELECT version FROM bank_state').fetchone()[0] == 3
