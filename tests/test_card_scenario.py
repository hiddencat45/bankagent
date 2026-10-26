"""卡片场景端到端：查询、冻结、解冻、澄清、失败重试。

用真实后端与真实注册表（``scenarios/card.py`` 已自动发现），不注入替身。
卡片状态变化直接读后端数据集核对，而不是只信接口返回的 status。
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from bankagent.agent.agent_security import SG_TZ
from bankagent.api.server import create_app
from test_api_http import chat, decision, login, result


@pytest.fixture
def app(monkeypatch):
    from bankagent.agent.scenarios import bills
    monkeypatch.setattr(bills, "_clock", bills._clock)
    with TestClient(
        create_app(demo=True, clock=lambda: datetime(2026, 10, 18, 12, tzinfo=SG_TZ)),
        base_url="http://localhost",
    ) as client:
        yield client


def _cards_state(client) -> dict[str, dict]:
    """直接读后端数据集里当前账户的卡片，用于核对真实状态。"""
    from bankagent.banking import bank_backend
    from bankagent.banking.bank_types import TrustedContext

    session = client.app.state.service
    result_ = bank_backend.query_cards(
        context=TrustedContext("user-001", "account-001", "inspect")
    )
    assert result_["status"] == "COMPLETED"
    return {row["card_id"]: row for row in result_["data"]["cards"]}


def _confirm_payload(out):
    return next(data["payload"] for name, data in out if name == "card" and data["type"] == "confirm")


def _interrupt(out):
    return next(data for name, data in out if name == "interrupt")


def _message(out):
    return " ".join(data["text"] for name, data in out if name == "message")


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------


def test_query_returns_only_own_account_cards(app):
    out = chat(app, login(app), message="我的卡片")
    data = result(out)

    assert data["operation"] == "QUERY_CARDS"
    names = [row["display_name"] for row in data["data"]["cards"]]
    # account-002 也有一张「日常消费卡」（card-003），不得出现在这里。
    assert names == ["日常消费卡", "备用卡"]
    assert "card-003" not in repr(out)
    assert "当前卡片：" in _message(out)


def test_query_message_shows_status(app):
    auth = login(app)
    out = chat(app, auth, message="我的卡片")
    text = _message(out)
    assert "日常消费卡（正常）" in text
    assert "备用卡（冻结）" in text


# ---------------------------------------------------------------------------
# 冻结
# ---------------------------------------------------------------------------


def test_freeze_confirm_card_shows_target_state_without_card_id(app):
    out = chat(app, login(app), message="冻结我的日常消费卡")
    payload = _confirm_payload(out)

    assert payload["operation"] == "FREEZE_CARD"
    assert payload["risk_level"] == "YELLOW"
    assert payload["display_name"] == "日常消费卡"
    assert payload["current_status"] == "ACTIVE"
    assert payload["target_status"] == "FROZEN"
    # 确认卡不含实体 ID：页面无法通过展示字段换一张卡。
    assert "card_id" not in payload
    assert "card-001" not in repr(payload)


def test_freeze_changes_real_status_after_confirm(app):
    auth = login(app)
    out = chat(app, auth, message="冻结我的日常消费卡")
    thread, intr = out[0][1]["thread_id"], _interrupt(out)

    assert _cards_state(app)["card-001"]["status"] == "ACTIVE"

    done = decision(app, auth, thread, intr)
    assert done[-1][1]["status"] == "COMPLETED"
    assert _cards_state(app)["card-001"]["status"] == "FROZEN"
    assert "已冻结" in _message(done)


def test_cancel_keeps_real_status(app):
    auth = login(app)
    out = chat(app, auth, message="冻结我的日常消费卡")
    thread, intr = out[0][1]["thread_id"], _interrupt(out)

    done = decision(app, auth, thread, intr, "reject")
    assert done[-1][1]["status"] == "REJECTED"
    assert _cards_state(app)["card-001"]["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# 解冻
# ---------------------------------------------------------------------------


def test_unfreeze_restores_frozen_card(app):
    auth = login(app)
    out = chat(app, auth, message="解冻 备用卡")
    payload = _confirm_payload(out)
    assert payload["operation"] == "UNFREEZE_CARD"
    assert payload["current_status"] == "FROZEN"
    assert payload["target_status"] == "ACTIVE"

    thread, intr = out[0][1]["thread_id"], _interrupt(out)
    done = decision(app, auth, thread, intr)
    assert done[-1][1]["status"] == "COMPLETED"
    assert _cards_state(app)["card-002"]["status"] == "ACTIVE"
    assert "已解冻" in _message(done)


def test_repeated_freeze_reports_already_frozen(app):
    """重复冻结不报错：返回原回执并说明当前状态，不假装又改了一次。"""
    auth = login(app)
    first = chat(app, auth, message="冻结我的日常消费卡")
    decision(app, auth, first[0][1]["thread_id"], _interrupt(first))
    assert _cards_state(app)["card-001"]["status"] == "FROZEN"

    second = chat(app, auth, message="冻结我的日常消费卡")
    payload = _confirm_payload(second)
    # 确认卡显示的是此刻的真实状态，不是缓存。
    assert payload["current_status"] == "FROZEN"

    done = decision(app, auth, second[0][1]["thread_id"], _interrupt(second))
    assert done[-1][1]["status"] == "COMPLETED"
    assert "已经是冻结状态" in _message(done)
    assert _cards_state(app)["card-001"]["status"] == "FROZEN"


# ---------------------------------------------------------------------------
# 澄清与拒绝
# ---------------------------------------------------------------------------


def test_unknown_card_name_asks_for_clarification(app):
    out = chat(app, login(app), message="冻结 幽灵卡")
    assert out[-1][1]["status"] == "NEEDS_CLARIFICATION"
    assert "当前账户下匹配的卡片" in _message(out)
    assert not any(name == "interrupt" for name, _ in out)


def test_hesitation_word_blocks_card_write_without_confirming(app):
    """含否定/犹豫词的写操作不发起，也不弹确认卡。

    "不存在的卡"里的"不"会命中犹豫检测——这是有意的保守取舍：宁可多问
    一次，也不把"不用了"误当成要执行。因此这里断言的是拦下了操作，
    而不是解析出了卡名。
    """
    out = chat(app, login(app), message="冻结 不存在的卡")
    assert out[-1][1]["status"] == "NEEDS_CLARIFICATION"
    assert not any(name == "interrupt" for name, _ in out)
    assert "转账" not in _message(out)


def test_cross_account_card_name_cannot_be_resolved(app):
    """account-002 的卡名在本账户下同样叫「日常消费卡」，只能命中自己那张。"""
    auth = login(app)
    out = chat(app, auth, message="冻结 日常消费卡")
    payload = _confirm_payload(out)
    assert payload["display_name"] == "日常消费卡"
    # 解析到的一定是 account-001 的卡，执行后 account-002 的卡不受影响。
    decision(app, auth, out[0][1]["thread_id"], _interrupt(out))
    assert _cards_state(app)["card-001"]["status"] == "FROZEN"
    from bankagent.banking import bank_backend
    from bankagent.banking.bank_types import TrustedContext
    other = bank_backend.query_cards(context=TrustedContext("user-002", "account-002", "inspect-2"))
    assert other["data"]["cards"][0]["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# resolve 的重名/查无：现有数据集在同一账户下没有同名卡，用替身直接测这条边界
# ---------------------------------------------------------------------------


def test_resolve_never_picks_one_of_two_same_named_cards(monkeypatch):
    """同账户存在同名卡时必须澄清，不能按顺序任选一张。"""
    from bankagent.banking.bank_types import TrustedContext
    from bankagent.agent.scenarios import card as card_module

    monkeypatch.setattr(card_module, "_cards", lambda context: [
        {"card_id": "card-a", "display_name": "日常消费卡", "status": "ACTIVE"},
        {"card_id": "card-b", "display_name": "日常消费卡", "status": "FROZEN"},
    ])
    params = card_module.resolve(
        {"card_name": "日常消费卡"}, TrustedContext("user-001", "account-001", "req-1")
    )
    assert params == {}, "重名时必须不写 card_id，由公共层转入澄清"


def test_resolve_returns_empty_when_card_not_found(monkeypatch):
    from bankagent.banking.bank_types import TrustedContext
    from bankagent.agent.scenarios import card as card_module

    monkeypatch.setattr(card_module, "_cards", lambda context: [
        {"card_id": "card-a", "display_name": "日常消费卡", "status": "ACTIVE"},
    ])
    params = card_module.resolve(
        {"card_name": "幽灵卡"}, TrustedContext("user-001", "account-001", "req-1")
    )
    assert params == {}


def test_resolve_matches_exact_name_only(monkeypatch):
    """子串不算匹配：「日常」不能解析到「日常消费卡」，否则会误伤短名。"""
    from bankagent.banking.bank_types import TrustedContext
    from bankagent.agent.scenarios import card as card_module

    monkeypatch.setattr(card_module, "_cards", lambda context: [
        {"card_id": "card-a", "display_name": "日常消费卡", "status": "ACTIVE"},
    ])
    params = card_module.resolve(
        {"card_name": "日常"}, TrustedContext("user-001", "account-001", "req-1")
    )
    assert params == {}


def test_ownership_failure_is_not_treated_as_empty_card_list(app):
    """越权查询必须报错，不能伪装成「没有这张卡」——后者会变成无限澄清。"""
    from bankagent.banking import bank_backend
    from bankagent.banking.bank_types import TrustedContext
    from bankagent.agent.scenarios import card as card_module

    # account-001 的用户配 account-002 的合同 → 归属失败
    with pytest.raises(PermissionError):
        card_module._cards(TrustedContext("user-001", "account-002", "req-x"))


# ---------------------------------------------------------------------------
# 失败重试（#30 去掉 TRANSFER 限定后的真实场景验证）
# ---------------------------------------------------------------------------


def test_card_failure_can_retry_with_same_challenge(app, monkeypatch):
    from bankagent.agent.scenarios import REGISTRY

    auth = login(app)
    out = chat(app, auth, message="冻结我的日常消费卡")
    thread, intr = out[0][1]["thread_id"], _interrupt(out)

    spec = REGISTRY.get("card")
    original = spec.execute
    attempts: list[str] = []

    def flaky(operation, params, context):
        attempts.append(operation)
        if len(attempts) == 1:
            raise RuntimeError("private transient diagnostic")
        return original(operation, params, context)

    monkeypatch.setattr(spec, "execute", flaky)

    failed = decision(app, auth, thread, intr)
    assert failed[-1][1]["status"] == "FAILED"
    assert "private transient diagnostic" not in repr(failed)
    assert _cards_state(app)["card-001"]["status"] == "ACTIVE"

    recovered = decision(app, auth, thread, intr)
    assert recovered[-1][1]["status"] == "COMPLETED"
    assert _cards_state(app)["card-001"]["status"] == "FROZEN"
    assert len(attempts) == 2

    replay = decision(app, auth, thread, intr)
    assert result(replay) == result(recovered)
    assert len(attempts) == 2
