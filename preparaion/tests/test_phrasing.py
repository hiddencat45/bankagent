"""措辞改写层：改写成功、编造拦截、各类回退。

这一层不产生事实，只改措辞；测试重点是**凡是可能出错的情况都必须回退原文**。
"""

import pytest

from agent_phrasing import ResponsePhraser

REFERENCE = "演示影音会员 已暂停代扣，后续不会再自动扣款；商户侧合同需另行取消。"
BALANCE = "当前可用余额为 5000.00 CNY。"


class FakeModel:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def predict(self, request):
        self.calls.append(request)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply

    def health(self):
        return True


def _result(**extra):
    return {"operation": "PAUSE_SUBSCRIPTION", "status": "COMPLETED",
            "data": {"display_name": "演示影音会员", "subscription_id": "sub-001"},
            "error_code": None, **extra}


# ---------------------------------------------------------------------------
# 直通
# ---------------------------------------------------------------------------


def test_without_model_the_reference_is_returned_untouched():
    assert ResponsePhraser(None).phrase(_result(), REFERENCE) == REFERENCE


def test_empty_reference_stays_empty():
    assert ResponsePhraser(FakeModel("随便什么")).phrase(_result(), "") == ""


def test_short_reference_is_not_sent_to_the_model():
    """短文案改写收益低、出错代价高，直接不送模型。"""
    model = FakeModel("好的")
    assert ResponsePhraser(model).phrase(_result(), "已暂停") == "已暂停"
    assert model.calls == []


# ---------------------------------------------------------------------------
# 正常改写
# ---------------------------------------------------------------------------


def test_model_rewrite_is_used_when_it_adds_no_numbers():
    rewritten = "演示影音会员的代扣已经暂停了，以后不会再自动扣款。"
    model = FakeModel(rewritten)
    assert ResponsePhraser(model).phrase(_result(), REFERENCE) == rewritten
    assert model.calls


def test_request_declares_text_mode_and_carries_facts():
    model = FakeModel("演示影音会员已暂停代扣，以后不会再自动扣款。")
    ResponsePhraser(model).phrase(_result(), REFERENCE)
    request = model.calls[-1]
    assert request["format"] == "text"
    assert request["facts"]["reference_text"] == REFERENCE
    assert request["facts"]["operation"] == "PAUSE_SUBSCRIPTION"


def test_facts_never_carry_entity_ids():
    """模型不该看到 card_id / subscription_id 这类内部标识。"""
    model = FakeModel("演示影音会员已暂停代扣，以后不会再自动扣款。")
    ResponsePhraser(model).phrase(_result(), REFERENCE)
    facts = model.calls[-1]["facts"]
    assert "sub-001" not in repr(facts)
    assert "subscription_id" not in repr(facts)
    assert facts["data"]["display_name"] == "演示影音会员"


def test_number_formatting_change_is_accepted():
    """25.00 写成 25、5000.00 写成 5000 是正常润色，不该判成编造。"""
    rewritten = "演示影音会员已暂停，之前扣的 50 元不会再扣。"
    model = FakeModel(rewritten)
    result = {"operation": "X", "status": "COMPLETED", "data": {"amount_minor": 5000},
              "error_code": None}
    assert ResponsePhraser(model).phrase(result, "本期已扣 50.00 元。") == rewritten


# ---------------------------------------------------------------------------
# 回退
# ---------------------------------------------------------------------------


def test_invented_number_falls_back():
    """原文没有 999，模型编出来就必须回退。"""
    model = FakeModel("演示影音会员已暂停，为您退回 999 元。")
    assert ResponsePhraser(model).phrase(_result(), REFERENCE) == REFERENCE


# ---------------------------------------------------------------------------
# 结论口径：系统没给成功信号，模型就不许说成功
# ---------------------------------------------------------------------------

FAILED_REFERENCE = "账户余额 5000.00 元，不足以支付这笔 6000.00 元，转账未执行。"
FAILED_RESULT = {"operation": "TRANSFER", "status": "REJECTED", "error_code": "INSUFFICIENT_BALANCE",
                 "data": {"balance_minor": 500000, "amount_minor": 600000}}


def test_success_wording_is_blocked_when_reference_reports_failure():
    """把「未执行」润色成「已完成」必须拦下——数字和长度都没变，只换了结论。"""
    model = FakeModel("账户余额 5000.00 元，不足以支付这笔 6000.00 元，转账已完成。")
    assert ResponsePhraser(model).phrase(FAILED_RESULT, FAILED_REFERENCE) == FAILED_REFERENCE


def test_transferred_wording_is_blocked_too():
    """宾语插进动词中间的写法（「已向张伟转账」）同样算宣称成功。"""
    model = FakeModel("账户余额 5000.00 元，不足以支付这笔 6000.00 元，已向张伟转账 6000.00 元。")
    assert ResponsePhraser(model).phrase(FAILED_RESULT, FAILED_REFERENCE) == FAILED_REFERENCE


def test_failure_wording_still_passes_when_reference_failed():
    """失败结论本身可以润色，只要不翻案。"""
    rewritten = "您的账户只有 5000.00 元，付不了这笔 6000.00 元，转账没有执行。"
    model = FakeModel(rewritten)
    assert ResponsePhraser(model).phrase(FAILED_RESULT, FAILED_REFERENCE) == rewritten


def test_negated_success_is_not_counted_as_success():
    """「没有执行成功」是否定语境，不能算肯定结论。"""
    from agent_phrasing import _claims_success

    assert _claims_success("转账没有执行成功") is False
    assert _claims_success("本次操作未能成功") is False
    assert _claims_success("已向张伟转账 300.00 元") is True
    assert _claims_success("这笔转账未执行") is False


def test_success_wording_is_allowed_when_reference_succeeded():
    """系统确实返回了 COMPLETED，模型说成功就没问题。"""
    reference = "已向张伟转账 300.00 元，剩余余额 4700.00 元。"
    result = {"operation": "TRANSFER", "status": "COMPLETED", "error_code": None,
              "data": {"amount_minor": 30000, "remaining_balance_minor": 470000,
                       "recipient": "张伟", "currency": "CNY"}}
    model = FakeModel("给张伟转的 300.00 元已经成功到账，剩余 4700.00 元。")
    assert ResponsePhraser(model).phrase(result, reference) == model.reply


def test_model_exception_falls_back():
    model = FakeModel(RuntimeError("upstream down"))
    assert ResponsePhraser(model).phrase(_result(), REFERENCE) == REFERENCE


def test_non_string_output_falls_back():
    model = FakeModel({"text": "不是字符串"})
    assert ResponsePhraser(model).phrase(_result(), REFERENCE) == REFERENCE


def test_too_short_output_falls_back():
    model = FakeModel("已暂停。")
    assert ResponsePhraser(model).phrase(_result(), REFERENCE) == REFERENCE


def test_too_long_output_falls_back():
    model = FakeModel("演示影音会员已暂停代扣。" * 20)
    assert ResponsePhraser(model).phrase(_result(), REFERENCE) == REFERENCE


def test_fallback_is_counted_for_observability():
    model = FakeModel("演示影音会员已暂停，为您退回 999 元。")
    phraser = ResponsePhraser(model)
    phraser.phrase(_result(), REFERENCE)
    assert phraser.stats() == {"rewritten": 0, "fallback": 1}


# ---------------------------------------------------------------------------
# 接入主图
# ---------------------------------------------------------------------------


def test_compose_response_uses_the_phraser(monkeypatch):
    """主图回复出口必须走改写层，而不是直接返回模板。"""
    from datetime import datetime

    from fastapi.testclient import TestClient

    from agent_security import SG_TZ
    from api.server import create_app
    from test_api_http import chat, login

    rewritten = ("您当前有两条代扣协议：演示影音会员生效中，25.00 元一期，本期已扣 50.00 元；"
                 "演示云存储已暂停，12.00 元一期。本期合计扣款 50.00 元。")
    clock = lambda: datetime(2026, 10, 18, 12, tzinfo=SG_TZ)
    app = create_app(demo=True, clock=clock, phraser=ResponsePhraser(FakeModel(rewritten)))
    with TestClient(app, base_url="http://localhost") as client:
        out = chat(client, login(client), message="我的订阅有哪些")
    texts = [data["text"] for name, data in out if name == "message"]
    assert texts and texts[-1] == rewritten
