"""非转账写操作的确认卡投影与失败重试。

验证两件事，都不依赖 B 的卡片后端实现：

1. 确认卡展示字段由**场景**提供，`api/server.py` 不再按 operation 写死转账分支；
2. 失败重试入口不再限定 `operation == "TRANSFER"`。

卡片后端按已确认的契约签名做测试替身。**替身不等于运行能力**：真实卡片
后端未实现，本文件证明的是接线正确，不是功能已交付。
"""
import json
import types
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from bankagent.agent.agent_security import SG_TZ
from bankagent.api.server import create_app
from bankagent.agent.scenarios import balance, bills, build_registry, transfer
from test_api_http import chat, decision, login, result


class FakeCardBackend:
    """按契约签名实现的最小卡片后端；只存在于测试里。"""

    def __init__(self) -> None:
        self.cards = {
            "card-001": {"card_id": "card-001", "display_name": "日常消费卡", "status": "ACTIVE"}
        }
        self.freeze_calls: list[str] = []

    def query_cards(self, *, context):
        return {
            "operation": "QUERY_CARDS",
            "status": "COMPLETED",
            "data": {"cards": [dict(row) for row in self.cards.values()]},
            "error_code": None,
        }

    def freeze_card(self, *, context, card_id):
        self.freeze_calls.append(card_id)
        row = self.cards[card_id]
        previous = row["status"]
        row["status"] = "FROZEN"
        return {
            "operation": "FREEZE_CARD",
            "status": "COMPLETED",
            "data": {**row, "previous_status": previous, "changed": previous != "FROZEN"},
            "error_code": None,
        }


def _card_scenario_module(backend: FakeCardBackend, *, with_confirmation: bool = True):
    """构造一个非转账写场景，形状与 transfer.py 相同。"""
    module = types.ModuleType("fake_card")
    module.SCENARIO = "card_demo"
    module.INTENTS = {
        "CARD_FREEZE": {
            "keywords": ["冻结"],
            "slots": {"card_name": r"冻结\s*(\S+)"},
            "required": ["card_name"],
            "operation": "FREEZE_CARD",
            "effect": "WRITE",
            "risk": "YELLOW",
        }
    }
    module.CLARIFY_LABELS = {"card_name": "卡片", "card_id": "有效卡片"}

    def resolve(candidate_params, context):
        # 候选是名称，card_id 只能来自受控查询。
        params = {}
        name = candidate_params.get("card_name")
        if isinstance(name, str) and name.strip():
            result = backend.query_cards(context=context)
            matches = [c for c in result["data"]["cards"] if c["display_name"] == name.strip()]
            if len(matches) == 1:
                params["card_id"] = matches[0]["card_id"]
        return params

    def validate(operation, params):
        return bool(params.get("card_id"))

    def risk(operation, params, context):
        return "YELLOW"

    def confirmation(*, operation, params, candidate_params, context):
        result = backend.query_cards(context=context)
        card = next(c for c in result["data"]["cards"] if c["card_id"] == params["card_id"])
        return {
            "display_name": card["display_name"],
            "current_status": card["status"],
            "target_status": "FROZEN",
        }

    def execute(operation, params, context):
        return backend.freeze_card(context=context, card_id=params["card_id"])

    def render(result_):
        return "卡片操作完成。"

    module.resolve = resolve
    module.validate = validate
    module.risk = risk
    module.execute = execute
    module.render = render
    if with_confirmation:
        module.confirmation = confirmation
    return module


def _make_app(monkeypatch, *, with_confirmation: bool = True):
    monkeypatch.setattr(bills, "_clock", bills._clock)
    backend = FakeCardBackend()
    module = _card_scenario_module(backend, with_confirmation=with_confirmation)
    registry = build_registry([balance, bills, transfer, module])
    app = create_app(
        demo=True,
        clock=lambda: datetime(2026, 10, 18, 12, tzinfo=SG_TZ),
        registry=registry,
    )
    return app, backend, registry


@pytest.fixture
def card_app(monkeypatch):
    app, backend, registry = _make_app(monkeypatch)
    with TestClient(app, base_url="http://localhost") as client:
        yield client, backend, registry


def _confirm_payload(out):
    return next(data["payload"] for name, data in out if name == "card" and data["type"] == "confirm")


def _interrupt(out):
    return next(data for name, data in out if name == "interrupt")


# ---------------------------------------------------------------------------
# 确认卡由场景提供
# ---------------------------------------------------------------------------


def test_non_transfer_confirm_card_uses_scenario_hook(card_app):
    client, _, _ = card_app
    out = chat(client, login(client), message="冻结 日常消费卡")
    payload = _confirm_payload(out)

    assert payload["operation"] == "FREEZE_CARD"
    assert payload["risk_level"] == "YELLOW"
    assert payload["display_name"] == "日常消费卡"
    assert payload["current_status"] == "ACTIVE"
    assert payload["target_status"] == "FROZEN"
    assert payload["challenge_id"] and payload["operation_hash"] and payload["expires_at"]


def test_confirm_card_never_carries_entity_id(card_app):
    """确认卡不得含实体 ID：页面只回传 challenge_id，执行对象由服务端记录决定。"""
    client, _, _ = card_app
    out = chat(client, login(client), message="冻结 日常消费卡")
    payload = _confirm_payload(out)

    assert "card_id" not in payload
    assert "card-001" not in json.dumps(payload, ensure_ascii=False)


def test_confirmation_hook_receives_bound_params_not_raw_candidates(card_app):
    """钩子拿到的是绑定后的 params（card_id），不是模型/规则给的候选名。"""
    client, _, registry = card_app
    seen = {}
    spec = registry.get("card_demo")
    original = spec.confirmation

    def spy(*, operation, params, candidate_params, context):
        seen["operation"] = operation
        seen["params"] = dict(params)
        seen["candidate"] = dict(candidate_params)
        return original(operation=operation, params=params,
                        candidate_params=candidate_params, context=context)

    spec.confirmation = spy
    try:
        chat(client, login(client), message="冻结 日常消费卡")
    finally:
        spec.confirmation = original

    assert seen["operation"] == "FREEZE_CARD"
    assert seen["params"] == {"card_id": "card-001"}
    assert seen["candidate"] == {"card_name": "日常消费卡"}


def test_scenario_without_confirmation_hook_keeps_base_payload(monkeypatch):
    """没有钩子的场景退化为基础字段，不会因为缺少展示字段而报错。"""
    app, _, _ = _make_app(monkeypatch, with_confirmation=False)
    with TestClient(app, base_url="http://localhost") as client:
        out = chat(client, login(client), message="冻结 日常消费卡")
        payload = _confirm_payload(out)

    assert set(payload) == {
        "operation", "risk_level", "challenge_id", "operation_hash", "expires_at"
    }


def test_transfer_confirm_payload_includes_bound_payer_card(card_app):
    """契约增量：保留原确认字段，补充服务端当前付款卡名称和尾号。"""
    client, _, _ = card_app
    out = chat(client, login(client), message="给张伟转 300 元")
    payload = _confirm_payload(out)

    assert set(payload) == {
        "operation", "risk_level", "challenge_id", "operation_hash", "expires_at",
        "recipient", "amount_minor", "currency", "payer_card", "risk_context",
    }
    assert payload["recipient"] == "张伟"
    assert payload["amount_minor"] == 30000
    assert payload["currency"] == "CNY"
    assert '日常消费卡' in payload['payer_card'] and '0001' in payload['payer_card']


def test_transfer_confirmation_refuses_unmatched_recipient(card_app):
    """绑定事实与查询结果对不上时不能生成残缺确认卡，而应失败。

    收款人为空的确认卡会让用户确认一笔"转给某人"但看不出转给谁的操作，
    比直接失败危险得多。
    """
    from bankagent.banking.bank_types import TrustedContext
    from bankagent.agent.scenarios import transfer as transfer_module

    context = TrustedContext("user-001", "account-001", "req-1")
    with pytest.raises(ValueError):
        transfer_module.confirmation(
            operation="TRANSFER",
            params={"contact_id": "contact-999", "amount_minor": 30000, "currency": "CNY"},
            candidate_params={"recipient_name": "张伟"},
            context=context,
        )
    with pytest.raises(ValueError):
        transfer_module.confirmation(
            operation="TRANSFER",
            params={"amount_minor": 30000, "currency": "CNY"},
            candidate_params={"recipient_name": "张伟"},
            context=context,
        )


# ---------------------------------------------------------------------------
# 执行与取消
# ---------------------------------------------------------------------------


def test_non_transfer_operation_changes_state_after_confirm(card_app):
    client, backend, _ = card_app
    auth = login(client)
    out = chat(client, auth, message="冻结 日常消费卡")
    thread, intr = out[0][1]["thread_id"], _interrupt(out)

    assert backend.cards["card-001"]["status"] == "ACTIVE"  # 确认前不变

    done = decision(client, auth, thread, intr)
    assert done[-1][1]["status"] == "COMPLETED"
    assert backend.cards["card-001"]["status"] == "FROZEN"
    assert backend.freeze_calls == ["card-001"]


def test_non_transfer_cancel_keeps_state(card_app):
    client, backend, _ = card_app
    auth = login(client)
    out = chat(client, auth, message="冻结 日常消费卡")
    thread, intr = out[0][1]["thread_id"], _interrupt(out)

    done = decision(client, auth, thread, intr, "reject")
    assert done[-1][1]["status"] == "REJECTED"
    assert backend.cards["card-001"]["status"] == "ACTIVE"
    assert backend.freeze_calls == []


# ---------------------------------------------------------------------------
# 失败重试不再限定 TRANSFER
# ---------------------------------------------------------------------------


def test_non_transfer_failure_can_retry_with_same_challenge(card_app, monkeypatch):
    """#20 的重试入口原先只接受 TRANSFER；这里证明它对其它写操作同样成立。"""
    client, backend, registry = card_app
    auth = login(client)
    out = chat(client, auth, message="冻结 日常消费卡")
    thread, intr = out[0][1]["thread_id"], _interrupt(out)

    spec = registry.get("card_demo")
    original = spec.execute
    attempts: list[str] = []

    def flaky(operation, params, context):
        attempts.append(operation)
        if len(attempts) == 1:
            raise RuntimeError("private transient diagnostic")
        return original(operation, params, context)

    monkeypatch.setattr(spec, "execute", flaky)

    failed = decision(client, auth, thread, intr)
    assert failed[-1][1]["status"] == "FAILED"
    assert "private transient diagnostic" not in repr(failed)
    assert backend.cards["card-001"]["status"] == "ACTIVE"

    recovered = decision(client, auth, thread, intr)
    assert recovered[-1][1]["status"] == "COMPLETED"
    assert backend.cards["card-001"]["status"] == "FROZEN"
    assert len(attempts) == 2
    assert result(recovered)["data"]["status"] == "FROZEN"

    # 成功后重放不再进入执行节点。
    replay = decision(client, auth, thread, intr)
    assert result(replay) == result(recovered)
    assert len(attempts) == 2


def test_rejected_record_cannot_be_retried_into_execution(card_app):
    """拒绝后同一 challenge 再提交必须被拒，不能翻盘成执行。

    挑战是一次性的：reject 把它消费为终态，服务端记录停在 REJECTED。
    重试入口因此永远拿不到 ``decision == "APPROVED"``。
    """
    client, backend, _ = card_app
    auth = login(client)
    out = chat(client, auth, message="冻结 日常消费卡")
    thread, intr = out[0][1]["thread_id"], _interrupt(out)

    rejected = decision(client, auth, thread, intr, "reject")
    assert rejected[-1][1]["status"] == "REJECTED"

    again = client.post(
        "/agent/chat", headers=auth,
        json={"thread_id": thread,
              "resume": {"challenge_id": intr["challenge_id"], "decision": "approve"}},
    )
    assert again.status_code == 409
    assert again.json()["code"] == "CHALLENGE_INVALID"
    assert backend.freeze_calls == []
    assert backend.cards["card-001"]["status"] == "ACTIVE"


def test_non_transfer_failed_operation_recovers_once_when_backend_returns(card_app, monkeypatch):
    """持续失败时每次重试都重新执行；后端恢复后一次就成功，不会重复执行。"""
    client, backend, registry = card_app
    auth = login(client)
    out = chat(client, auth, message="冻结 日常消费卡")
    thread, intr = out[0][1]["thread_id"], _interrupt(out)

    spec = registry.get("card_demo")
    original = spec.execute
    attempts: list[str] = []

    def always_fail(operation, params, context):
        attempts.append(operation)
        raise RuntimeError("private transient diagnostic")

    monkeypatch.setattr(spec, "execute", always_fail)
    failed = decision(client, auth, thread, intr)
    assert failed[-1][1]["status"] == "FAILED"
    assert len(attempts) == 1
    assert backend.cards["card-001"]["status"] == "ACTIVE"

    monkeypatch.setattr(spec, "execute", original)
    recovered = decision(client, auth, thread, intr)
    assert recovered[-1][1]["status"] == "COMPLETED"
    assert backend.cards["card-001"]["status"] == "FROZEN"
    assert backend.freeze_calls == ["card-001"]
