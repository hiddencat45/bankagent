"""账单只读适配层。尚待 A 的注册器/主图接入，不是独立对话机器人。"""

from datetime import date, datetime, timedelta, timezone
import re
from typing import Callable

from bankagent.banking.bank_types import (BILLS_MAX_RANGE_DAYS, SUPPORTED_CURRENCY,
                        BackendResult, IntentSpec, TrustedContext)


SCENARIO = "bills"
INTENTS: dict[str, IntentSpec] = {
    "BILLS_QUERY": {
        "keywords": ["账单", "消费明细", "花了多少", "支出", "异常消费", "可疑交易"],
        "slots": {"period": r"(本月|上月|近\d+天)"},
        "required": [],  # 未指定期间时查询本月，不猜测缺失身份或业务事实。
        "operation": "QUERY_BILLS", "effect": "READ", "risk": "GREEN",
    }
}
CLARIFY_LABELS = {"period": "时间范围"}
_clock: Callable[[], datetime] = lambda: datetime.now(timezone(timedelta(hours=8)))


def configure_clock(*, clock: Callable[[], datetime]) -> None:
    """服务端启动注入与后端一致的时钟；不接收来自模型或前端的时间基准。"""
    if not callable(clock):
        raise TypeError("clock must be callable")
    global _clock
    _clock = clock


def resolve(candidate_params: dict, context: TrustedContext) -> dict:
    """候选 period → 服务端 start/end；非法候选返回不可通过 validate 的空范围。

    不修改 context/State，不接受候选 start/end、账户 ID 或授权字段。
    只补缺省期间；用户明确提供但不支持的期间不能悄悄退回本月。
    """
    invalid = {"start": None, "end": None}
    if not isinstance(candidate_params, dict) or set(candidate_params) - {"period"}:
        return invalid
    period = candidate_params.get("period", "本月")
    if not isinstance(period, str):
        return invalid
    now = _clock()
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("bills clock must be timezone aware")
    today = now.astimezone(timezone(timedelta(hours=8))).date()
    first = today.replace(day=1)
    period = period.strip()
    if period == "本月":
        end = date(first.year + 1, 1, 1) if first.month == 12 else first.replace(month=first.month + 1)
        return {"start": first, "end": end}
    if period == "上月":
        return {"start": (first - timedelta(days=1)).replace(day=1), "end": first}
    match = re.fullmatch(r"近([1-9]\d{0,2})天", period)
    if match and 1 <= int(match[1]) <= BILLS_MAX_RANGE_DAYS:
        end = today + timedelta(days=1)
        return {"start": end - timedelta(days=int(match[1])), "end": end}
    return invalid


def validate(operation: str, params: dict) -> bool:
    return (operation == "QUERY_BILLS" and isinstance(params, dict)
            and set(params) == {"start", "end"}
            and type(params["start"]) is date and type(params["end"]) is date
            and 0 < (params["end"] - params["start"]).days <= BILLS_MAX_RANGE_DAYS)


def execute(operation: str, params: dict, context: TrustedContext) -> BackendResult:
    if operation != "QUERY_BILLS":
        raise ValueError("unsupported bills operation")
    if not validate(operation, params):
        return {"operation": operation, "status": "REJECTED", "data": None,
                "error_code": "INVALID_DATE_RANGE"}
    from bankagent.banking.bank_backend import query_bills
    return query_bills(context=context, start=params["start"], end=params["end"])


def render(result: BackendResult) -> str:
    """只解释后端事实；不调用工具，不改变状态，不将疑似交易定性为欺诈。"""
    if result.get("operation") != "QUERY_BILLS":
        return "账单查询未完成。"
    if result.get("status") != "COMPLETED":
        return {"INVALID_DATE_RANGE": "请提供有效的时间范围，例如本月、上月或近7天。",
                "TOO_MANY_TRANSACTIONS": "该时间范围交易过多，请缩短查询范围。",
                "ACCOUNT_NOT_ACCESSIBLE": "无法访问当前账户的账单。"}.get(
                    result.get("error_code"), "账单查询尚未完成，请稍后重试。")
    data = result.get("data")
    if not isinstance(data, dict):
        return "账单结果暂不可用。"
    amount = data.get("total_minor")
    if (type(amount) is not int or amount < 0 or data.get("currency") != SUPPORTED_CURRENCY
            or result.get("error_code") is not None):
        return "账单结果暂不可用。"
    try:
        start, end = date.fromisoformat(data["start"]), date.fromisoformat(data["end"])
    except (KeyError, TypeError, ValueError):
        return "账单结果暂不可用。"
    if not start < end:
        return "账单结果暂不可用。"
    label = f"{start.isoformat()} 至 {end.isoformat()}（结束日不含）"
    if amount == 0:
        return f"{label}没有消费支出记录。"
    text = f"{label}共消费 {amount // 100}.{amount % 100:02d} 元。"
    categories = data.get("by_category", {})
    top = data.get("top_category")
    if isinstance(categories, dict) and isinstance(top, str) and top in categories:
        text += f"最大类别是{top}。"
    transactions = data.get("transactions", [])
    ids = {t.get("transaction_id") for t in transactions if isinstance(t, dict)
           and isinstance(t.get("transaction_id"), str)} if isinstance(transactions, list) else set()
    anomalies = data.get("anomalies", [])
    count = 0
    for item in anomalies if isinstance(anomalies, list) else []:
        evidence = item.get("evidence") if isinstance(item, dict) else None
        if (isinstance(item, dict) and item.get("type") == "POSSIBLE_DUPLICATE" and isinstance(evidence, list)
                and all(isinstance(i, str) for i in evidence)
                and len(set(evidence)) >= 2 and set(evidence) <= ids):
            count += 1
    if count:
        text += f"发现 {count} 组疑似重复扣款，可查看交易证据。"
    return text
