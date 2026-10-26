"""账单适配层与实际模拟后端的集成；主图路由仍由 A 接入。"""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import re

import pytest
from bankagent.banking import bank_backend
from bankagent.banking.bank_types import BILLS_MAX_RANGE_DAYS, TrustedContext
from bankagent.agent.scenarios import bills


@pytest.fixture
def context(monkeypatch):
    fixed = datetime(2026, 10, 18, 9, tzinfo=timezone(timedelta(hours=8)))
    monkeypatch.setattr(bills, "_clock", lambda: fixed)
    return TrustedContext("user-001", "account-001", "req-bills")


@pytest.mark.parametrize("params,start,end", [
    ({}, date(2026, 10, 1), date(2026, 11, 1)),
    ({"period": "上月"}, date(2026, 9, 1), date(2026, 10, 1)),
    ({"period": " 近7天 "}, date(2026, 10, 12), date(2026, 10, 19)),
    ({"period": "近1天"}, date(2026, 10, 18), date(2026, 10, 19)),
])
def test_normalizes_period_without_mutating_input(context, params, start, end):
    original = deepcopy(params)
    resolved = bills.resolve(params, context)
    assert resolved == {"start": start, "end": end}
    assert bills.validate("QUERY_BILLS", resolved)
    assert params == original


@pytest.mark.parametrize("period", [None, "", "去年", "近0天", "近367天", "近0001天", 7])
def test_invalid_period_does_not_silently_use_current_month(context, period):
    assert not bills.validate("QUERY_BILLS", bills.resolve({"period": period}, context))


@pytest.mark.parametrize("key", ["account_id", "authorized", "start", "operation"])
def test_candidate_cannot_supply_trusted_or_resolved_fields(context, key):
    assert not bills.validate("QUERY_BILLS", bills.resolve({key: "untrusted"}, context))


@pytest.mark.parametrize("instant,start,end", [
    ("2026-01-02T09:00:00+08:00", date(2025, 12, 1), date(2026, 1, 1)),
    ("2024-03-01T09:00:00+08:00", date(2024, 2, 1), date(2024, 3, 1)),
    ("2026-10-17T20:00:00+00:00", date(2026, 9, 1), date(2026, 10, 1)),
])
def test_calendar_and_timezone(context, instant, start, end):
    bills.configure_clock(clock=lambda: datetime.fromisoformat(instant))
    assert bills.resolve({"period": "上月"}, context) == {"start": start, "end": end}


def test_declaration_regex_and_validation_boundaries(context):
    spec = bills.INTENTS["BILLS_QUERY"]
    assert bills.SCENARIO == "bills" and spec["effect"] == "READ" and spec["risk"] == "GREEN"
    assert spec["required"] == [] and bills.CLARIFY_LABELS["period"] == "时间范围"
    assert re.search(spec["slots"]["period"], "看看近7天的账单").group(1) == "近7天"
    edge = bills.resolve({"period": f"近{BILLS_MAX_RANGE_DAYS}天"}, context)
    assert bills.validate("QUERY_BILLS", edge)
    assert not bills.validate("TRANSFER", edge)
    assert not bills.validate("QUERY_BILLS", {**edge, "account_id": "other"})
    assert not bills.validate("QUERY_BILLS", {"start": edge["end"], "end": edge["start"]})


def test_reads_actual_backend_and_only_renders_supported_evidence(context, monkeypatch):
    rows = [dict(transaction_id=f"t{i}", account_id="account-001",
                 occurred_at=f"2026-10-12T10:00:{i:02d}+08:00", kind="EXPENSE",
                 amount_minor=2500, category="订阅", merchant="演示商户") for i in (1, 2)]
    other = {**rows[0], "transaction_id": "private", "account_id": "account-002"}
    credits = [{"transaction_id": "income-1", "account_id": "account-001",
                "occurred_at": "2026-10-01T09:00:00+08:00", "kind": "INCOME",
                "amount_minor": 5000, "category": "工资", "merchant": "演示雇主"},
               {"transaction_id": "income-2", "account_id": "account-002",
                "occurred_at": "2026-10-01T09:00:00+08:00", "kind": "INCOME",
                "amount_minor": 2500, "category": "工资", "merchant": "演示雇主"}]
    data = {"accounts": {"account-001": {"user_id": "user-001", "balance_minor": 0, "currency": "CNY"},
                         "account-002": {"user_id": "user-002", "balance_minor": 0, "currency": "CNY"}},
            "reference_date": date(2026, 10, 18), "contacts": {}, "transactions": [*credits, *rows, other]}
    monkeypatch.setattr(bank_backend, "_backend", None)
    bank_backend.configure_backend(data_factory=lambda: data)
    params = bills.resolve({"period": "本月"}, context)
    result = bills.execute("QUERY_BILLS", params, context)
    assert result["data"]["total_minor"] == 5000
    assert result["data"]["anomalies"][0]["evidence"] == ["t1", "t2"]
    before = deepcopy(result)
    reply = bills.render(result)
    assert "50.00 元" in reply and "最大类别是订阅" in reply
    assert "1 组疑似重复扣款" in reply and "private" not in reply
    assert result == before
    foreign = TrustedContext("user-001", "account-002", "foreign")
    assert bills.execute("QUERY_BILLS", params, foreign)["error_code"] == "ACCOUNT_NOT_ACCESSIBLE"
    assert bank_backend.get_balance(context=context)["data"]["balance_minor"] == 0
    empty = bills.execute("QUERY_BILLS", bills.resolve({"period": "上月"}, context), context)
    assert "没有消费支出记录" in bills.render(empty)
    assert "最大类别" not in bills.render(empty)


@pytest.mark.parametrize("status", ["REJECTED", "FAILED", "PENDING"])
def test_failed_or_pending_result_cannot_render_fake_success(status):
    result = {"operation": "QUERY_BILLS", "status": status, "error_code": "INTERNAL",
              "data": {"total_minor": 999999, "top_category": "伪造类别"}}
    reply = bills.render(result)
    assert "未完成" in reply and "伪造类别" not in reply and "9999" not in reply


def test_bad_params_and_unknown_operation_do_not_call_backend(context, monkeypatch):
    def unexpected(**kwargs):
        pytest.fail("invalid request reached backend")
    monkeypatch.setattr(bank_backend, "query_bills", unexpected)
    bad = bills.execute("QUERY_BILLS", {"start": None, "end": None}, context)
    assert bad["status"] == "REJECTED" and bad["error_code"] == "INVALID_DATE_RANGE"
    assert "时间范围" in bills.render(bad)
    with pytest.raises(ValueError, match="unsupported"):
        bills.execute("TRANSFER", {}, context)


def test_render_ignores_unsupported_or_unresolvable_anomaly_evidence():
    result = {"operation": "QUERY_BILLS", "status": "COMPLETED", "error_code": None,
              "data": {"start": "2026-10-01", "end": "2026-11-01", "currency": "CNY",
                       "total_minor": 1, "by_category": {}, "top_category": "不存在",
                       "transactions": [], "anomalies": [{"type": "POSSIBLE_DUPLICATE",
                                                            "evidence": ["missing1", "missing2"]}]}}
    reply = bills.render(result)
    assert "0.01 元" in reply and "最大类别" not in reply and "重复扣款" not in reply
    result["data"]["anomalies"] = [None, "invalid", {"type": "POSSIBLE_DUPLICATE", "evidence": [[], 1]}]
    assert "重复扣款" not in bills.render(result)
    result["error_code"] = "INTERNAL"
    assert "暂不可用" in bills.render(result)
