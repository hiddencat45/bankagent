"""场景注册器的契约测试。

重点覆盖《阶段0-接口草案》§2 与《场景扩展与分工》§4 的硬规则：

- 声明校验：非法 effect/risk 组合、跨场景抢占 operation、多意图安全声明不一致
- 白名单：只来自已启用声明，operation 必须属于当前场景
- 风险：只能升高，钩子返回非法值或降级都要报错
- 异常边界：``PermissionError`` 在公共边界转成 REJECTED，不伪装成「空结果」
- 结果归一：COMPLETED 不能带 error_code，REJECTED/FAILED 必须有 error_code

每条断言都用构造的坏场景验证，**不是恒真**。
"""

from __future__ import annotations

import types

import pytest

from bank_types import TrustedContext
from scenarios import (
    ScenarioDeclarationError,
    ScenarioError,
    ScenarioRegistry,
    ScenarioSpec,
    build_registry,
)


CTX = TrustedContext(user_id="user-001", account_id="account-001", request_id="req-1")


def make_module(**overrides):
    """构造一个最小合法场景模块，可按需覆盖属性。"""
    module = types.ModuleType("fake_scenario")
    module.SCENARIO = overrides.pop("SCENARIO", "fake")
    module.INTENTS = overrides.pop(
        "INTENTS",
        {
            "FAKE_QUERY": {
                "keywords": ["查一下"],
                "slots": {"period": r"(本月)"},
                "required": [],
                "operation": "FAKE_READ",
                "effect": "READ",
                "risk": "GREEN",
            }
        },
    )
    module.execute = overrides.pop(
        "execute",
        lambda operation, params, context: {
            "operation": operation,
            "status": "COMPLETED",
            "data": {},
            "error_code": None,
        },
    )
    module.render = overrides.pop("render", lambda result: "ok")
    for key, value in overrides.items():
        setattr(module, key, value)
    return module


def registry_of(*modules) -> ScenarioRegistry:
    return build_registry(list(modules))


# ---------------------------------------------------------------------------
# 声明校验
# ---------------------------------------------------------------------------


def test_valid_scenario_is_registered() -> None:
    registry = registry_of(make_module())
    assert registry.scenario_names() == ["fake"]
    assert "FAKE_READ" in registry.allowed_operations


def test_missing_required_attr_is_rejected() -> None:
    module = make_module()
    del module.render
    with pytest.raises(ScenarioDeclarationError, match="缺少必需属性"):
        registry_of(module)


def test_read_must_be_green() -> None:
    """只读操作声明成 YELLOW 是配置错误，必须阻止启用。"""
    module = make_module(
        INTENTS={
            "FAKE_QUERY": {
                "keywords": ["查"],
                "slots": {},
                "required": [],
                "operation": "FAKE_READ",
                "effect": "READ",
                "risk": "YELLOW",
            }
        }
    )
    with pytest.raises(ScenarioDeclarationError, match="只读操作只能是 GREEN"):
        registry_of(module)


def test_write_must_not_be_green() -> None:
    """写操作声明成 GREEN 是配置错误，必须阻止启用。"""
    module = make_module(
        INTENTS={
            "FAKE_WRITE": {
                "keywords": ["改"],
                "slots": {},
                "required": [],
                "operation": "FAKE_WRITE",
                "effect": "WRITE",
                "risk": "GREEN",
            }
        }
    )
    with pytest.raises(ScenarioDeclarationError, match="写操作至少 YELLOW"):
        registry_of(module)


def test_invalid_risk_value_is_rejected() -> None:
    module = make_module(
        INTENTS={
            "FAKE_QUERY": {
                "keywords": ["查"],
                "slots": {},
                "required": [],
                "operation": "FAKE_READ",
                "effect": "READ",
                "risk": "BLUE",
            }
        }
    )
    with pytest.raises(ScenarioDeclarationError, match="risk 非法"):
        registry_of(module)


def test_cross_scenario_operation_collision_is_rejected() -> None:
    """不同场景抢占同一 operation 名必须报错。"""
    a = make_module(SCENARIO="alpha")
    b = make_module(SCENARIO="beta")  # 同样声明 FAKE_READ
    with pytest.raises(ScenarioDeclarationError, match="已被场景"):
        registry_of(a, b)


def test_same_scenario_multiple_intents_must_share_safety() -> None:
    """同一场景内多意图映射同一 operation 时，安全声明必须一致。"""
    module = make_module(
        INTENTS={
            "A": {
                "keywords": ["a"],
                "slots": {},
                "required": [],
                "operation": "SHARED",
                "effect": "WRITE",
                "risk": "YELLOW",
            },
            "B": {
                "keywords": ["b"],
                "slots": {},
                "required": [],
                "operation": "SHARED",
                "effect": "WRITE",
                "risk": "RED",
            },
        }
    )
    with pytest.raises(ScenarioDeclarationError, match="不同 risk"):
        registry_of(module)


def test_required_slot_must_be_declared() -> None:
    module = make_module(
        INTENTS={
            "FAKE": {
                "keywords": ["x"],
                "slots": {"a": "r"},
                "required": ["b"],
                "operation": "OP",
                "effect": "READ",
                "risk": "GREEN",
            }
        }
    )
    with pytest.raises(ScenarioDeclarationError, match="未声明槽位"):
        registry_of(module)


def test_empty_registry_is_rejected() -> None:
    with pytest.raises(ScenarioDeclarationError, match="没有可用的场景声明"):
        build_registry([])


def test_duplicate_scenario_name_is_rejected() -> None:
    a = make_module(SCENARIO="dup")
    b = make_module(SCENARIO="dup")
    with pytest.raises(ScenarioDeclarationError, match="场景名重复"):
        registry_of(a, b)


# ---------------------------------------------------------------------------
# 白名单与操作归属
# ---------------------------------------------------------------------------


def test_check_operation_rejects_foreign_operation() -> None:
    """operation 必须属于该场景——不能凭候选参数指定任意函数。"""
    registry = registry_of(make_module())
    with pytest.raises(ScenarioError, match="不属于场景"):
        registry.check_operation("fake", "TRANSFER")


def test_check_operation_rejects_unknown_scenario() -> None:
    registry = registry_of(make_module())
    with pytest.raises(ScenarioError, match="未知场景"):
        registry.check_operation("nope", "FAKE_READ")


def test_allowed_operations_only_from_valid_declarations() -> None:
    registry = registry_of(make_module())
    assert registry.allowed_operations == frozenset({"FAKE_READ"})


# ---------------------------------------------------------------------------
# 风险：只能升高
# ---------------------------------------------------------------------------


def test_risk_floor_is_declared_value() -> None:
    registry = registry_of(make_module())
    assert registry.risk_floor("fake", "FAKE_READ") == "GREEN"


def test_risk_hook_cannot_lower() -> None:
    """场景钩子试图降级必须报错，不能静默采用。"""
    module = make_module(
        INTENTS={
            "FAKE_WRITE": {
                "keywords": ["改"],
                "slots": {},
                "required": [],
                "operation": "FAKE_WRITE",
                "effect": "WRITE",
                "risk": "RED",
            }
        },
        risk=lambda operation, params, context: "YELLOW",
    )
    registry = registry_of(module)
    with pytest.raises(ScenarioDeclarationError, match="风险只能升高"):
        registry.evaluate_risk("fake", "FAKE_WRITE", {}, CTX)


def test_risk_hook_can_raise() -> None:
    module = make_module(
        INTENTS={
            "FAKE_WRITE": {
                "keywords": ["改"],
                "slots": {},
                "required": [],
                "operation": "FAKE_WRITE",
                "effect": "WRITE",
                "risk": "YELLOW",
            }
        },
        risk=lambda operation, params, context: "RED",
    )
    registry = registry_of(module)
    assert registry.evaluate_risk("fake", "FAKE_WRITE", {}, CTX) == "RED"


def test_risk_hook_invalid_value_is_rejected() -> None:
    module = make_module(
        INTENTS={
            "FAKE_WRITE": {
                "keywords": ["改"],
                "slots": {},
                "required": [],
                "operation": "FAKE_WRITE",
                "effect": "WRITE",
                "risk": "YELLOW",
            }
        },
        risk=lambda operation, params, context: "PURPLE",
    )
    registry = registry_of(module)
    with pytest.raises(ScenarioDeclarationError, match="非法值"):
        registry.evaluate_risk("fake", "FAKE_WRITE", {}, CTX)


# ---------------------------------------------------------------------------
# 异常边界：PermissionError 必须转成 REJECTED，不能伪装成空结果
# ---------------------------------------------------------------------------


def test_resolve_permission_error_becomes_scenario_error() -> None:
    """B 的 find_contacts 归属失败抛 PermissionError，公共边界统一转码。"""

    def resolve(candidate_params, context):
        raise PermissionError("ACCOUNT_NOT_ACCESSIBLE")

    registry = registry_of(make_module(resolve=resolve))
    with pytest.raises(ScenarioError, match="ACCOUNT_NOT_ACCESSIBLE"):
        registry.resolve_params("fake", {}, CTX)


def test_resolve_without_hook_passes_through() -> None:
    registry = registry_of(make_module())
    assert registry.resolve_params("fake", {"a": 1}, CTX) == {"a": 1}


def test_resolve_non_dict_result_is_rejected() -> None:
    registry = registry_of(make_module(resolve=lambda params, ctx: "not-a-dict"))
    with pytest.raises(ScenarioError, match="INVALID_PARAMS"):
        registry.resolve_params("fake", {}, CTX)


def test_execute_permission_error_returns_rejected_not_success() -> None:
    """执行期权限错误必须返回 REJECTED，绝不能变成 COMPLETED。"""

    def execute(operation, params, context):
        raise PermissionError("ACCOUNT_NOT_ACCESSIBLE")

    registry = registry_of(make_module(execute=execute))
    result = registry.execute("fake", "FAKE_READ", {}, CTX)
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "ACCOUNT_NOT_ACCESSIBLE"
    assert result["data"] is None


def test_not_implemented_is_not_converted_to_success() -> None:
    """未实现的后端必须明确失败，不能把 NotImplementedError 转成成功。"""

    def execute(operation, params, context):
        raise NotImplementedError

    registry = registry_of(make_module(execute=execute))
    result = registry.execute("fake", "FAKE_READ", {}, CTX)
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "NOT_IMPLEMENTED"


# ---------------------------------------------------------------------------
# 结果归一
# ---------------------------------------------------------------------------


def test_completed_with_error_code_is_rejected() -> None:
    module = make_module(
        execute=lambda o, p, c: {
            "operation": o,
            "status": "COMPLETED",
            "data": {},
            "error_code": "SOMETHING",
        }
    )
    registry = registry_of(module)
    with pytest.raises(ScenarioError, match="error_code 非空"):
        registry.execute("fake", "FAKE_READ", {}, CTX)


def test_rejected_without_error_code_is_rejected() -> None:
    module = make_module(
        execute=lambda o, p, c: {
            "operation": o,
            "status": "REJECTED",
            "data": None,
            "error_code": None,
        }
    )
    registry = registry_of(module)
    with pytest.raises(ScenarioError, match="缺少 error_code"):
        registry.execute("fake", "FAKE_READ", {}, CTX)


def test_invalid_status_is_rejected() -> None:
    module = make_module(
        execute=lambda o, p, c: {
            "operation": o,
            "status": "OK",
            "data": {},
            "error_code": None,
        }
    )
    registry = registry_of(module)
    with pytest.raises(ScenarioError, match="非法 status"):
        registry.execute("fake", "FAKE_READ", {}, CTX)


def test_render_must_return_str() -> None:
    module = make_module(render=lambda result: 123)
    registry = registry_of(module)
    with pytest.raises(ScenarioError, match="必须返回 str"):
        registry.render("fake", {"status": "COMPLETED"})


# ---------------------------------------------------------------------------
# 意图匹配
# ---------------------------------------------------------------------------


def test_match_intents_collects_all_hits_not_first() -> None:
    """不同场景同时命中时要全部返回，不能按文件名顺序只取第一个。"""
    a = make_module(
        SCENARIO="alpha",
        INTENTS={
            "A": {
                "keywords": ["转账"],
                "slots": {},
                "required": [],
                "operation": "OP_A",
                "effect": "WRITE",
                "risk": "YELLOW",
            }
        },
    )
    b = make_module(
        SCENARIO="beta",
        INTENTS={
            "B": {
                "keywords": ["转账", "汇款"],
                "slots": {},
                "required": [],
                "operation": "OP_B",
                "effect": "WRITE",
                "risk": "YELLOW",
            }
        },
    )
    registry = registry_of(a, b)

    # 只命中一个共同词时，两者命中数相同，按场景名稳定排序。
    same_hits = registry.match_intents("我要转账")
    assert len(same_hits) == 2
    assert [item[2] for item in same_hits] == [1, 1]

    # 同时命中 beta 的两个词时，beta 命中数更高，排到前面。
    more_hits = registry.match_intents("我要转账汇款")
    assert len(more_hits) == 2
    assert more_hits[0][0] == "beta"
    assert more_hits[0][2] == 2
    assert more_hits[1][2] == 1


def test_match_intents_empty_message() -> None:
    registry = registry_of(make_module())
    assert registry.match_intents("") == []
    assert registry.match_intents(None) == []


# ---------------------------------------------------------------------------
# 真实场景：bills 与 transfer 必须能被自动发现并通过校验
# ---------------------------------------------------------------------------


def test_real_registry_discovers_shipped_scenarios() -> None:
    """真实注册表应发现 bills 与 transfer，且白名单包含两个操作。"""
    registry = build_registry()
    assert {"bills", "transfer"} <= set(registry.scenario_names())
    assert {"QUERY_BILLS", "TRANSFER"} <= registry.allowed_operations


def test_real_transfer_is_write_yellow() -> None:
    registry = build_registry()
    assert registry.effect_of("transfer", "TRANSFER") == "WRITE"
    assert registry.risk_floor("transfer", "TRANSFER") == "YELLOW"


def test_real_bills_is_read_green() -> None:
    registry = build_registry()
    assert registry.effect_of("bills", "QUERY_BILLS") == "READ"
    assert registry.risk_floor("bills", "QUERY_BILLS") == "GREEN"
