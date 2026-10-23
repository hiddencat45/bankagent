"""已登记代扣协议与历史扣费；暂停不退款、不取消商户合同。"""

from bank_backend import find_subscriptions, pause_subscription, query_subscriptions
from bank_types import BackendResult, TrustedContext
from scenarios import bills

SCENARIO = "subscription"
INTENTS = {
    "SUBSCRIPTIONS_QUERY": {
        "keywords": ["我的订阅", "有哪些订阅", "订阅列表", "查询订阅", "查看订阅", "订阅扣费", "代扣记录"],
        "slots": {"period": r"(本月|上月|近\d+天)"}, "required": [],
        "operation": "QUERY_SUBSCRIPTIONS", "effect": "READ", "risk": "GREEN",
    },
    "SUBSCRIPTION_PAUSE": {
        "keywords": ["暂停"],
        "slots": {"subscription_name": r"暂停\s*(.+?)(?:的代扣|的订阅)?[。！!？?]?$"},
        "required": ["subscription_name"],
        "operation": "PAUSE_SUBSCRIPTION", "effect": "WRITE", "risk": "YELLOW",
    },
}
CLARIFY_LABELS = {"subscription_name": "代扣协议名称", "subscription_id": "可唯一确定的代扣协议"}


def resolve(candidate_params: dict, context: TrustedContext) -> dict:
    if set(candidate_params) <= {"period"}:
        params = bills.resolve(candidate_params, context)
        if not bills.validate("QUERY_BILLS", params):
            raise ValueError("invalid subscription period")
        return params
    if set(candidate_params) != {"subscription_name"}:
        raise ValueError("unexpected subscription candidates")
    matches = find_subscriptions(context=context, name=candidate_params["subscription_name"])
    return {"subscription_id": matches[0]["subscription_id"]} if len(matches) == 1 else {}


def validate(operation: str, params: dict) -> bool:
    if operation == "QUERY_SUBSCRIPTIONS":
        return bills.validate("QUERY_BILLS", params)
    return (operation == "PAUSE_SUBSCRIPTION" and set(params) == {"subscription_id"}
            and isinstance(params["subscription_id"], str) and bool(params["subscription_id"]))


def confirmation(*, params: dict, candidate_params: dict, context: TrustedContext) -> dict:
    """只投影已绑定协议的展示字段；复用公共确认卡钩子。"""
    rows = find_subscriptions(context=context, name=candidate_params.get("subscription_name", ""))
    row = next((r for r in rows if r["subscription_id"] == params.get("subscription_id")), None)
    if row is None:
        raise ValueError("subscription binding no longer matches")
    return {"display_name": row["display_name"], "current_status": row["status"], "target_status": "PAUSED"}


def execute(operation: str, params: dict, context: TrustedContext) -> BackendResult:
    if not validate(operation, params):
        return {"operation": operation, "status": "REJECTED", "data": None, "error_code": "INVALID_PARAMS"}
    if operation == "QUERY_SUBSCRIPTIONS":
        return query_subscriptions(context=context, start=params["start"], end=params["end"])
    return pause_subscription(context=context, subscription_id=params["subscription_id"])


def render(result: BackendResult) -> str:
    if result["status"] != "COMPLETED":
        return {
            "USER_CANCELLED": "已取消暂停，代扣协议状态未改变。",
            "INVALID_PARAMS": "请明确协议名称，或提供有效期间：本月、上月、近7天。",
            "INVALID_DATE_RANGE": "请提供有效查询期间：本月、上月、近7天。",
            "TOO_MANY_TRANSACTIONS": "关联扣费过多，请缩短查询期间。",
            "ACCOUNT_NOT_ACCESSIBLE": "无法访问当前账户。",
            "SUBSCRIPTION_NOT_ACCESSIBLE": "无法使用该代扣协议，请重新选择。",
            "AUTHORIZATION_REQUIRED": "请先确认暂停操作。",
            "AUTHORIZATION_INVALID": "确认已失效或不匹配，请重新发起暂停。",
            "IDEMPOTENCY_CONFLICT": "同一请求的办理对象不一致，已拒绝变更。",
        }.get(result.get("error_code"), "办理结果尚未确认，请核对协议状态。")
    data = result["data"]
    if result["operation"] == "QUERY_SUBSCRIPTIONS":
        if not data["subscriptions"]:
            return "本账户暂无已登记的代扣协议。"
        amount = data["total_minor"]
        return (f"本账户共 {len(data['subscriptions'])} 个已登记月度协议；"
                f"本期实际扣费 {amount // 100}.{amount % 100:02d} 元，可查看每笔证据。"
                "协议状态与历史扣费分别展示，疑似重复扣费需进一步核对。")
    return (f"{data['display_name']}的本次暂停请求已办理"
            + ("，办理时已是暂停状态。" if not data["changed"] else "，模拟协议状态已改为暂停。")
            + "历史扣费不变；尚未模拟后续扣款，不表示商户合同取消或退款。")
