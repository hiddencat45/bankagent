"""订阅代扣场景端到端：查询、暂停、澄清、跨账户隔离。

用真实后端与真实注册表（``scenarios/subscription.py`` 已自动发现），不注入
替身。协议状态直接读后端数据集核对，而不是只信接口返回的 status。
"""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from bankagent.agent.agent_security import SG_TZ
from bankagent.api.server import create_app
from bankagent.agent.scenarios import subscription
from test_api_http import chat, decision, login, result


@pytest.fixture
def app(monkeypatch):
    from bankagent.agent.scenarios import bills

    # 两个场景都持有模块级时钟，服务端启动会覆盖；测试结束后必须还原。
    monkeypatch.setattr(bills, "_clock", bills._clock)
    monkeypatch.setattr(subscription, "_clock", subscription._clock)
    with TestClient(
        create_app(demo=True, clock=lambda: datetime(2026, 10, 18, 12, tzinfo=SG_TZ)),
        base_url="http://localhost",
    ) as client:
        yield client


def _rows(client) -> dict[str, dict]:
    """直接读后端数据集里当前账户的协议，用于核对真实状态。"""
    from bankagent.banking import bank_backend
    from bankagent.banking.bank_types import TrustedContext

    result_ = bank_backend.query_subscriptions(
        context=TrustedContext("user-001", "account-001", "inspect"),
        start=date(2026, 10, 1), end=date(2026, 11, 1))
    assert result_["status"] == "COMPLETED"
    return {row["subscription_id"]: row for row in result_["data"]["subscriptions"]}


def _confirm_payload(out):
    return next(data["payload"] for name, data in out
                if name == "card" and data["type"] == "confirm")


def _interrupt(out):
    return next(data for name, data in out if name == "interrupt")


def _message(out):
    return " ".join(data["text"] for name, data in out if name == "message")


# ---------------------------------------------------------------------------
# 意图匹配
# ---------------------------------------------------------------------------


def test_query_keyword_matches_only_the_read_intent():
    from bankagent.agent.scenarios import REGISTRY

    hits = REGISTRY.match_intents("我的订阅有哪些")
    assert [(s, i) for s, i, _ in hits] == [("subscription", "QUERY_SUBSCRIPTIONS")]


def test_pause_keyword_does_not_also_hit_the_query_intent():
    """「暂停订阅」不能同时命中查询，否则明确指令会变成歧义澄清。"""
    from bankagent.agent.scenarios import REGISTRY

    hits = REGISTRY.match_intents("暂停订阅 演示影音会员")
    assert [i for _, i, _ in hits] == ["PAUSE_SUBSCRIPTION"]


def test_bills_wording_does_not_trigger_subscription():
    from bankagent.agent.scenarios import REGISTRY

    assert all(s != "subscription" for s, _, _ in REGISTRY.match_intents("看看我的账单"))


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------


def test_query_lists_own_subscriptions_only(app):
    out = chat(app, login(app), message="我的订阅有哪些")
    data = result(out)

    assert data["operation"] == "QUERY_SUBSCRIPTIONS"
    names = [row["display_name"] for row in data["data"]["subscriptions"]]
    # sub-003 属于 account-002，不得出现。
    assert names == ["演示影音会员", "演示云存储"]
    assert "sub-003" not in repr(out)


def test_query_message_shows_status_amount_and_paid(app):
    text = _message(chat(app, login(app), message="我的订阅有哪些"))
    assert "演示影音会员（生效中，25.00 元/期，本期已扣 50.00 元）" in text
    assert "演示云存储（已暂停，12.00 元/期）" in text
    assert "本期合计扣款 50.00 元" in text


def test_query_defaults_to_current_month(app):
    data = result(chat(app, login(app), message="我的订阅有哪些"))
    assert (data["data"]["start"], data["data"]["end"]) == ("2026-10-01", "2026-11-01")


# ---------------------------------------------------------------------------
# 暂停
# ---------------------------------------------------------------------------


def test_pause_confirm_card_shows_states_without_subscription_id(app):
    out = chat(app, login(app), message="暂停演示影音会员")
    payload = _confirm_payload(out)

    assert payload["operation"] == "PAUSE_SUBSCRIPTION"
    assert payload["risk_level"] == "YELLOW"
    assert payload["display_name"] == "演示影音会员"
    assert payload["current_status"] == "ACTIVE"
    assert payload["target_status"] == "PAUSED"
    # 确认卡不含实体 ID。
    assert "subscription_id" not in payload
    assert "sub-001" not in repr(payload)


def test_pause_requires_a_confirmation_before_changing_state(app):
    auth = login(app)
    out = chat(app, auth, message="暂停演示影音会员")
    thread, intr = out[0][1]["thread_id"], _interrupt(out)

    assert _rows(app)["sub-001"]["status"] == "ACTIVE"

    done = decision(app, auth, thread, intr)
    assert done[-1][1]["status"] == "COMPLETED"
    row = _rows(app)["sub-001"]
    assert row["status"] == "PAUSED"
    assert row["next_payment_date"] is None
    # 暂停不改历史流水，也不动余额。
    assert row["paid_minor"] == 5000


def test_pause_message_states_the_boundary(app):
    auth = login(app)
    out = chat(app, auth, message="暂停演示影音会员")
    done = decision(app, auth, out[0][1]["thread_id"], _interrupt(out))
    text = _message(done)
    assert "已暂停代扣" in text
    # 不能让人以为订阅合同已经终止或退款了。
    assert "商户侧合同需另行取消" in text


def test_cancel_keeps_subscription_active(app):
    auth = login(app)
    out = chat(app, auth, message="暂停演示影音会员")
    done = decision(app, auth, out[0][1]["thread_id"], _interrupt(out), "reject")

    assert done[-1][1]["status"] == "REJECTED"
    assert _rows(app)["sub-001"]["status"] == "ACTIVE"


def test_already_paused_subscription_reports_unchanged(app):
    auth = login(app)
    out = chat(app, auth, message="暂停演示云存储")
    done = decision(app, auth, out[0][1]["thread_id"], _interrupt(out))

    assert done[-1][1]["status"] == "COMPLETED"
    assert "已经是暂停状态，无需再次暂停" in _message(done)


def test_unknown_subscription_asks_for_clarification(app):
    out = chat(app, login(app), message="暂停演示健身")
    # sub-003 属于 account-002，当前账户看不到，不能猜成同名的别家协议。
    assert out[-1][1]["status"] == "NEEDS_CLARIFICATION"
    text = _message(out)
    assert "代扣协议" in text
    # 暂停不该被问「时间范围」——那是查询意图的槽位。
    assert "时间范围" not in text


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code,expected", [
    ("INVALID_DATE_RANGE", "请提供有效的时间范围"),
    ("TOO_MANY_TRANSACTIONS", "扣款笔数过多"),
    ("SUBSCRIPTION_NOT_ACCESSIBLE", "无法访问当前账户的代扣协议"),
])
def test_render_maps_failures(code, expected):
    text = subscription.render({"operation": "QUERY_SUBSCRIPTIONS", "status": "REJECTED",
                                "data": None, "error_code": code})
    assert expected in text
