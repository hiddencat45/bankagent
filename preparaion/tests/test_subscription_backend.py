from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from threading import RLock

import pytest

import bank_backend as module
from agent_security import ChallengeStore, compute_operation_hash
from bank_types import MAX_BILL_TRANSACTIONS, TrustedContext, WriteContext
from data.generator import build_demo_data
from data.validate import validate_demo_data

CTX = TrustedContext("user-001", "account-001", "subscription-request")
START, END = date(2026, 10, 1), date(2026, 11, 1)


@pytest.fixture
def service():
    lock = RLock()
    now = [datetime(2026, 10, 18, 12, tzinfo=timezone(timedelta(hours=8)))]
    store = ChallengeStore(lock=lock, clock=lambda: now[0])
    backend = module.configure_backend(data_factory=build_demo_data, lookup_authorization=store.lookup,
        operation_hash=compute_operation_hash, lock=lock, clock=lambda: now[0])

    def issue(sub_id="subscription-001", decision="approve", request="subscription-request"):
        ctx = replace(CTX, request_id=request)
        params = {"subscription_id": sub_id}
        record = store.register(context=ctx, operation="PAUSE_SUBSCRIPTION", params=params,
            operation_hash=compute_operation_hash(ctx, "PAUSE_SUBSCRIPTION", params), risk_level="YELLOW")
        if decision:
            store.decide(challenge_id=record["challenge_id"], user_id=ctx.user_id,
                request_id=ctx.request_id, operation_hash=record["operation_hash"], decision=decision)
        return WriteContext(ctx.user_id, ctx.account_id, ctx.request_id, record["challenge_id"], record["idempotency_key"])

    return backend, store, now, issue


def query():
    return module.query_subscriptions(context=CTX, start=START, end=END)


def test_subscription_totals_are_paid_evidence_not_monthly_promises(service):
    data = query()["data"]
    assert data["total_minor"] == 23000
    first, normal, paused = data["subscriptions"]
    assert first["amount_minor"] == 2500 and first["paid_minor"] == 5000
    assert [t["transaction_id"] for t in first["payments"]] == ["txn-005", "txn-006"]
    assert normal["paid_minor"] == normal["amount_minor"] == 6000
    assert paused["status"] == "PAUSED" and paused["paid_minor"] == 12000
    first["payments"][0]["amount_minor"] = 1
    assert query()["data"]["subscriptions"][0]["payments"][0]["amount_minor"] == 2500
    other = module.query_subscriptions(context=TrustedContext("user-002", "account-002", "other"), start=START, end=END)
    assert len(other["data"]["subscriptions"]) == 1 and other["data"]["total_minor"] == 0


def test_scope_range_empty_period_and_half_open_dates(service):
    assert module.query_subscriptions(context=replace(CTX, account_id="account-002"), start=START, end=END)["error_code"] == "ACCOUNT_NOT_ACCESSIBLE"
    for start, end in [(START, START), ("本月", END), (date(2024, 1, 1), END)]:
        assert module.query_subscriptions(context=CTX, start=start, end=end)["error_code"] == "INVALID_DATE_RANGE"
    ended = module.query_subscriptions(context=CTX, start=START, end=date(2026, 10, 12))["data"]
    assert ended["subscriptions"][0]["paid_minor"] == 0
    included = module.query_subscriptions(context=CTX, start=date(2026, 10, 12), end=date(2026, 10, 13))["data"]
    assert included["total_minor"] == 5000
    assert len(included["subscriptions"]) == 3


def test_lookup_is_scoped_supports_paused_and_returns_fresh_records(service):
    found = module.find_subscriptions(context=CTX, name=" 演示订阅 ")
    assert [r["subscription_id"] for r in found] == ["subscription-001"]
    assert module.find_subscriptions(context=CTX, name="工作餐月卡")[0]["status"] == "PAUSED"
    found[0]["status"] = "PAUSED"
    assert module.find_subscriptions(context=CTX, name="演示订阅")[0]["status"] == "ACTIVE"
    with pytest.raises(PermissionError):
        module.find_subscriptions(context=replace(CTX, account_id="account-002"), name="演示订阅")


def test_cap_counts_linked_payments_and_does_not_limit_lookup():
    data = build_demo_data()
    prototype = data["transactions"][4]
    for i in range(MAX_BILL_TRANSACTIONS):
        tx_id = f"extra-{i}"
        data["transactions"].append({**prototype, "transaction_id": tx_id})
        data["subscription_payments"][tx_id] = "subscription-001"
    backend = module.BankBackend(data_factory=lambda: data)
    assert backend.query_subscriptions(context=CTX, start=START, end=END)["error_code"] == "TOO_MANY_TRANSACTIONS"
    assert len(backend.find_subscriptions(context=CTX, name="演示订阅")) == 1
    data["subscription_payments"] = {}
    assert module.BankBackend(data_factory=lambda: data).query_subscriptions(context=CTX, start=START, end=END)["data"]["total_minor"] == 0


def test_pause_preserves_evidence_balance_and_replay_after_expiry(service):
    _, store, now, issue = service
    before = query()["data"]
    balance = module.get_balance(context=CTX)
    bills = module.query_bills(context=CTX, start=START, end=END)
    ctx = issue()
    receipt = module.pause_subscription(context=ctx, subscription_id="subscription-001")
    assert receipt["data"]["changed"] is True and receipt["data"]["previous_status"] == "ACTIVE"
    assert receipt["data"]["next_payment_date"] is None
    after = query()["data"]
    assert after["subscriptions"][0]["status"] == "PAUSED"
    assert after["total_minor"] == before["total_minor"]
    assert after["subscriptions"][0]["payments"] == before["subscriptions"][0]["payments"]
    assert module.get_balance(context=CTX) == balance
    assert module.query_bills(context=CTX, start=START, end=END) == bills
    store.invalidate_all(); now[0] += timedelta(minutes=6)
    assert module.pause_subscription(context=ctx, subscription_id="subscription-001") == receipt


@pytest.mark.parametrize("decision", [None, "reject"])
def test_pause_rejects_missing_or_rejected_approval(service, decision):
    _, _, _, issue = service
    assert module.pause_subscription(context=issue(decision=decision), subscription_id="subscription-001")["error_code"] == "AUTHORIZATION_INVALID"
    assert query()["data"]["subscriptions"][0]["status"] == "ACTIVE"


def test_pause_scope_expiry_and_noop_authorization(service):
    _, _, now, issue = service
    assert module.pause_subscription(context=CTX, subscription_id="subscription-003")["error_code"] == "AUTHORIZATION_REQUIRED"
    no_change = module.pause_subscription(context=issue("subscription-003"), subscription_id="subscription-003")
    assert no_change["data"]["changed"] is False
    ctx = issue(request="second")
    for sub_id in ["subscription-004", "missing", None]:
        assert module.pause_subscription(context=ctx, subscription_id=sub_id)["error_code"] == "SUBSCRIPTION_NOT_ACCESSIBLE"
    now[0] += timedelta(minutes=5)
    assert module.pause_subscription(context=ctx, subscription_id="subscription-001")["error_code"] == "AUTHORIZATION_INVALID"


def test_idempotency_cannot_target_another_subscription_and_reset_clears_results(service):
    backend, store, _, issue = service
    ctx = issue()
    module.pause_subscription(context=ctx, subscription_id="subscription-001")
    assert module.pause_subscription(context=ctx, subscription_id="subscription-002")["error_code"] == "IDEMPOTENCY_CONFLICT"
    with backend.lock:
        backend.reset_demo_data(); store.invalidate_all()
    assert query()["data"]["subscriptions"][0]["status"] == "ACTIVE"
    assert module.pause_subscription(context=ctx, subscription_id="subscription-001")["error_code"] == "AUTHORIZATION_INVALID"


@pytest.mark.parametrize("change,error", [
    (lambda d: d["subscription_payments"].update({"txn-001": "subscription-001"}), "must be an expense"),
    (lambda d: d["subscription_payments"].update({"txn-005": "subscription-004"}), "account mismatch"),
    (lambda d: d["subscription_payments"].update({"missing": "subscription-001"}), "unknown subscription payment"),
    (lambda d: d["subscriptions"]["subscription-003"].update(next_payment_date="2026-11-01"), "paused subscription"),
])
def test_fixture_rejects_invalid_agreements_and_links(change, error):
    data = build_demo_data(); change(data)
    with pytest.raises(ValueError, match=error):
        validate_demo_data(data)
