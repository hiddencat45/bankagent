"""``bank_types`` 公共契约层的回归测试。

这些测试校验的是**契约本身**，不是业务行为。每条断言都在
「有人改坏了声明或常量」时会真正失败：

- 叶子模块约束：一旦有人让 bank_types 依赖项目内模块（会造成循环导入），
  这里立刻红；
- 常量取值：阈值与契约 §3.4 的数字不一致时红；
- 上下文不可变：有人去掉 ``frozen=True`` 时红；
- 不可写字段清单：漏字段或多字段时红。

注意：本文件只测声明与常量，不测业务逻辑。业务行为由各场景的测试覆盖。
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
import typing
from pathlib import Path

import pytest


MODULE_NAME = "bank_types"


@pytest.fixture(scope="module")
def bank_types():
    """导入被测模块；模块不存在时直接失败，而不是跳过。"""
    return importlib.import_module(MODULE_NAME)


# ---------------------------------------------------------------------------
# 叶子模块约束
# ---------------------------------------------------------------------------

# 只允许这些标准库模块被 bank_types 导入。出现其它名字即视为违反
# 《阶段0-接口草案》§5.1 的叶子模块约定。
ALLOWED_STDLIB_IMPORTS = {"dataclasses", "typing", "enum", "datetime", "__future__"}

# 明确禁止的项目模块与第三方依赖，给出更可读的失败信息。
FORBIDDEN_IMPORTS = {
    "bank_agent_graph",
    "bank_backend",
    "scenarios",
    "langgraph",
    "langchain_core",
    "fastapi",
    "pydantic",
}


def _collect_imports(tree: ast.AST) -> set[str]:
    """收集模块中所有 import 的顶层名字（含 ``from x import y`` 的 x）。"""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # 相对导入（level > 0）也属于项目内部依赖，用 "<relative>" 标记。
            if node.level and node.level > 0:
                names.add("<relative>")
            elif node.module:
                names.add(node.module.split(".")[0])
    return names


def test_bank_types_is_a_leaf_module() -> None:
    """bank_types 只能依赖标准库，不能依赖项目内模块或第三方包。"""
    source_path = Path(inspect.getfile(importlib.import_module(MODULE_NAME)))
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = _collect_imports(tree)

    forbidden = imported & FORBIDDEN_IMPORTS
    assert not forbidden, (
        f"bank_types 不得导入 {sorted(forbidden)}："
        "它是叶子模块，依赖项目内模块会造成循环导入"
    )
    assert "<relative>" not in imported, "bank_types 不得使用相对导入"

    unexpected = imported - ALLOWED_STDLIB_IMPORTS
    assert not unexpected, (
        f"bank_types 出现未列入白名单的导入 {sorted(unexpected)}；"
        f"如确属标准库，请更新 ALLOWED_STDLIB_IMPORTS 并说明理由"
    )


def test_bank_types_does_not_import_langgraph(bank_types) -> None:
    """运行期也不能间接把 langgraph 拉进来。"""
    assert "langgraph" not in inspect.getsource(bank_types)


# ---------------------------------------------------------------------------
# 常量取值：必须与契约一致
# ---------------------------------------------------------------------------


def test_risk_thresholds_match_contract(bank_types) -> None:
    """阈值与契约 §3.4 一致：100000 分 / 1000000 分。"""
    assert bank_types.YELLOW_DAILY_LIMIT_MINOR == 100_000
    assert bank_types.TRANSFER_SINGLE_LIMIT_MINOR == 1_000_000


def test_thresholds_are_integral_minor_units(bank_types) -> None:
    """阈值必须是整数分，不能是 float——金额一旦用 float 就会出精度问题。"""
    for name in ("YELLOW_DAILY_LIMIT_MINOR", "TRANSFER_SINGLE_LIMIT_MINOR"):
        value = getattr(bank_types, name)
        assert isinstance(value, int) and not isinstance(value, bool), (
            f"{name} 必须是 int（整数分），实际是 {type(value).__name__}"
        )


def test_thresholds_match_legacy_yuan_behavior(bank_types) -> None:
    """阈值换算回元，必须与旧教学代码的行为等价，保证迁移不改风险行为。

    旧代码：``amount > 10_000`` 元 → DENY；``projected_total <= 1000`` 元 → YELLOW。
    """
    assert bank_types.TRANSFER_SINGLE_LIMIT_MINOR // 100 == 10_000
    assert bank_types.YELLOW_DAILY_LIMIT_MINOR // 100 == 1_000


def test_other_constants_match_contract(bank_types) -> None:
    """其余常量与契约一致。"""
    assert bank_types.MAX_BILL_TRANSACTIONS == 100
    assert bank_types.CLARIFICATION_TIMEOUT_MINUTES == 30
    assert bank_types.CHALLENGE_TIMEOUT_MINUTES == 5
    assert bank_types.BILLS_MAX_RANGE_DAYS == 366
    assert bank_types.SUPPORTED_CURRENCY == "CNY"


# ---------------------------------------------------------------------------
# 类型声明
# ---------------------------------------------------------------------------


def test_top_level_status_values_match_contract(bank_types) -> None:
    """顶层状态恰好是契约 §1.4 的 8 个取值，不能多也不能少。"""
    expected = {
        "PROCESSING",
        "NEEDS_CLARIFICATION",
        "AWAITING_CONFIRMATION",
        "AWAITING_AUTHENTICATION",
        "COMPLETED",
        "REJECTED",
        "FAILED",
        "PENDING",
    }
    assert set(typing.get_args(bank_types.TopLevelStatus)) == expected


def test_backend_status_is_separate_from_top_level(bank_types) -> None:
    """后端 status 与顶层 status 是两套取值，不能合并成一个。"""
    backend = set(typing.get_args(bank_types.BackendStatus))
    top_level = set(typing.get_args(bank_types.TopLevelStatus))

    assert backend == {"COMPLETED", "REJECTED", "FAILED", "PENDING"}
    # 后端没有这些"流程中"的中间状态，混用会让调度器误判。
    assert backend < top_level
    assert "NEEDS_CLARIFICATION" not in backend
    assert "PROCESSING" not in backend


def test_risk_level_values(bank_types) -> None:
    assert set(typing.get_args(bank_types.RiskLevel)) == {
        "GREEN",
        "YELLOW",
        "RED",
        "DENY",
    }


def test_state_has_no_thread_id(bank_types) -> None:
    """thread_id 不能进 State——它是 Checkpoint 的会话键，只放 config。"""
    assert "thread_id" not in bank_types.BankAgentState.__annotations__


def test_state_covers_contract_fields(bank_types) -> None:
    """State 必须覆盖契约 §1.2 声明的全部字段。"""
    expected = {
        "user_id",
        "account_id",
        "request_id",
        "message",
        "scenario",
        "intent",
        "candidate_params",
        "missing_fields",
        "operation",
        "params",
        "risk_level",
        "operation_hash",
        "challenge_id",
        "authorized",
        "result",
        "status",
        "response",
    }
    assert expected <= set(bank_types.BankAgentState.__annotations__)


def test_state_does_not_predefine_plan_list(bank_types) -> None:
    """契约明确要求不预埋 ``plan: list``，用 operation + params 表达单操作。"""
    assert "plan" not in bank_types.BankAgentState.__annotations__


def test_backend_result_fields(bank_types) -> None:
    """BackendResult 恰为四字段结构。"""
    assert set(bank_types.BackendResult.__annotations__) == {
        "operation",
        "status",
        "data",
        "error_code",
    }


def test_intent_spec_fields(bank_types) -> None:
    """IntentSpec 恰为六个声明字段。"""
    assert set(bank_types.IntentSpec.__annotations__) == {
        "keywords",
        "slots",
        "required",
        "operation",
        "effect",
        "risk",
    }


# ---------------------------------------------------------------------------
# 可信上下文
# ---------------------------------------------------------------------------


def test_trusted_context_is_frozen(bank_types) -> None:
    """身份字段必须不可改写，否则归属校验失去意义。"""
    ctx = bank_types.TrustedContext(
        user_id="user-001", account_id="account-001", request_id="req-1"
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.user_id = "user-999"


def test_write_context_extends_trusted_context(bank_types) -> None:
    """WriteContext 继承 TrustedContext，并额外带两个服务端字段。"""
    assert issubclass(bank_types.WriteContext, bank_types.TrustedContext)

    ctx = bank_types.WriteContext(
        user_id="user-001",
        account_id="account-001",
        request_id="req-1",
        authorization_ref="auth-ref-1",
        idempotency_key="idem-1",
    )
    assert ctx.user_id == "user-001"
    assert ctx.authorization_ref == "auth-ref-1"
    assert ctx.idempotency_key == "idem-1"


def test_write_context_is_frozen(bank_types) -> None:
    ctx = bank_types.WriteContext(
        user_id="u",
        account_id="a",
        request_id="r",
        authorization_ref="ref",
        idempotency_key="key",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.idempotency_key = "tampered"


def test_write_context_has_no_credential_field(bank_types) -> None:
    """凭证不得进入上下文——不能出现 otp / password / token 之类字段。"""
    field_names = {f.name for f in dataclasses.fields(bank_types.WriteContext)}
    for banned in ("otp", "password", "token", "secret", "pin"):
        assert banned not in field_names, f"WriteContext 不得包含 {banned}"


# ---------------------------------------------------------------------------
# 不可写字段清单
# ---------------------------------------------------------------------------


def test_untrusted_fields_cover_contract_list(bank_types) -> None:
    """契约 §1.3 列出的字段必须全部在清单里。"""
    expected = {
        "user_id",
        "account_id",
        "request_id",
        "contact_id",
        "card_id",
        "product_code",
        "risk_level",
        "operation_hash",
        "challenge_id",
        "authorized",
        "balance",
        "result",
        "idempotency_key",
        "authorization_ref",
        "daily_transfer_total_minor",
    }
    assert expected <= bank_types.UNTRUSTED_STATE_FIELDS


def test_untrusted_fields_is_immutable(bank_types) -> None:
    """清单用 frozenset，防止运行期被意外追加或清空。"""
    assert isinstance(bank_types.UNTRUSTED_STATE_FIELDS, frozenset)


def test_server_only_fields_are_subset_of_untrusted(bank_types) -> None:
    """只供服务端的数据字段也必须是不可写字段。"""
    assert bank_types.SERVER_ONLY_DATA_FIELDS <= bank_types.UNTRUSTED_STATE_FIELDS


def test_daily_transfer_total_is_server_only(bank_types) -> None:
    """风控累计量不得进入 Prompt/SSE/render，因此必须标记为服务端专属。"""
    assert "daily_transfer_total_minor" in bank_types.SERVER_ONLY_DATA_FIELDS


def test_all_exports_exist(bank_types) -> None:
    """``__all__`` 里声明的名字必须真实存在，避免 import * 时才炸。"""
    for name in bank_types.__all__:
        assert hasattr(bank_types, name), f"__all__ 声明了不存在的名字：{name}"
