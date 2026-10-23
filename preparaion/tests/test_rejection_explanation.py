"""拒绝要说清原因：后端带判断依据，场景层把它讲成人话。

银行场景里「暂时无法办理」等于什么都没说。用户需要知道差多少、超了哪条线，
否则只能反复试。这里同时验证两层：后端把依据带出来，渲染把它用上。
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from threading import RLock

import pytest

from bank_backend import BankBackend
from bank_types import TRANSFER_SINGLE_LIMIT_MINOR, YELLOW_DAILY_LIMIT_MINOR, WriteContext
from scenarios import transfer

BALANCE = 5000_00          # 5000.00 元
TOO_MUCH = 6000_00         # 超过余额
SPENT_TODAY = 800_00       # 已转出
NEXT = 300_00              # 再转，累计 1100 元越过 1000 元阈值


def _data():
    return {
        "accounts": {"a1": {"user_id": "u1", "balance_minor": BALANCE}},
        "contacts": {"c1": {"user_id": "u1", "display_name": "演示收款人"}},
        "transactions": [],
    }


def _hash(context, operation, params):
    payload = [context.user_id, context.account_id, context.request_id, operation, params]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


_hash.__test__ = False


@pytest.fixture
def service():
    clock = [datetime(2026, 10, 18, 9, tzinfo=timezone(timedelta(hours=8)))]
    records = {}
    backend = BankBackend(data_factory=_data, lookup_authorization=records.get,
                          operation_hash=_hash, lock=RLock(), clock=lambda: clock[0])

    def grant(amount, risk="RED", request="r1"):
        context = WriteContext("u1", "a1", request, "ref-" + request, "key-" + request)
        params = {"contact_id": "c1", "amount_minor": amount, "currency": "CNY"}
        records[context.authorization_ref] = dict(
            user_id="u1", account_id="a1", request_id=request, operation="TRANSFER",
            params=params, operation_hash=_hash(context, "TRANSFER", params),
            challenge_id="ch-" + request, risk_level=risk, decision="APPROVED",
            expires_at=clock[0] + timedelta(minutes=5),
            idempotency_key=context.idempotency_key)
        return context

    return backend, grant


# ---------------------------------------------------------------------------
# 后端把依据带出来
# ---------------------------------------------------------------------------


def test_insufficient_balance_reports_balance_and_amount(service):
    backend, grant = service
    result = backend.execute_transfer(context=grant(TOO_MUCH), contact_id="c1",
                                      amount_minor=TOO_MUCH)
    assert result["error_code"] == "INSUFFICIENT_BALANCE"
    assert result["data"] == {"balance_minor": BALANCE, "amount_minor": TOO_MUCH}


def test_single_limit_reports_the_cap(service):
    backend, grant = service
    amount = TRANSFER_SINGLE_LIMIT_MINOR + 1
    result = backend.execute_transfer(context=grant(amount), contact_id="c1",
                                      amount_minor=amount)
    assert result["error_code"] == "TRANSFER_LIMIT_EXCEEDED"
    assert result["data"] == {"amount_minor": amount, "limit_minor": TRANSFER_SINGLE_LIMIT_MINOR}


def test_reauth_reports_what_was_already_spent(service):
    """日累计超标时要说清「今天已经转了多少」，否则用户不知道为什么被拦。

    第一笔用 RED 授权可以越过阈值；第二笔是 YELLOW，累计超标就要重新强认证。
    """
    backend, grant = service
    first = backend.execute_transfer(context=grant(SPENT_TODAY, request="r0"),
                                     contact_id="c1", amount_minor=SPENT_TODAY)
    assert first["status"] == "COMPLETED"

    result = backend.execute_transfer(context=grant(NEXT, risk="YELLOW", request="r1"),
                                      contact_id="c1", amount_minor=NEXT)
    assert result["error_code"] == "REAUTHORIZATION_REQUIRED"
    assert result["data"] == {"daily_total_minor": SPENT_TODAY, "amount_minor": NEXT,
                              "limit_minor": YELLOW_DAILY_LIMIT_MINOR}


# ---------------------------------------------------------------------------
# 渲染把它讲清楚
# ---------------------------------------------------------------------------


def test_render_explains_insufficient_balance_with_numbers():
    text = transfer.render({"operation": "TRANSFER", "status": "REJECTED",
                            "error_code": "INSUFFICIENT_BALANCE",
                            "data": {"balance_minor": BALANCE, "amount_minor": TOO_MUCH}})
    assert "5000.00" in text and "6000.00" in text
    assert "不足" in text


def test_render_explains_daily_limit_with_numbers():
    text = transfer.render({"operation": "TRANSFER", "status": "REJECTED",
                            "error_code": "REAUTHORIZATION_REQUIRED",
                            "data": {"daily_total_minor": SPENT_TODAY,
                                     "amount_minor": NEXT,
                                     "limit_minor": YELLOW_DAILY_LIMIT_MINOR}})
    assert "800.00" in text and "300.00" in text and "1000.00" in text
    assert "强认证" in text


def test_render_explains_single_limit_with_numbers():
    text = transfer.render({"operation": "TRANSFER", "status": "REJECTED",
                            "error_code": "TRANSFER_LIMIT_EXCEEDED",
                            "data": {"amount_minor": TRANSFER_SINGLE_LIMIT_MINOR + 1,
                                     "limit_minor": TRANSFER_SINGLE_LIMIT_MINOR}})
    assert "10000.00" in text and "单笔上限" in text


def test_render_falls_back_when_backend_sends_no_detail():
    """后端没带依据时不能编数字，退回原来的简单文案。"""
    text = transfer.render({"operation": "TRANSFER", "status": "REJECTED",
                            "error_code": "INSUFFICIENT_BALANCE", "data": None})
    assert text == "账户余额不足，转账未执行。"
    assert not any(ch.isdigit() for ch in text)


def test_render_ignores_detail_of_the_wrong_shape():
    text = transfer.render({"operation": "TRANSFER", "status": "REJECTED",
                            "error_code": "INSUFFICIENT_BALANCE",
                            "data": {"balance_minor": "500元", "amount_minor": TOO_MUCH}})
    assert text == "账户余额不足，转账未执行。"
