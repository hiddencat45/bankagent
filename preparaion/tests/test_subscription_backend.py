"""订阅代扣后端：协议、流水显式归属、暂停与幂等。"""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from threading import RLock

import pytest

import bank_backend as module
from agent_security import ChallengeStore, compute_operation_hash
from bank_types import TrustedContext, WriteContext
from data.generator import build_demo_data


CTX = TrustedContext("user-001", "account-001", "sub-request")
OTHER = TrustedContext("user-002", "account-002", "sub-other")
OCTOBER = (date(2026, 10, 1), date(2026, 11, 1))


@pytest.fixture
def service():
    clock = [datetime(2026, 10, 18, 12, tzinfo=timezone(timedelta(hours=8)))]
    lock = RLock()
    store = ChallengeStore(lock=lock, clock=lambda: clock[0])
    backend = module.configure_backend(
        data_factory=build_demo_data, lookup_authorization=store.lookup,
        operation_hash=compute_operation_hash, lock=lock, clock=lambda: clock[0])

    def issue(subscription_id="sub-001", *, request="sub-request", decision="approve"):
        ctx = replace(CTX, request_id=request)
        params = {"subscription_id": subscription_id}
        record = store.register(context=ctx, operation="PAUSE_SUBSCRIPTION", params=params,
                                operation_hash=compute_operation_hash(
                                    ctx, "PAUSE_SUBSCRIPTION", params),
                                risk_level="YELLOW")
        if decision:
            store.decide(challenge_id=record["challenge_id"], user_id=ctx.user_id,
                         request_id=ctx.request_id,
                         operation_hash=record["operation_hash"], decision=decision)
        return WriteContext(ctx.user_id, ctx.account_id, ctx.request_id,
                            record["challenge_id"], record["idempotency_key"])

    return backend, store, clock, issue


def query(context=CTX, period=OCTOBER):
    start, end = period
    return module.query_subscriptions(context=context, start=start, end=end)


def test_query_lists_active_and_paused_with_explicit_payment_links(service):
    result = query()
    assert result["status"] == "COMPLETED"
    data = result["data"]
    assert (data["start"], data["end"], data["currency"]) == ("2026-10-01", "2026-11-01", "CNY")

    rows = data["subscriptions"]
    assert [r["subscription_id"] for r in rows] == ["sub-001", "sub-002"]
    active, paused = rows

    assert active["display_name"] == "演示影音会员"
    assert active["status"] == "ACTIVE"
    assert active["amount_minor"] == 2500
    assert active["next_payment_date"] == "2026-11-12"
    # 两笔重复扣款都挂在同一条协议上，靠显式外键而不是商户名
    assert [p["transaction_id"] for p in active["payments"]] == ["txn-005", "txn-006"]
    assert active["paid_minor"] == 5000

    # 暂停项仍要显示，且本期没有扣款
    assert paused["status"] == "PAUSED"
    assert paused["next_payment_date"] is None
    assert paused["paid_minor"] == 0 and paused["payments"] == []

    assert data["total_minor"] == 5000


def test_query_returns_detached_copies(service):
    rows = query()["data"]["subscriptions"]
    rows[0]["status"] = "PAUSED"
    assert query()["data"]["subscriptions"][0]["status"] == "ACTIVE"


def test_query_is_scoped_to_the_owning_account(service):
    own = [r["subscription_id"] for r in query()["data"]["subscriptions"]]
    other = [r["subscription_id"] for r in query(context=OTHER)["data"]["subscriptions"]]
    assert own == ["sub-001", "sub-002"]
    assert other == ["sub-003"]
    assert query(context=replace(CTX, account_id="account-002"))["error_code"] == (
        "ACCOUNT_NOT_ACCESSIBLE")


def test_query_excludes_payments_outside_the_period(service):
    # 两笔扣款都在 10-12，这个窗口之外应当为零，但协议仍然显示
    result = query(period=(date(2026, 10, 13), date(2026, 10, 20)))
    rows = result["data"]["subscriptions"]
    assert [r["paid_minor"] for r in rows] == [0, 0]
    assert result["data"]["total_minor"] == 0


@pytest.mark.parametrize("period", [
    (date(2026, 10, 1), date(2026, 10, 1)),
    (date(2026, 10, 5), date(2026, 10, 1)),
])
def test_query_rejects_invalid_ranges(service, period):
    assert query(period=period)["error_code"] == "INVALID_DATE_RANGE"


def test_query_rejects_too_many_linked_payments(service, monkeypatch):
    monkeypatch.setattr(module, "MAX_BILL_TRANSACTIONS", 1)
    assert query()["error_code"] == "TOO_MANY_TRANSACTIONS"


def test_find_matches_exactly_and_ignores_other_accounts(service):
    found = module.find_subscriptions(context=CTX, name="演示影音会员")
    assert [r["subscription_id"] for r in found] == ["sub-001"]
    assert found[0]["status"] == "ACTIVE"

    # 暂停项也能被解析出来（解约前要先找到它）
    assert [r["subscription_id"] for r in
            module.find_subscriptions(context=CTX, name="演示云存储")] == ["sub-002"]

    # 精确匹配：前缀/模糊都不算命中
    assert module.find_subscriptions(context=CTX, name="演示影音") == []
    assert module.find_subscriptions(context=CTX, name="") == []
    # 跨账户不可见
    assert module.find_subscriptions(context=OTHER, name="演示影音会员") == []


def test_find_rejects_foreign_account_context(service):
    with pytest.raises(PermissionError, match="ACCOUNT_NOT_ACCESSIBLE"):
        module.find_subscriptions(context=replace(CTX, account_id="account-002"),
                                  name="演示影音会员")


def test_pause_requires_authorization(service):
    backend, _, _, issue = service
    context = WriteContext(CTX.user_id, CTX.account_id, CTX.request_id, None, None)
    result = module.pause_subscription(context=context, subscription_id="sub-001")
    assert result["error_code"] == "AUTHORIZATION_REQUIRED"


def test_pause_moves_to_paused_and_clears_next_payment(service):
    result = module.pause_subscription(context=service[3](), subscription_id="sub-001")
    assert result["status"] == "COMPLETED"
    data = result["data"]
    assert (data["status"], data["previous_status"], data["changed"]) == (
        "PAUSED", "ACTIVE", True)
    assert data["next_payment_date"] is None

    row = query()["data"]["subscriptions"][0]
    assert row["status"] == "PAUSED" and row["next_payment_date"] is None
    # 暂停不改历史流水，也不动余额
    assert row["paid_minor"] == 5000
    assert module.get_balance(context=CTX)["data"]["balance_minor"] == 500000


def test_pausing_an_already_paused_subscription_reports_unchanged(service):
    _, _, _, issue = service
    module.pause_subscription(context=issue("sub-002", request="r1"),
                              subscription_id="sub-002")
    again = module.pause_subscription(context=issue("sub-002", request="r2"),
                                      subscription_id="sub-002")
    assert again["status"] == "COMPLETED", again
    assert (again["data"]["status"], again["data"]["changed"]) == ("PAUSED", False)


def test_pause_replays_the_original_receipt(service):
    _, _, _, issue = service
    context = issue(request="replay")
    first = module.pause_subscription(context=context, subscription_id="sub-001")
    replay = module.pause_subscription(context=context, subscription_id="sub-001")
    assert replay == first
    # 同键换参数必须报冲突，不能静默当成新操作
    conflict = module.pause_subscription(context=context, subscription_id="sub-002")
    assert conflict["error_code"] == "IDEMPOTENCY_CONFLICT"


def test_pause_rejects_unknown_and_foreign_subscriptions(service):
    other = service[3]("sub-003", request="foreign")
    assert module.pause_subscription(context=other,
                                     subscription_id="sub-003")["error_code"] == (
        "SUBSCRIPTION_NOT_ACCESSIBLE")
    assert module.pause_subscription(context=service[3](request="missing"),
                                     subscription_id="sub-404")["error_code"] == (
        "SUBSCRIPTION_NOT_ACCESSIBLE")
