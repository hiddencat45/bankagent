"""A 的安全层 ↔ B 的后端：跨模块契约测试。

这是两个角色唯一真正"接缝"的地方，比任何单侧单测都重要：

- A 的 ``compute_operation_hash`` 必须和 B 注入后端的哈希算出同一个值；
- A 的挑战记录必须含后端复查所需的全部字段（§3.4）；
- 篡改参数、跨用户、无授权、过期授权都必须被后端拒绝；
- 幂等重放不能重复扣款，但换参数必须换新请求。

用真实的 ``build_demo_data`` 和真实后端，不用替身——替身测不出接缝问题。
"""

from __future__ import annotations

import threading

import pytest

from agent_security import ChallengeStore, compute_operation_hash
from bank_backend import configure_backend, execute_transfer, get_balance
from bank_types import (
    TRANSFER_SINGLE_LIMIT_MINOR,
    TrustedContext,
    WriteContext,
)
from data.generator import build_demo_data


CTX = TrustedContext("user-001", "account-001", "req-1")
PARAMS = {"contact_id": "contact-001", "amount_minor": 30_000, "currency": "CNY"}


@pytest.fixture()
def wired():
    """共享同一把 RLock 装配安全层与后端——契约 §3.4 要求同进程互斥。"""
    lock = threading.RLock()
    store = ChallengeStore(lock=lock)
    configure_backend(
        data_factory=build_demo_data,
        lookup_authorization=store.lookup,
        operation_hash=compute_operation_hash,
        lock=lock,
    )
    return store


def approve(store: ChallengeStore, *, params=None, risk="YELLOW", ctx=CTX):
    params = PARAMS if params is None else params
    op_hash = compute_operation_hash(ctx, "TRANSFER", params)
    record = store.register(
        context=ctx, operation="TRANSFER", params=params,
        operation_hash=op_hash, risk_level=risk,
    )
    store.decide(
        challenge_id=record["challenge_id"], user_id=ctx.user_id,
        request_id=ctx.request_id, operation_hash=op_hash,
        decision="approve", authenticated=True,
    )
    return record


def write_ctx(record, ctx=CTX) -> WriteContext:
    return WriteContext(
        user_id=ctx.user_id, account_id=ctx.account_id, request_id=ctx.request_id,
        authorization_ref=record["challenge_id"],
        idempotency_key=record["idempotency_key"],
    )


# ---------------------------------------------------------------------------
# 正常路径
# ---------------------------------------------------------------------------


def test_approved_challenge_lets_backend_transfer(wired: ChallengeStore) -> None:
    record = approve(wired)
    result = execute_transfer(
        context=write_ctx(record), contact_id="contact-001", amount_minor=30_000
    )
    assert result["status"] == "COMPLETED"
    assert result["data"]["remaining_balance_minor"] == 470_000


def test_balance_reflects_transfer(wired: ChallengeStore) -> None:
    record = approve(wired)
    execute_transfer(context=write_ctx(record), contact_id="contact-001", amount_minor=30_000)
    balance = get_balance(context=CTX)
    assert balance["data"]["balance_minor"] == 470_000
    assert balance["data"]["daily_transfer_total_minor"] == 30_000


def test_idempotent_replay_does_not_double_charge(wired: ChallengeStore) -> None:
    record = approve(wired)
    first = execute_transfer(
        context=write_ctx(record), contact_id="contact-001", amount_minor=30_000)
    second = execute_transfer(
        context=write_ctx(record), contact_id="contact-001", amount_minor=30_000)
    assert first["data"]["transaction_id"] == second["data"]["transaction_id"]
    assert get_balance(context=CTX)["data"]["balance_minor"] == 470_000


def test_replay_survives_authorization_expiry(wired: ChallengeStore) -> None:
    """已成功同键同指纹重放返回存储结果，即使授权随后过期也不重新扣款。"""
    record = approve(wired)
    first = execute_transfer(
        context=write_ctx(record), contact_id="contact-001", amount_minor=30_000)
    # 模拟授权记录消失（等价于过期后的不可用）
    wired.invalidate_all()
    second = execute_transfer(
        context=write_ctx(record), contact_id="contact-001", amount_minor=30_000)
    assert second["status"] == "COMPLETED"
    assert second["data"]["transaction_id"] == first["data"]["transaction_id"]
    assert get_balance(context=CTX)["data"]["balance_minor"] == 470_000


# ---------------------------------------------------------------------------
# 拒绝路径：每一条都必须由后端挡住
# ---------------------------------------------------------------------------


def test_pending_challenge_cannot_transfer(wired: ChallengeStore) -> None:
    """只有 PENDING 记录、没有 APPROVED 时不能扣款。"""
    op_hash = compute_operation_hash(CTX, "TRANSFER", PARAMS)
    record = wired.register(
        context=CTX, operation="TRANSFER", params=PARAMS,
        operation_hash=op_hash, risk_level="YELLOW",
    )
    result = execute_transfer(
        context=write_ctx(record), contact_id="contact-001", amount_minor=30_000)
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "AUTHORIZATION_INVALID"
    assert get_balance(context=CTX)["data"]["balance_minor"] == 500_000


def test_rejected_challenge_cannot_transfer(wired: ChallengeStore) -> None:
    op_hash = compute_operation_hash(CTX, "TRANSFER", PARAMS)
    record = wired.register(
        context=CTX, operation="TRANSFER", params=PARAMS,
        operation_hash=op_hash, risk_level="YELLOW",
    )
    wired.decide(
        challenge_id=record["challenge_id"], user_id="user-001", request_id="req-1",
        operation_hash=op_hash, decision="reject",
    )
    result = execute_transfer(
        context=write_ctx(record), contact_id="contact-001", amount_minor=30_000)
    assert result["status"] == "REJECTED"
    assert get_balance(context=CTX)["data"]["balance_minor"] == 500_000


def test_tampered_amount_is_caught_by_param_binding(wired: ChallengeStore) -> None:
    """授权 300.00 元，实际提交 300.01 元 → 必须拒绝。

    这里拦住它的是**参数绑定**：后端比对授权记录里的 ``params`` 与本次调用
    参数，不一致即 ``AUTHORIZATION_INVALID``。操作哈希是第二道防线
    （B 的 ``test_bad_server_authorization_cannot_change_money`` 覆盖）。

    金额特意选在单笔上限与余额之内，确保不被限额或余额检查"顺带"拦住。
    """
    record = approve(wired)  # 授权 30_000
    result = execute_transfer(
        context=write_ctx(record), contact_id="contact-001", amount_minor=30_001)
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "AUTHORIZATION_INVALID"
    assert get_balance(context=CTX)["data"]["balance_minor"] == 500_000


def test_tampered_contact_is_caught_by_param_binding(wired: ChallengeStore) -> None:
    """授权给张伟，实际改给李娜 → 参数绑定不一致即拒绝。"""
    record = approve(wired)
    result = execute_transfer(
        context=write_ctx(record), contact_id="contact-002", amount_minor=30_000)
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "AUTHORIZATION_INVALID"
    assert get_balance(context=CTX)["data"]["balance_minor"] == 500_000


def test_missing_authorization_ref_is_rejected(wired: ChallengeStore) -> None:
    record = approve(wired)
    ctx = WriteContext("user-001", "account-001", "req-1",
                       authorization_ref="", idempotency_key=record["idempotency_key"])
    result = execute_transfer(context=ctx, contact_id="contact-001", amount_minor=30_000)
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "AUTHORIZATION_REQUIRED"


def test_foreign_user_cannot_use_someone_elses_approval(wired: ChallengeStore) -> None:
    """用户 B 拿用户 A 的授权引用必须失败。"""
    record = approve(wired)
    stolen = WriteContext("user-002", "account-002", "req-1",
                          authorization_ref=record["challenge_id"],
                          idempotency_key=record["idempotency_key"])
    result = execute_transfer(context=stolen, contact_id="contact-001", amount_minor=30_000)
    assert result["status"] == "REJECTED"


def test_invalidate_all_blocks_old_card(wired: ChallengeStore) -> None:
    """重置演示数据后，旧确认卡不能再扣款（§3.5）。"""
    record = approve(wired)
    wired.invalidate_all()
    result = execute_transfer(
        context=write_ctx(record), contact_id="contact-001", amount_minor=30_000)
    assert result["status"] == "REJECTED"
    assert get_balance(context=CTX)["data"]["balance_minor"] == 500_000


def test_insufficient_balance_is_rejected(wired: ChallengeStore) -> None:
    """余额不足必须报 INSUFFICIENT_BALANCE。

    注意检查顺序：后端先查单笔上限、再查日累计（超阈值要 RED）、最后查余额。
    所以要触发余额不足，必须先消费到余额低于日累计阈值（10 万元），
    否则会先撞上 REAUTHORIZATION_REQUIRED。

    每笔用独立的 request_id：参数与请求都相同属于同一逻辑操作，
    按契约会被幂等合并成一次扣款（这本身是正确行为，见幂等测试）。
    """
    for index in range(5):
        step_ctx = TrustedContext("user-001", "account-001", f"req-spend-{index}")
        step = {**PARAMS, "amount_minor": 90_000}
        record = approve(wired, params=step, risk="RED", ctx=step_ctx)
        assert execute_transfer(
            context=write_ctx(record, step_ctx), contact_id="contact-001",
            amount_minor=90_000)["status"] == "COMPLETED"

    assert get_balance(context=CTX)["data"]["balance_minor"] == 50_000

    over_ctx = TrustedContext("user-001", "account-001", "req-over")
    over = {**PARAMS, "amount_minor": 60_000}
    record = approve(wired, params=over, risk="RED", ctx=over_ctx)
    result = execute_transfer(
        context=write_ctx(record, over_ctx), contact_id="contact-001", amount_minor=60_000)
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "INSUFFICIENT_BALANCE"
    # 被拒绝的转账不能改变余额。
    assert get_balance(context=CTX)["data"]["balance_minor"] == 50_000


def test_single_limit_enforced_consistently(wired: ChallengeStore) -> None:
    """A 的常量与 B 的检查必须同时生效，不能各写一份。"""
    params = {**PARAMS, "amount_minor": TRANSFER_SINGLE_LIMIT_MINOR + 1}
    record = approve(wired, params=params, risk="RED")
    result = execute_transfer(
        context=write_ctx(record), contact_id="contact-001",
        amount_minor=TRANSFER_SINGLE_LIMIT_MINOR + 1)
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "TRANSFER_LIMIT_EXCEEDED"


def test_daily_limit_requires_red(wired: ChallengeStore) -> None:
    """累计超阈值时，只有 YELLOW 授权不足以扣款（需 REAUTHORIZATION）。"""
    first_params = {**PARAMS, "amount_minor": 90_000}
    first = approve(wired, params=first_params)
    execute_transfer(
        context=write_ctx(first), contact_id="contact-001", amount_minor=90_000)

    # 第二笔 2 万元，累计 11 万 > 10 万阈值，但只申请了 YELLOW
    second_params = {**PARAMS, "amount_minor": 20_000}
    second = approve(wired, params=second_params, risk="YELLOW")
    result = execute_transfer(
        context=write_ctx(second), contact_id="contact-001", amount_minor=20_000)
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "REAUTHORIZATION_REQUIRED"
