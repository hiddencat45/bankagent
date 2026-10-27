from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
import sqlite3

from bankagent.banking.bank_backend import BankBackend
from bankagent.banking.bank_types import TrustedContext, WriteContext
from bankagent.banking.data.generator import build_demo_data
from bankagent.agent.agent_security import compute_operation_hash

NOW = datetime(2026, 10, 18, 12, tzinfo=timezone(timedelta(hours=8)))


@pytest.fixture
def setup(tmp_path):
    records = {}
    path = tmp_path / 'bank.sqlite3'
    def bank():
        return BankBackend(data_factory=build_demo_data, database_path=path,
            lookup_authorization=records.get, operation_hash=compute_operation_hash, clock=lambda: NOW)
    def grant(operation, params, account='account-001', user='user-001'):
        request = uuid4().hex
        ctx = WriteContext(user, account, request, 'auth-' + request, 'key-' + request)
        records[ctx.authorization_ref] = dict(user_id=user, account_id=account, request_id=request,
            idempotency_key=ctx.idempotency_key, operation=operation, params=params, decision='APPROVED',
            challenge_id='ch-' + request, risk_level='YELLOW', expires_at=NOW + timedelta(minutes=5),
            operation_hash=compute_operation_hash(TrustedContext(user, account, request), operation, params))
        return ctx
    return bank, grant, records


def test_account_card_payment_freeze_unfreeze_restart(setup):
    bank, grant, records = setup
    b = bank()
    opened = b.open_account(context=grant('OPEN_ACCOUNT', {'display_name': '消费账户'}), display_name='消费账户')
    assert opened['status'] == 'COMPLETED'
    account = opened['data']['account_id']
    assert opened['data']['funding_source'] == 'DEMO_CREDIT'
    q = TrustedContext('user-001', account, 'query')
    issue_params = {'display_name': '新借记卡'}
    issued = b.issue_debit_card(context=grant('ISSUE_DEBIT_CARD', issue_params, account), **issue_params)
    card = issued['data']['card_id']
    assert issued['data']['status'] == 'PENDING_ACTIVATION'
    payment = dict(card_id=card, amount_minor=12000, merchant='演示商店', category='购物')
    pay_context = grant('PAY_BY_CARD', payment, account)
    assert b.pay_by_card(context=pay_context, **payment)['error_code'] == 'CARD_NOT_ACTIVE'
    for operation, method in [('FREEZE_CARD', b.freeze_card), ('UNFREEZE_CARD', b.unfreeze_card)]:
        assert method(context=grant(operation, {'card_id': card}, account), card_id=card)['error_code'] == 'CARD_NOT_ACTIVE'
    assert b.activate_debit_card(context=grant('ACTIVATE_DEBIT_CARD', {'card_id': card}, account), card_id=card)['status'] == 'COMPLETED'
    paid = b.pay_by_card(context=pay_context, **payment)
    assert paid['data']['remaining_balance_minor'] == 88000
    assert b.freeze_card(context=grant('FREEZE_CARD', {'card_id': card}, account), card_id=card)['status'] == 'COMPLETED'
    next_pay = grant('PAY_BY_CARD', payment, account)
    assert b.pay_by_card(context=next_pay, **payment)['error_code'] == 'CARD_NOT_ACTIVE'
    assert b.activate_debit_card(context=grant('ACTIVATE_DEBIT_CARD', {'card_id': card}, account), card_id=card)['error_code'] == 'CARD_NOT_PENDING_ACTIVATION'
    assert b.unfreeze_card(context=grant('UNFREEZE_CARD', {'card_id': card}, account), card_id=card)['status'] == 'COMPLETED'
    assert b.pay_by_card(context=next_pay, **payment)['data']['remaining_balance_minor'] == 76000
    records.clear()
    reopened = bank()
    assert reopened.pay_by_card(context=pay_context, **payment) == paid
    assert reopened.get_balance(context=q)['data']['balance_minor'] == 76000
    bills = reopened.query_bills(context=q, start=date(2026, 10, 1), end=date(2026, 11, 1))['data']
    assert bills['total_minor'] == 24000
    assert len(bills['transactions']) == 3
    assert reopened.query_cards(context=q)['data']['cards'][0]['status'] == 'ACTIVE'


@pytest.mark.parametrize('change', ['decision', 'expiry', 'hash', 'params', 'risk', 'user'])
def test_opening_requires_bound_valid_authorization(setup, change):
    bank, grant, records = setup
    ctx = grant('OPEN_ACCOUNT', {'display_name': '新账户'})
    record = records[ctx.authorization_ref]
    field, value = {'decision': ('decision', 'REJECTED'), 'expiry': ('expires_at', NOW),
        'hash': ('operation_hash', 'wrong'), 'params': ('params', {'display_name': '其他'}),
        'risk': ('risk_level', 'GREEN'), 'user': ('user_id', 'user-002')}[change]
    record[field] = value
    b = bank()
    before = deepcopy(b._data)
    assert b.open_account(context=ctx, display_name='新账户')['error_code'] == 'AUTHORIZATION_INVALID'
    assert bank()._data == before


def test_concurrent_opening_is_idempotent(setup):
    bank, grant, _ = setup
    ctx = grant('OPEN_ACCOUNT', {'display_name': '新账户'})
    a, b = bank(), bank()
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda item: item.open_account(context=ctx, display_name='新账户'), [a, b]))
    assert replies[0] == replies[1]
    assert len(bank()._data['accounts']) == len(build_demo_data()['accounts']) + 1
    assert b.open_account(context=ctx, display_name='变更名称')['error_code'] == 'IDEMPOTENCY_CONFLICT'


def test_payment_ownership_amount_and_funds(setup):
    bank, grant, _ = setup
    b = bank()
    params = dict(card_id='card-003', amount_minor=100, merchant='演示商店', category='其他')
    assert b.pay_by_card(context=grant('PAY_BY_CARD', params), **params)['error_code'] == 'CARD_NOT_ACCESSIBLE'
    params['card_id'] = 'card-001'
    valid_context = grant('PAY_BY_CARD', dict(params))
    for amount in [True, 0, -1, 0.1]:
        params['amount_minor'] = amount
        assert b.pay_by_card(context=valid_context, **params)['error_code'] == 'INVALID_AMOUNT'
    params['amount_minor'] = 500001
    assert b.pay_by_card(context=grant('PAY_BY_CARD', params), **params)['error_code'] == 'INSUFFICIENT_BALANCE'
    assert bank()._data == build_demo_data()


def test_second_card_requires_another_account_without_creating_money(setup):
    bank, grant, _ = setup
    before = deepcopy(bank()._data)
    params = {'display_name':'第二张普通卡'}
    result = bank().issue_debit_card(context=grant('ISSUE_DEBIT_CARD', params), **params)
    assert result['error_code'] == 'ACCOUNT_ALREADY_HAS_CARD'
    assert bank()._data == before


def test_concurrent_payments_cannot_overdraw(setup):
    bank, grant, _ = setup
    params = dict(card_id='card-001', amount_minor=300000, merchant='演示商店', category='购物')
    calls = [(bank(), grant('PAY_BY_CARD', params)) for _ in range(2)]
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda call: call[0].pay_by_card(context=call[1], **params), calls))
    assert sorted(r['status'] for r in replies) == ['COMPLETED', 'REJECTED']
    assert bank().get_balance(context=TrustedContext('user-001', 'account-001', 'q'))['data']['balance_minor'] == 200000


def test_failed_opening_commit_leaves_no_account_or_receipt(setup, monkeypatch):
    bank, grant, _ = setup
    b = bank()
    ctx = grant('OPEN_ACCOUNT', {'display_name': '新账户'})
    save = b._store.save
    def fail(db, data, completed):
        save(db, data, completed)
        raise sqlite3.OperationalError('injected disk failure')
    monkeypatch.setattr(b._store, 'save', fail)
    with pytest.raises(sqlite3.OperationalError):
        b.open_account(context=ctx, display_name='新账户')
    reopened = bank()
    assert reopened._data == build_demo_data()
    assert reopened._completed == {}
    assert reopened.open_account(context=ctx, display_name='新账户')['status'] == 'COMPLETED'
    assert len(bank()._data['accounts']) == len(build_demo_data()['accounts']) + 1


def test_pending_card_query_render():
    from bankagent.agent.scenarios.card import render
    assert '待激活' in render(dict(operation='QUERY_CARDS', status='COMPLETED', error_code=None,
        data={'cards': [{'card_id': 'new', 'display_name': '新卡', 'status': 'PENDING_ACTIVATION'}]}))
