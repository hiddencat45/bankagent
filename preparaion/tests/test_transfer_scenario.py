"""转账场景的契约测试。

重点覆盖契约 §3.2 对转账的硬要求：

- 金额一律整数分，``float`` 直接拒绝（不静默转换）
- 超过两位小数拒绝，**不暗自四舍五入**
- 单笔上限来自 ``bank_types`` 常量，不另写阈值
- ``contact_id`` 只能来自受控后端查询，不能由候选参数提供
- 风险只能升高：超过单笔上限 DENY、当日累计超阈值 RED
- 拿不到可信累计量时必须失败，**不能降级为 YELLOW**
- ``render`` 用整数分格式化，不经过 float

后端通过 ``sys.modules`` 注入替身，避免依赖真实模拟数据。
"""

from __future__ import annotations

import sys
import types
from decimal import Decimal

import pytest

from bank_types import (
    TRANSFER_SINGLE_LIMIT_MINOR,
    YELLOW_DAILY_LIMIT_MINOR,
    TrustedContext,
)
from scenarios import ScenarioError, build_registry


CTX = TrustedContext(user_id="user-001", account_id="account-001", request_id="req-1")


class FakeBackend:
    """可控的后端替身，只实现转账场景用到的两个函数。"""

    def __init__(self, *, contacts=None, daily_total=0, balance_status="COMPLETED"):
        self.contacts = contacts if contacts is not None else [
            {"contact_id": "contact-001", "display_name": "张伟"}
        ]
        self.daily_total = daily_total
        self.balance_status = balance_status
        self.transfer_calls: list[dict] = []
        self.find_calls: list[str] = []

    def find_contacts(self, *, context, name):
        self.find_calls.append(name)
        return [c for c in self.contacts if c["display_name"] == name]

    def get_balance(self, *, context):
        if self.balance_status != "COMPLETED":
            return {"operation": "GET_BALANCE", "status": self.balance_status,
                    "data": None, "error_code": "BACKEND_UNAVAILABLE"}
        return {"operation": "GET_BALANCE", "status": "COMPLETED",
                "data": {"balance_minor": 500_000, "currency": "CNY",
                         "daily_transfer_total_minor": self.daily_total},
                "error_code": None}

    def execute_transfer(self, *, context, contact_id, amount_minor, currency="CNY"):
        self.transfer_calls.append(
            {"contact_id": contact_id, "amount_minor": amount_minor, "currency": currency}
        )
        return {"operation": "TRANSFER", "status": "COMPLETED",
                "data": {"recipient": "张伟", "amount_minor": amount_minor,
                         "remaining_balance_minor": 500_000 - amount_minor,
                         "currency": "CNY"},
                "error_code": None}


@pytest.fixture()
def fake_backend(monkeypatch):
    """把 bank_backend 替换成替身；场景内部是延迟 import，所以能生效。"""
    backend = FakeBackend()

    def install(**kwargs):
        nonlocal backend
        backend = FakeBackend(**kwargs)
        module = types.ModuleType("bank_backend")
        module.find_contacts = backend.find_contacts
        module.get_balance = backend.get_balance
        module.execute_transfer = backend.execute_transfer
        monkeypatch.setitem(sys.modules, "bank_backend", module)
        return backend

    install()
    return install


@pytest.fixture()
def registry():
    return build_registry()


# ---------------------------------------------------------------------------
# 金额换算：整数分，拒绝 float
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("candidate", "expected_minor"),
    [
        (300, 30_000),          # 整数按元解释
        ("300", 30_000),
        ("300.5", 30_050),
        ("300.50", 30_050),
        (Decimal("300.55"), 30_055),
        ("0.01", 1),            # 一分钱也要正确
    ],
)
def test_amount_to_minor(registry, fake_backend, candidate, expected_minor) -> None:
    params = registry.resolve_params(
        "transfer", {"recipient_name": "张伟", "amount": candidate}, CTX
    )
    assert params["amount_minor"] == expected_minor


@pytest.mark.parametrize(
    "candidate",
    [
        300.0,              # float 一律拒绝，不静默转换
        "300.555",          # 超过两位小数，拒绝而不是四舍五入
        "0",                # 必须为正
        "-100",             # 负数
        "abc",
        "",
        None,
        True,               # bool 不是金额
    ],
)
def test_invalid_amount_is_not_resolved(registry, fake_backend, candidate) -> None:
    params = registry.resolve_params(
        "transfer", {"recipient_name": "张伟", "amount": candidate}, CTX
    )
    assert "amount_minor" not in params


def test_float_amount_is_rejected_not_truncated(registry, fake_backend) -> None:
    """关键：0.1+0.2 这类 float 误差不能混进资金计算。"""
    params = registry.resolve_params(
        "transfer", {"recipient_name": "张伟", "amount": 300.0000001}, CTX
    )
    assert "amount_minor" not in params


def test_three_decimals_rejected_by_scale_rule(registry, fake_backend) -> None:
    """超过两位小数必须由**小数位规则**拒绝，而不是靠整数分兜底偶然拦住。

    ``Decimal("300.555")`` 乘 100 得 30055.500，非整数，会被兜底检查拦下。
    但 ``Decimal("0.125")`` 这类同样超两位小数的值也应当被拒；
    这里断言「拒绝」这一结果，并另测一个乘 100 后恰好是整数、
    只有小数位规则能拦住的值（``Decimal("0.100")`` 是两位，合法；
    ``Decimal("1.230")`` 是三位但数值等于 1.23）。
    """
    # 三位小数且乘 100 非整数：两条规则都能拦。
    for candidate in ("300.555", "1.234", "0.001"):
        params = registry.resolve_params(
            "transfer", {"recipient_name": "张伟", "amount": candidate}, CTX
        )
        assert "amount_minor" not in params, f"{candidate} 应被拒绝"

    # 三位小数但数值上等于两位（1.230 == 1.23）：兜底拦不住，只能靠小数位规则。
    # 这里明确要求拒绝，避免「看起来是 1.23」就放行。
    params = registry.resolve_params(
        "transfer", {"recipient_name": "张伟", "amount": Decimal("1.230")}, CTX
    )
    assert "amount_minor" not in params, "1.230 应被小数位规则拒绝，而不是当作 1.23 放行"


# ---------------------------------------------------------------------------
# 联系人解析：只能来自受控后端
# ---------------------------------------------------------------------------


def test_contact_id_comes_from_backend(registry, fake_backend) -> None:
    params = registry.resolve_params(
        "transfer", {"recipient_name": "张伟", "amount": 300}, CTX
    )
    assert params["contact_id"] == "contact-001"


def test_candidate_cannot_supply_contact_id(registry, fake_backend) -> None:
    """候选参数里塞 contact_id 必须被忽略——它只能来自后端查询。"""
    params = registry.resolve_params(
        "transfer",
        {"recipient_name": "张伟", "amount": 300, "contact_id": "contact-999"},
        CTX,
    )
    assert params["contact_id"] == "contact-001"


def test_unknown_recipient_leaves_contact_missing(registry, fake_backend) -> None:
    params = registry.resolve_params(
        "transfer", {"recipient_name": "查无此人", "amount": 300}, CTX
    )
    assert "contact_id" not in params


def test_ambiguous_recipient_is_not_guessed(registry, fake_backend) -> None:
    """重名歧义时不能任选一条。"""
    fake_backend(contacts=[
        {"contact_id": "contact-001", "display_name": "张伟"},
        {"contact_id": "contact-002", "display_name": "张伟"},
    ])
    params = registry.resolve_params(
        "transfer", {"recipient_name": "张伟", "amount": 300}, CTX
    )
    assert "contact_id" not in params


def test_find_contacts_permission_error_surfaces_as_scenario_error(
    registry, fake_backend, monkeypatch
) -> None:
    """归属失败抛 PermissionError 时，公共边界转成 ACCOUNT_NOT_ACCESSIBLE。"""

    def boom(*, context, name):
        raise PermissionError("ACCOUNT_NOT_ACCESSIBLE")

    module = types.ModuleType("bank_backend")
    module.find_contacts = boom
    module.get_balance = lambda *, context: {}
    module.execute_transfer = lambda **kwargs: {}
    monkeypatch.setitem(sys.modules, "bank_backend", module)

    with pytest.raises(ScenarioError, match="ACCOUNT_NOT_ACCESSIBLE"):
        registry.resolve_params(
            "transfer", {"recipient_name": "张伟", "amount": 300}, CTX
        )


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------


def test_validate_accepts_wellformed_params() -> None:
    from scenarios import transfer

    assert transfer.validate(
        "TRANSFER",
        {"contact_id": "c-1", "amount_minor": 30_000, "currency": "CNY"},
    )


@pytest.mark.parametrize(
    "params",
    [
        {"contact_id": "c-1", "amount_minor": 30_000},                      # 缺 currency
        {"contact_id": "c-1", "amount_minor": 0, "currency": "CNY"},        # 非正
        {"contact_id": "", "amount_minor": 30_000, "currency": "CNY"},      # 空联系人
        {"contact_id": "c-1", "amount_minor": 30_000, "currency": "USD"},   # 币种
        {"contact_id": "c-1", "amount_minor": True, "currency": "CNY"},     # bool
        {"contact_id": "c-1", "amount_minor": 30_000.0, "currency": "CNY"}, # float
        {"contact_id": "c-1", "amount_minor": TRANSFER_SINGLE_LIMIT_MINOR + 1,
         "currency": "CNY"},                                                # 超上限
    ],
)
def test_validate_rejects_bad_params(params) -> None:
    from scenarios import transfer

    assert not transfer.validate("TRANSFER", params)


def test_validate_rejects_foreign_operation() -> None:
    from scenarios import transfer

    assert not transfer.validate("QUERY_BILLS", {
        "contact_id": "c-1", "amount_minor": 30_000, "currency": "CNY"})


# ---------------------------------------------------------------------------
# 风险：只能升高
# ---------------------------------------------------------------------------


def test_risk_yellow_within_daily_limit(registry, fake_backend) -> None:
    fake_backend(daily_total=0)
    level = registry.evaluate_risk(
        "transfer", "TRANSFER",
        {"contact_id": "c-1", "amount_minor": 30_000, "currency": "CNY"}, CTX,
    )
    assert level == "YELLOW"


def test_risk_red_when_daily_total_exceeds_limit(registry, fake_backend) -> None:
    """当日累计加本笔超过阈值 → RED，需要强认证。"""
    fake_backend(daily_total=YELLOW_DAILY_LIMIT_MINOR - 1)
    level = registry.evaluate_risk(
        "transfer", "TRANSFER",
        {"contact_id": "c-1", "amount_minor": 2, "currency": "CNY"}, CTX,
    )
    assert level == "RED"


def test_risk_exactly_at_limit_is_yellow(registry, fake_backend) -> None:
    """边界：恰好等于阈值仍是 YELLOW（契约是 <= 阈值 → YELLOW）。"""
    fake_backend(daily_total=YELLOW_DAILY_LIMIT_MINOR - 30_000)
    level = registry.evaluate_risk(
        "transfer", "TRANSFER",
        {"contact_id": "c-1", "amount_minor": 30_000, "currency": "CNY"}, CTX,
    )
    assert level == "YELLOW"


def test_risk_deny_over_single_limit(registry, fake_backend) -> None:
    fake_backend()
    level = registry.evaluate_risk(
        "transfer", "TRANSFER",
        {"contact_id": "c-1", "amount_minor": TRANSFER_SINGLE_LIMIT_MINOR + 1,
         "currency": "CNY"}, CTX,
    )
    assert level == "DENY"


def test_risk_deny_on_invalid_amount(registry, fake_backend) -> None:
    fake_backend()
    level = registry.evaluate_risk(
        "transfer", "TRANSFER",
        {"contact_id": "c-1", "amount_minor": 0, "currency": "CNY"}, CTX,
    )
    assert level == "DENY"


def test_risk_fails_closed_when_daily_total_unavailable(registry, fake_backend) -> None:
    """拿不到可信累计量时必须失败，不能假设「今天还没转过钱」。"""
    fake_backend(balance_status="FAILED")
    with pytest.raises(ValueError, match="trusted daily total"):
        registry.evaluate_risk(
            "transfer", "TRANSFER",
            {"contact_id": "c-1", "amount_minor": 30_000, "currency": "CNY"}, CTX,
        )


def test_risk_rejects_negative_daily_total(registry, fake_backend) -> None:
    fake_backend(daily_total=-1)
    with pytest.raises(ValueError, match="invalid daily_transfer_total_minor"):
        registry.evaluate_risk(
            "transfer", "TRANSFER",
            {"contact_id": "c-1", "amount_minor": 30_000, "currency": "CNY"}, CTX,
        )


# ---------------------------------------------------------------------------
# 执行与渲染
# ---------------------------------------------------------------------------


def test_execute_forwards_to_backend(registry, fake_backend) -> None:
    backend = fake_backend()
    result = registry.execute(
        "transfer", "TRANSFER",
        {"contact_id": "contact-001", "amount_minor": 30_000, "currency": "CNY"}, CTX,
    )
    assert result["status"] == "COMPLETED"
    assert backend.transfer_calls == [
        {"contact_id": "contact-001", "amount_minor": 30_000, "currency": "CNY"}
    ]


def test_execute_rejects_invalid_params_before_backend(registry, fake_backend) -> None:
    backend = fake_backend()
    result = registry.execute(
        "transfer", "TRANSFER",
        {"contact_id": "contact-001", "amount_minor": 0, "currency": "CNY"}, CTX,
    )
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "INVALID_AMOUNT"
    assert backend.transfer_calls == []


def test_render_success_uses_integer_minor(registry) -> None:
    text = registry.render("transfer", {
        "operation": "TRANSFER", "status": "COMPLETED",
        "data": {"recipient": "张伟", "amount_minor": 30_050,
                 "remaining_balance_minor": 469_950, "currency": "CNY"},
        "error_code": None,
    })
    assert "300.50" in text
    assert "4699.50" in text


def test_render_failure_does_not_claim_success(registry) -> None:
    text = registry.render("transfer", {
        "operation": "TRANSFER", "status": "REJECTED",
        "data": None, "error_code": "INSUFFICIENT_BALANCE",
    })
    assert "余额不足" in text
    assert "已向" not in text


def test_render_unknown_error_has_generic_message(registry) -> None:
    text = registry.render("transfer", {
        "operation": "TRANSFER", "status": "FAILED",
        "data": None, "error_code": "SOMETHING_NEW",
    })
    assert "未完成" in text


def test_render_rejects_malformed_success_data(registry) -> None:
    """声称成功但数据不完整时不能编造结果。"""
    text = registry.render("transfer", {
        "operation": "TRANSFER", "status": "COMPLETED",
        "data": {"recipient": "张伟"}, "error_code": None,
    })
    assert "暂不可用" in text
