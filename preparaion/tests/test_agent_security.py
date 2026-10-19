"""服务端安全层测试：操作哈希、挑战登记、决定落定。

重点守住契约 §3.4 / §4.3 的硬约束：

- 哈希绑定用户/账户/请求/操作/全部参数，任一项变化都要换哈希
- 参数不允许 float（二进制误差会被固化进授权绑定）
- resume 的 ``decision`` 只是输入，落定后的记录才是授权事实
- 终态不可翻转；重复提交相同终态幂等返回
- 参数被改过 → CHALLENGE_STATE_MISMATCH，不是直接放行
- RED 的 approve 没有强认证不能落成 APPROVED
- 过期挑战不能被复活；``invalidate_all`` 让旧卡片彻底失效
- 归属不符与不存在同样处理，不泄漏他人挑战是否存在

每条都用构造的坏输入验证，不是恒真断言。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent_security import (
    SG_TZ,
    ChallengeError,
    ChallengeStore,
    compute_operation_hash,
)
from bank_types import TrustedContext


CTX = TrustedContext(user_id="user-001", account_id="account-001", request_id="req-1")
PARAMS = {"contact_id": "contact-001", "amount_minor": 30_000, "currency": "CNY"}


# ---------------------------------------------------------------------------
# 操作哈希
# ---------------------------------------------------------------------------


def test_hash_is_stable_across_calls() -> None:
    a = compute_operation_hash(CTX, "TRANSFER", PARAMS)
    b = compute_operation_hash(CTX, "TRANSFER", dict(reversed(list(PARAMS.items()))))
    assert a == b, "键顺序不应影响哈希"


def test_hash_changes_when_any_bound_field_changes() -> None:
    base = compute_operation_hash(CTX, "TRANSFER", PARAMS)
    variants = [
        compute_operation_hash(
            TrustedContext("user-002", "account-001", "req-1"), "TRANSFER", PARAMS),
        compute_operation_hash(
            TrustedContext("user-001", "account-002", "req-1"), "TRANSFER", PARAMS),
        compute_operation_hash(
            TrustedContext("user-001", "account-001", "req-2"), "TRANSFER", PARAMS),
        compute_operation_hash(CTX, "QUERY_BILLS", PARAMS),
        compute_operation_hash(CTX, "TRANSFER", {**PARAMS, "amount_minor": 30_001}),
    ]
    for variant in variants:
        assert variant != base


def test_hash_rejects_float_params() -> None:
    """float 会把二进制误差固化进授权绑定，必须拒绝。"""
    with pytest.raises(TypeError, match="float is not allowed"):
        compute_operation_hash(CTX, "TRANSFER", {"amount_minor": 300.0})


def test_hash_handles_dates_and_nested_params() -> None:
    from datetime import date

    h = compute_operation_hash(
        CTX, "QUERY_BILLS", {"start": date(2026, 10, 1), "end": date(2026, 11, 1)}
    )
    assert isinstance(h, str) and len(h) == 64


def test_hash_rejects_bad_operation() -> None:
    with pytest.raises(ValueError, match="operation"):
        compute_operation_hash(CTX, "", PARAMS)


# ---------------------------------------------------------------------------
# 时钟夹具
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 19, 10, 0, tzinfo=SG_TZ)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now = self.now + timedelta(**kwargs)


@pytest.fixture()
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture()
def store(clock: FakeClock) -> ChallengeStore:
    return ChallengeStore(clock=clock)


def register(store: ChallengeStore, risk="YELLOW", params=None, operation_hash=None):
    params = PARAMS if params is None else params
    op_hash = operation_hash or compute_operation_hash(CTX, "TRANSFER", params)
    return store.register(
        context=CTX, operation="TRANSFER", params=params,
        operation_hash=op_hash, risk_level=risk,
    )


# ---------------------------------------------------------------------------
# 登记
# ---------------------------------------------------------------------------


def test_register_creates_pending_challenge(store: ChallengeStore) -> None:
    record = register(store)
    assert record["decision"] == "PENDING"
    assert record["challenge_id"].startswith("ch-")
    assert record["idempotency_key"].startswith("idem-")
    assert record["risk_level"] == "YELLOW"


def test_register_is_idempotent_for_same_key(store: ChallengeStore) -> None:
    """恢复图时 API 可能重复登记，不能生成两个挑战或两把幂等键。"""
    first = register(store)
    second = register(store)
    assert first["challenge_id"] == second["challenge_id"]
    assert first["idempotency_key"] == second["idempotency_key"]


def test_register_rejects_green_risk(store: ChallengeStore) -> None:
    with pytest.raises(ValueError, match="does not require a challenge"):
        register(store, risk="GREEN")


def test_register_differs_when_params_change(store: ChallengeStore) -> None:
    first = register(store)
    changed = {**PARAMS, "amount_minor": 31_000}
    second = register(store, params=changed)
    assert first["challenge_id"] != second["challenge_id"]


def test_expired_pending_challenge_is_replaced(
    store: ChallengeStore, clock: FakeClock
) -> None:
    """过期的待处理挑战不能复活，必须换新的。"""
    first = register(store)
    clock.advance(minutes=10)  # 超过 5 分钟有效期
    second = register(store)
    assert second["challenge_id"] != first["challenge_id"]
    assert second["decision"] == "PENDING"


# ---------------------------------------------------------------------------
# 决定落定
# ---------------------------------------------------------------------------


def test_approve_settles_record(store: ChallengeStore) -> None:
    record = register(store)
    settled = store.decide(
        challenge_id=record["challenge_id"], user_id="user-001",
        request_id="req-1", operation_hash=record["operation_hash"],
        decision="approve",
    )
    assert settled["decision"] == "APPROVED"


def test_reject_settles_record(store: ChallengeStore) -> None:
    record = register(store)
    settled = store.decide(
        challenge_id=record["challenge_id"], user_id="user-001",
        request_id="req-1", operation_hash=record["operation_hash"],
        decision="reject",
    )
    assert settled["decision"] == "REJECTED"


def test_same_terminal_state_is_idempotent(store: ChallengeStore) -> None:
    """重复提交相同终态返回已保存状态，便于 HTTP 重试。"""
    record = register(store)
    kwargs = dict(
        challenge_id=record["challenge_id"], user_id="user-001",
        request_id="req-1", operation_hash=record["operation_hash"],
        decision="approve",
    )
    first = store.decide(**kwargs)
    second = store.decide(**kwargs)
    assert first["decision"] == second["decision"] == "APPROVED"


def test_flipping_terminal_state_is_rejected(store: ChallengeStore) -> None:
    """批准后再拒绝必须报错，不改变已完成的业务。"""
    record = register(store)
    store.decide(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
        operation_hash=record["operation_hash"], decision="approve",
    )
    with pytest.raises(ChallengeError, match="CHALLENGE_INVALID"):
        store.decide(
            challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
            operation_hash=record["operation_hash"], decision="reject",
        )


def test_reject_then_approve_is_rejected(store: ChallengeStore) -> None:
    record = register(store)
    store.decide(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
        operation_hash=record["operation_hash"], decision="reject",
    )
    with pytest.raises(ChallengeError, match="CHALLENGE_INVALID"):
        store.decide(
            challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
            operation_hash=record["operation_hash"], decision="approve",
        )


def test_param_change_is_state_mismatch(store: ChallengeStore) -> None:
    """参数被改过 → CHALLENGE_STATE_MISMATCH，要求重新确认。"""
    record = register(store)
    tampered = compute_operation_hash(CTX, "TRANSFER", {**PARAMS, "amount_minor": 99_999})
    with pytest.raises(ChallengeError) as exc:
        store.decide(
            challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
            operation_hash=tampered, decision="approve",
        )
    assert exc.value.code == "CHALLENGE_STATE_MISMATCH"


def test_foreign_user_cannot_decide(store: ChallengeStore) -> None:
    record = register(store)
    with pytest.raises(ChallengeError, match="CHALLENGE_INVALID"):
        store.decide(
            challenge_id=record["challenge_id"], user_id="user-002", request_id="req-1",
            operation_hash=record["operation_hash"], decision="approve",
        )


def test_unknown_challenge_is_invalid(store: ChallengeStore) -> None:
    with pytest.raises(ChallengeError, match="CHALLENGE_INVALID"):
        store.decide(
            challenge_id="ch-does-not-exist", user_id="user-001", request_id="req-1",
            operation_hash="x" * 64, decision="approve",
        )


def test_expired_challenge_cannot_be_approved(
    store: ChallengeStore, clock: FakeClock
) -> None:
    record = register(store)
    clock.advance(minutes=6)
    with pytest.raises(ChallengeError, match="CHALLENGE_INVALID"):
        store.decide(
            challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
            operation_hash=record["operation_hash"], decision="approve",
        )


def test_red_requires_strong_authentication(store: ChallengeStore) -> None:
    """RED 的 approve 没有强认证不能落成 APPROVED。"""
    record = register(store, risk="RED")
    with pytest.raises(ChallengeError, match="strong authentication"):
        store.decide(
            challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
            operation_hash=record["operation_hash"], decision="approve",
        )


def test_red_approves_with_authentication(store: ChallengeStore) -> None:
    record = register(store, risk="RED")
    settled = store.decide(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
        operation_hash=record["operation_hash"], decision="approve", authenticated=True,
    )
    assert settled["decision"] == "APPROVED"


def test_red_reject_needs_no_authentication(store: ChallengeStore) -> None:
    record = register(store, risk="RED")
    settled = store.decide(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
        operation_hash=record["operation_hash"], decision="reject",
    )
    assert settled["decision"] == "REJECTED"


def test_unknown_decision_is_rejected(store: ChallengeStore) -> None:
    record = register(store)
    with pytest.raises(ChallengeError, match="INVALID_REQUEST"):
        store.decide(
            challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
            operation_hash=record["operation_hash"], decision="maybe",
        )


# ---------------------------------------------------------------------------
# 查询与失效
# ---------------------------------------------------------------------------


def test_lookup_returns_snapshot_not_internal_object(store: ChallengeStore) -> None:
    """返回快照：调用方改不到内部状态，否则授权可被前端篡改。"""
    record = register(store)
    snapshot = store.lookup(record["challenge_id"])
    assert snapshot is not None
    snapshot["decision"] = "APPROVED"
    again = store.lookup(record["challenge_id"])
    assert again["decision"] == "PENDING"


def test_lookup_unknown_returns_none(store: ChallengeStore) -> None:
    assert store.lookup("ch-nope") is None
    assert store.lookup("") is None
    assert store.lookup(None) is None  # type: ignore[arg-type]


def test_pending_detects_open_challenge(store: ChallengeStore) -> None:
    assert store.pending(user_id="user-001", request_id="req-1") is None
    record = register(store)
    pending = store.pending(user_id="user-001", request_id="req-1")
    assert pending is not None and pending["challenge_id"] == record["challenge_id"]


def test_pending_ignores_settled_and_expired(
    store: ChallengeStore, clock: FakeClock
) -> None:
    record = register(store)
    store.decide(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
        operation_hash=record["operation_hash"], decision="approve",
    )
    assert store.pending(user_id="user-001", request_id="req-1") is None

    fresh = register(store, params={**PARAMS, "amount_minor": 1})
    clock.advance(minutes=6)
    assert store.pending(user_id="user-001", request_id="req-1") is None
    assert fresh["decision"] == "PENDING"


def test_cancel_frees_the_session(store: ChallengeStore) -> None:
    record = register(store)
    cancelled = store.cancel(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1"
    )
    assert cancelled["decision"] == "CANCELLED"
    assert store.pending(user_id="user-001", request_id="req-1") is None


def test_cancel_does_not_erase_settled_business(store: ChallengeStore) -> None:
    """取消不能抹掉已完成的业务。"""
    record = register(store)
    store.decide(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
        operation_hash=record["operation_hash"], decision="approve",
    )
    after = store.cancel(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1"
    )
    assert after["decision"] == "APPROVED"


def test_invalidate_all_makes_old_cards_useless(store: ChallengeStore) -> None:
    """重置后旧确认卡必须彻底失效，不能继续扣款。"""
    record = register(store)
    store.invalidate_all()
    assert store.lookup(record["challenge_id"]) is None
    with pytest.raises(ChallengeError, match="CHALLENGE_INVALID"):
        store.decide(
            challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
            operation_hash=record["operation_hash"], decision="approve",
        )


# ---------------------------------------------------------------------------
# 与真实后端联调：授权记录必须能被 lookup_authorization 使用
# ---------------------------------------------------------------------------


def test_settled_record_matches_backend_identity_requirements(
    store: ChallengeStore,
) -> None:
    """契约 §3.4 要求记录含后端复查所需的全部字段。"""
    record = register(store)
    store.decide(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
        operation_hash=record["operation_hash"], decision="approve",
    )
    snapshot = store.lookup(record["challenge_id"])
    assert snapshot is not None
    for field in ("user_id", "account_id", "request_id", "operation", "params",
                  "operation_hash", "challenge_id", "risk_level", "decision",
                  "expires_at", "idempotency_key"):
        assert field in snapshot, f"缺少后端所需字段 {field}"
    assert snapshot["decision"] == "APPROVED"
    assert snapshot["risk_level"] in {"YELLOW", "RED"}
    assert isinstance(snapshot["expires_at"], datetime)
    assert snapshot["expires_at"].utcoffset() is not None
    # 凭证绝不能出现在记录里。
    assert "otp" not in snapshot
    assert "password" not in snapshot
    assert "auth_token" not in snapshot
