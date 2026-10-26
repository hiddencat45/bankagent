"""后端隔离测试：独立小样例与服务端授权替身，不依赖尚待审的 PR #7。"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from threading import RLock

import pytest
import bankagent.banking.bank_backend as module
from bankagent.banking.bank_backend import BankBackend
from bankagent.banking.bank_types import (MAX_BILL_TRANSACTIONS, TRANSFER_SINGLE_LIMIT_MINOR,
                        YELLOW_DAILY_LIMIT_MINOR, TrustedContext, WriteContext)


def sample_data():
    rows = [("t0", "a1", "2026-10-01T09:00:00+08:00", "INCOME", 505000),
            ("t1", "a1", "2026-10-12T10:00:00+08:00", "EXPENSE", 2500),
            ("t2", "a1", "2026-10-12T10:00:30+08:00", "EXPENSE", 2500),
            ("t3", "a2", "2026-10-01T09:00:00+08:00", "INCOME", 40000)]
    return {"accounts": {"a1": {"user_id": "u1", "balance_minor": 500000, "currency": "CNY"},
                         "a2": {"user_id": "u2", "balance_minor": 40000, "currency": "CNY"}},
            "contacts": {"c1": {"user_id": "u1", "display_name": "演示收款人", "recipient_account_id": "a2"},
                         "c2": {"user_id": "u2", "display_name": "其他用户联系人"}},
            "transactions": [dict(transaction_id=i, account_id=a, occurred_at=t,
                kind=k, amount_minor=m, category="订阅" if k == "EXPENSE" else "工资",
                merchant="演示商户") for i, a, t, k, m in rows]}


def test_hash(context, operation, params):
    payload = [context.user_id, context.account_id, context.request_id, operation, params]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


test_hash.__test__ = False  # 哈希是服务端测试替身，不是生产算法或 pytest 测试。


@pytest.fixture
def service():
    clock = [datetime(2026, 10, 18, 9, tzinfo=timezone(timedelta(hours=8)))]
    records = {}
    backend = BankBackend(data_factory=sample_data, lookup_authorization=records.get,
                          operation_hash=test_hash, lock=RLock(), clock=lambda: clock[0])
    def grant(amount=30000, risk="YELLOW", request="r1", contact="c1"):
        context = WriteContext("u1", "a1", request, "ref-" + request, "key-" + request)
        params = {"contact_id": contact, "amount_minor": amount, "currency": "CNY"}
        records[context.authorization_ref] = dict(user_id="u1", account_id="a1",
            request_id=request, operation="TRANSFER", params=params,
            operation_hash=test_hash(context, "TRANSFER", params), challenge_id="ch-" + request,
            risk_level=risk, decision="APPROVED", expires_at=clock[0] + timedelta(minutes=5),
            idempotency_key=context.idempotency_key)
        return context
    return backend, grant, records, clock


def transfer(backend, context, amount=30000, **kwargs):
    return backend.execute_transfer(context=context, contact_id="c1", amount_minor=amount, **kwargs)


def bills(backend, context):
    return backend.query_bills(context=context, start=date(2026, 10, 1), end=date(2026, 11, 1))


def test_queries_are_scoped_and_outputs_do_not_mutate_storage(service):
    backend, _, _, _ = service
    ctx = TrustedContext("u1", "a1", "query")
    result = bills(backend, ctx)
    assert result["status"] == "COMPLETED" and result["error_code"] is None
    data = result["data"]
    assert data["total_minor"] == 5000 and data["by_category"] == {"订阅": 5000}
    assert data["top_category"] == "订阅"
    assert data["anomalies"] == [{"type": "POSSIBLE_DUPLICATE", "evidence": ["t1", "t2"]}]
    assert [t["transaction_id"] for t in data["transactions"]] == ["t0", "t1", "t2"]
    assert all("account_id" not in t for t in data["transactions"])
    data["transactions"][0]["amount_minor"] = 1
    assert bills(backend, ctx)["data"]["transactions"][0]["amount_minor"] == 505000
    assert backend.find_contacts(context=ctx, name="演示收款人") == [
        {"contact_id": "c1", "display_name": "演示收款人"}]
    assert backend.find_contacts(context=ctx, name="其他用户联系人") == []
    foreign = TrustedContext("u1", "a2", "foreign")
    assert backend.get_balance(context=foreign)["error_code"] == "ACCOUNT_NOT_ACCESSIBLE"
    assert bills(backend, foreign)["error_code"] == "ACCOUNT_NOT_ACCESSIBLE"
    with pytest.raises(PermissionError):
        backend.find_contacts(context=foreign, name="其他用户联系人")


def test_dates_empty_range_and_cap():
    backend = BankBackend(data_factory=sample_data)
    ctx = TrustedContext("u1", "a1", "query")
    empty = backend.query_bills(context=ctx, start=date(2026, 9, 1), end=date(2026, 10, 1))["data"]
    assert empty["total_minor"] == 0 and empty["top_category"] is None
    assert empty["by_category"] == {} and empty["transactions"] == []
    for start, end in [(date(2026, 10, 1), date(2026, 10, 1)),
                       (date(2025, 1, 1), date(2026, 10, 1)), ("本月", date(2026, 11, 1))]:
        assert backend.query_bills(context=ctx, start=start, end=end)["error_code"] == "INVALID_DATE_RANGE"
    data = sample_data()
    prototype = data["transactions"][0]
    data["transactions"] = [{**prototype, "transaction_id": str(i)} for i in range(MAX_BILL_TRANSACTIONS)]
    capped = BankBackend(data_factory=lambda: data)
    assert len(bills(capped, ctx)["data"]["transactions"]) == MAX_BILL_TRANSACTIONS
    data["transactions"].append({**prototype, "transaction_id": "extra"})
    over = bills(BankBackend(data_factory=lambda: data), ctx)
    assert over == {"operation": "QUERY_BILLS", "status": "REJECTED", "data": None,
                    "error_code": "TOO_MANY_TRANSACTIONS"}


@pytest.mark.parametrize("field,value", [
    ("decision", "REJECTED"), ("operation", "GET_BALANCE"), ("user_id", "u2"),
    ("account_id", "a2"), ("request_id", "different"), ("idempotency_key", "different"),
    ("operation_hash", "wrong"), ("params", {}), ("risk_level", "GREEN"), ("challenge_id", ""),
])
def test_bad_server_authorization_cannot_change_money(service, field, value):
    backend, grant, records, _ = service
    ctx = grant()
    records[ctx.authorization_ref][field] = value
    assert transfer(backend, ctx)["error_code"] == "AUTHORIZATION_INVALID"
    assert backend.get_balance(context=ctx)["data"]["balance_minor"] == 500000
    assert len(bills(backend, ctx)["data"]["transactions"]) == 3


def test_authorization_expiry_replay_and_idempotency_conflict(service):
    backend, grant, _, clock = service
    ctx = grant()
    first = transfer(backend, ctx)
    assert first["status"] == "COMPLETED" and first["data"]["remaining_balance_minor"] == 470000
    clock[0] += timedelta(minutes=6)
    assert transfer(backend, ctx) == first  # 成功重放不重新扣款，也不因授权已过期失败。
    assert transfer(backend, ctx, 30001)["error_code"] == "IDEMPOTENCY_CONFLICT"
    assert transfer(backend, replace(ctx, request_id="new"))["error_code"] == "IDEMPOTENCY_CONFLICT"
    expired = grant(request="expired")
    clock[0] += timedelta(minutes=5)
    assert transfer(backend, expired)["error_code"] == "AUTHORIZATION_INVALID"
    assert backend.get_balance(context=ctx)["data"] == {
        "balance_minor": 470000, "currency": "CNY", "daily_transfer_total_minor": 30000}
    assert bills(backend, ctx)["data"]["total_minor"] == 5000  # 转账不算消费。


@pytest.mark.parametrize("amount,error", [(True, "INVALID_AMOUNT"), (1.5, "INVALID_AMOUNT"),
    (0, "INVALID_AMOUNT"), (-1, "INVALID_AMOUNT"),
    (TRANSFER_SINGLE_LIMIT_MINOR + 1, "TRANSFER_LIMIT_EXCEEDED"), (500001, "INSUFFICIENT_BALANCE")])
def test_amount_validation_and_business_rejections(service, amount, error):
    backend, grant, _, _ = service
    assert transfer(backend, grant(amount=amount, risk="RED"), amount)["error_code"] == error


def test_missing_auth_wrong_contact_currency_and_unconfigured_backend(service, monkeypatch):
    backend, grant, records, _ = service
    ctx = grant()
    assert transfer(backend, TrustedContext("u1", "a1", "q"))["error_code"] == "AUTHORIZATION_REQUIRED"
    records.clear()
    assert transfer(backend, ctx)["error_code"] == "AUTHORIZATION_INVALID"
    assert transfer(backend, ctx, currency="USD")["error_code"] == "UNSUPPORTED_CURRENCY"
    assert backend.execute_transfer(context=ctx, contact_id="c2", amount_minor=30000)["error_code"] == "CONTACT_NOT_ACCESSIBLE"
    monkeypatch.setattr(module, "_backend", None)
    with pytest.raises(RuntimeError, match="not configured"):
        module.get_balance(context=ctx)


def test_public_entry_points_and_fail_closed_without_auth_service(service, monkeypatch):
    _, grant, _, clock = service
    ctx = grant()
    monkeypatch.setattr(module, "_backend", None)
    instance = module.configure_backend(data_factory=sample_data, clock=lambda: clock[0])
    assert isinstance(instance, BankBackend)
    assert module.get_balance(context=ctx)["data"]["balance_minor"] == 500000
    assert module.query_bills(context=ctx, start=date(2026, 10, 1),
                              end=date(2026, 11, 1))["data"]["total_minor"] == 5000
    assert module.find_contacts(context=ctx, name="演示收款人")[0]["contact_id"] == "c1"
    assert module.execute_transfer(context=ctx, contact_id="c1", amount_minor=30000)["error_code"] == "AUTHORIZATION_INVALID"
    module.reset_demo_data()
    assert module.get_balance(context=ctx)["data"]["balance_minor"] == 500000


def test_risk_boundary_and_success_result_are_isolated(service):
    backend, grant, _, _ = service
    ctx = grant(amount=YELLOW_DAILY_LIMIT_MINOR)
    result = transfer(backend, ctx, YELLOW_DAILY_LIMIT_MINOR)
    assert result["status"] == "COMPLETED"
    result["data"]["remaining_balance_minor"] = 0
    assert transfer(backend, ctx, YELLOW_DAILY_LIMIT_MINOR)["data"]["remaining_balance_minor"] == 400000
    next_ctx = grant(amount=1, request="next")
    assert transfer(backend, next_ctx, 1)["error_code"] == "REAUTHORIZATION_REQUIRED"


def test_concurrent_replays_and_risk_upgrade(service):
    backend, grant, _, _ = service
    ctx = grant()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: transfer(backend, ctx), range(12)))
    assert all(r == results[0] for r in results)
    assert backend.get_balance(context=ctx)["data"]["balance_minor"] == 470000
    # 已转 30000，再准备两笔各 60000 的 YELLOW；第二笔必须重认证。
    contexts = [grant(amount=60000, request=f"r{i}") for i in (2, 3)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda c: transfer(backend, c, 60000), contexts))
    assert sorted(r["status"] for r in results) == ["COMPLETED", "REJECTED"]
    assert next(r for r in results if r["status"] == "REJECTED")["error_code"] == "REAUTHORIZATION_REQUIRED"
    assert backend.get_balance(context=ctx)["data"]["balance_minor"] == 410000


def test_failure_before_commit_and_coordinated_reset(service, monkeypatch):
    backend, grant, records, _ = service
    ctx = grant()
    def broken_id():
        raise RuntimeError("injected execution failure")
    with monkeypatch.context() as patch:
        patch.setattr(module, "uuid4", broken_id)
        with pytest.raises(RuntimeError, match="injected execution failure"):
            transfer(backend, ctx)
    assert backend.get_balance(context=ctx)["data"]["balance_minor"] == 500000
    assert len(bills(backend, ctx)["data"]["transactions"]) == 3
    assert transfer(backend, ctx)["status"] == "COMPLETED"  # 失败不占成功幂等键。
    with backend.lock:
        records.clear()  # A 负责使授权/会话失效，B 只恢复业务数据。
        backend.reset_demo_data()
    assert transfer(backend, ctx)["error_code"] == "AUTHORIZATION_INVALID"
    assert backend.get_balance(context=ctx)["data"]["balance_minor"] == 500000
