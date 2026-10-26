"""余额只读场景：在进入图状态前投影后端数据。"""
from bankagent.banking.bank_types import SUPPORTED_CURRENCY, BackendResult, IntentSpec, TrustedContext

SCENARIO = "balance"
INTENTS: dict[str, IntentSpec] = {
    "BALANCE_QUERY": {
        "keywords": ["余额"], "slots": {}, "required": [],
        "operation": "GET_BALANCE", "effect": "READ", "risk": "GREEN",
    }
}


def execute(operation: str, params: dict, context: TrustedContext) -> BackendResult:
    if operation != "GET_BALANCE" or params:
        raise ValueError("invalid balance operation")
    from bankagent.banking.bank_backend import get_balance
    result = get_balance(context=context)
    if result["status"] == "COMPLETED":
        data = result["data"]
        result = {**result, "data": {k: data[k] for k in ("balance_minor", "currency")}}
    return result


def render(result: BackendResult) -> str:
    if result.get("operation") == "GET_BALANCE":
        data = result.get("data") or {}
        amount = data.get("balance_minor")
        if (result.get("status") == "COMPLETED" and type(amount) is int
                and amount >= 0 and data.get("currency") == SUPPORTED_CURRENCY):
            return f"当前可用余额为 {amount // 100}.{amount % 100:02d} CNY。"
        return "余额查询未完成，请稍后重试。"
    return "余额查询未完成，请稍后重试。"
