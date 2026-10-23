"""卡片后端与现有真实挑战表联调；不依赖尚未接入的 card 场景。"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from threading import RLock

import pytest

import bank_backend as module
from agent_security import ChallengeStore, compute_operation_hash
from bank_types import TrustedContext, WriteContext
from data.generator import build_demo_data


CTX = TrustedContext("user-001", "account-001", "card-request")


@pytest.fixture
def service():
    clock = [datetime(2026, 10, 18, 12, tzinfo=timezone(timedelta(hours=8)))]
    lock = RLock()
    store = ChallengeStore(lock=lock, clock=lambda: clock[0])
    backend = module.configure_backend(
        data_factory=build_demo_data, lookup_authorization=store.lookup,
        operation_hash=compute_operation_hash, lock=lock, clock=lambda: clock[0])

    def issue(operation="FREEZE_CARD", card_id="card-001", *, request="card-request",
              decision="approve"):
        ctx = replace(CTX, request_id=request)
        params = {"card_id": card_id}
        record = store.register(context=ctx, operation=operation, params=params,
                                operation_hash=compute_operation_hash(ctx, operation, params),
                                risk_level="YELLOW")
        if decision:
            store.decide(challenge_id=record["challenge_id"], user_id=ctx.user_id,
                         request_id=ctx.request_id, operation_hash=record["operation_hash"],
                         decision=decision)
        return WriteContext(ctx.user_id, ctx.account_id, ctx.request_id,
                            record["challenge_id"], record["idempotency_key"])

    return backend, store, clock, issue


def cards():
    return module.query_cards(context=CTX)["data"]["cards"]


def test_card_queries_are_account_scoped_sorted_and_detached(service):
    rows = cards()
    assert rows == [
        {"card_id": "card-001", "display_name": "日常消费卡", "status": "ACTIVE"},
        {"card_id": "card-002", "display_name": "备用卡", "status": "FROZEN"},
    ]
    rows[0]["status"] = "FROZEN"
    assert cards()[0]["status"] == "ACTIVE"
    assert module.query_cards(context=replace(CTX, account_id="account-002"))["error_code"] == "ACCOUNT_NOT_ACCESSIBLE"
    other = TrustedContext("user-002", "account-002", "other")
    assert module.query_cards(context=other)["data"]["cards"][0]["card_id"] == "card-003"


def test_card_query_empty_account_and_duplicate_names_are_preserved():
    data = build_demo_data()
    data["cards"]["card-002"]["display_name"] = "日常消费卡"
    backend = module.BankBackend(data_factory=lambda: data)
    assert len(backend.query_cards(context=CTX)["data"]["cards"]) == 2
    data["cards"] = {}
    empty = module.BankBackend(data_factory=lambda: data).query_cards(context=CTX)
    assert empty == {"operation": "QUERY_CARDS", "status": "COMPLETED",
                     "data": {"cards": []}, "error_code": None}


def test_freeze_then_unfreeze_preserves_balance_and_all_transactions(service):
    _, _, _, issue = service
    balance = module.get_balance(context=CTX)
    ledger = module.query_bills(context=CTX, start=date(2026, 10, 1), end=date(2026, 11, 1))
    result = module.freeze_card(context=issue(), card_id="card-001")
    assert result == {"operation": "FREEZE_CARD", "status": "COMPLETED", "error_code": None,
                      "data": {"card_id": "card-001", "display_name": "日常消费卡",
                               "status": "FROZEN", "previous_status": "ACTIVE", "changed": True}}
    assert cards()[0]["status"] == "FROZEN"
    result["data"]["status"] = "ACTIVE"
    assert cards()[0]["status"] == "FROZEN"
    restored = module.unfreeze_card(context=issue("UNFREEZE_CARD", request="restore"), card_id="card-001")
    assert restored["data"]["previous_status"] == "FROZEN" and restored["data"]["changed"] is True
    assert cards()[0]["status"] == "ACTIVE"
    assert module.get_balance(context=CTX) == balance
    assert module.query_bills(context=CTX, start=date(2026, 10, 1), end=date(2026, 11, 1)) == ledger


@pytest.mark.parametrize("decision", [None, "reject"])
def test_unapproved_challenge_never_changes_card(service, decision):
    _, _, _, issue = service
    result = module.freeze_card(context=issue(decision=decision), card_id="card-001")
    assert result["status"] == "REJECTED" and result["error_code"] == "AUTHORIZATION_INVALID"
    assert cards()[0]["status"] == "ACTIVE"


@pytest.mark.parametrize("card_id", ["missing", "card-003", None])
def test_unknown_or_foreign_card_is_rejected(service, card_id):
    _, _, _, issue = service
    result = module.freeze_card(context=issue(), card_id=card_id)
    assert result["error_code"] == "CARD_NOT_ACCESSIBLE"
    assert cards()[0]["status"] == "ACTIVE"


def test_write_requires_owned_context_and_authorization_reference(service):
    _, _, _, issue = service
    assert module.freeze_card(context=CTX, card_id="card-001")["error_code"] == "AUTHORIZATION_REQUIRED"
    context = issue()
    assert module.freeze_card(context=replace(context, user_id="user-002"), card_id="card-001")["error_code"] == "ACCOUNT_NOT_ACCESSIBLE"
    assert module.freeze_card(context=replace(context, authorization_ref=""), card_id="card-001")["error_code"] == "AUTHORIZATION_REQUIRED"
    assert module.freeze_card(context=replace(context, idempotency_key=""), card_id="card-001")["error_code"] == "AUTHORIZATION_INVALID"


@pytest.mark.parametrize("field,value", [
    ("user_id", "user-002"), ("account_id", "account-002"),
    ("request_id", "another"), ("idempotency_key", "another"),
    ("operation", "UNFREEZE_CARD"), ("params", {"card_id": "card-002"}),
    ("decision", "PENDING"), ("risk_level", "GREEN"),
    ("challenge_id", ""), ("operation_hash", "different"), ("expires_at", None),
])
def test_authorization_snapshot_is_bound_to_exact_card_operation(service, monkeypatch, field, value):
    backend, store, _, issue = service
    context = issue()
    record = store.lookup(context.authorization_ref)
    record[field] = value
    monkeypatch.setattr(backend, "_lookup", lambda _: record)
    assert module.freeze_card(context=context, card_id="card-001")["error_code"] == "AUTHORIZATION_INVALID"
    assert cards()[0]["status"] == "ACTIVE"


def test_expired_authorization_fails_before_first_execution(service):
    _, _, clock, issue = service
    context = issue()
    clock[0] += timedelta(minutes=5)
    assert module.freeze_card(context=context, card_id="card-001")["error_code"] == "AUTHORIZATION_INVALID"
    assert cards()[0]["status"] == "ACTIVE"


def test_already_target_state_still_requires_authorization_and_records_noop(service):
    _, _, _, issue = service
    assert module.freeze_card(context=CTX, card_id="card-002")["error_code"] == "AUTHORIZATION_REQUIRED"
    result = module.freeze_card(context=issue(card_id="card-002"), card_id="card-002")
    assert result["status"] == "COMPLETED"
    assert result["data"]["changed"] is False
    assert result["data"]["previous_status"] == result["data"]["status"] == "FROZEN"


def test_replay_returns_historical_receipt_without_reapplying_after_unfreeze(service):
    _, store, clock, issue = service
    original = issue()
    receipt = module.freeze_card(context=original, card_id="card-001")
    module.unfreeze_card(context=issue("UNFREEZE_CARD", request="restore"), card_id="card-001")
    clock[0] += timedelta(minutes=6)
    store.invalidate_all()
    assert module.freeze_card(context=original, card_id="card-001") == receipt
    assert cards()[0]["status"] == "ACTIVE"


def test_same_idempotency_key_cannot_change_card_operation_or_request(service):
    _, _, _, issue = service
    context = issue()
    module.freeze_card(context=context, card_id="card-001")
    assert module.freeze_card(context=context, card_id="card-002")["error_code"] == "IDEMPOTENCY_CONFLICT"
    assert module.unfreeze_card(context=context, card_id="card-001")["error_code"] == "IDEMPOTENCY_CONFLICT"
    assert module.freeze_card(context=replace(context, request_id="different"), card_id="card-001")["error_code"] == "IDEMPOTENCY_CONFLICT"


def test_concurrent_replays_and_reset(service):
    backend, store, _, issue = service
    context = issue()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: module.freeze_card(context=context, card_id="card-001"), range(24)))
    assert all(result == results[0] and result["data"]["changed"] for result in results)
    assert cards()[0]["status"] == "FROZEN"
    with backend.lock:
        store.invalidate_all()
        backend.reset_demo_data()
    assert cards()[0]["status"] == "ACTIVE"
    assert module.freeze_card(context=context, card_id="card-001")["error_code"] == "AUTHORIZATION_INVALID"


def test_receipt_construction_failure_does_not_publish_partial_state(service, monkeypatch):
    _, _, _, issue = service
    context = issue()
    copy = module.deepcopy

    def fail_receipt(value):
        if isinstance(value, dict) and value.get("operation") == "FREEZE_CARD" and value.get("status") == "COMPLETED":
            raise RuntimeError("simulated receipt failure")
        return copy(value)

    with monkeypatch.context() as fault:
        fault.setattr(module, "deepcopy", fail_receipt)
        with pytest.raises(RuntimeError, match="simulated receipt failure"):
            module.freeze_card(context=context, card_id="card-001")
    assert cards()[0]["status"] == "ACTIVE"
    retried = module.freeze_card(context=context, card_id="card-001")
    assert retried["data"]["changed"] is True
