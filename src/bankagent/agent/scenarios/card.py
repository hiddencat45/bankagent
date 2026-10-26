"""卡片场景：查询卡片、冻结、解冻。

本模块只声明意图、把候选卡名解析成受控 ``card_id``、分发到后端。它
**不**改余额、不产生资金流水、不判定授权——那些是后端与公共安全层的职责。

三个边界：

- ``card_id`` 只能来自受控后端查询（``query_cards``），**绝不**由模型或
  ``candidate_params`` 直接提供；
- 确认卡只展示「对哪张卡做什么」，不含 ``card_id``；执行对象由服务端绑定
  的挑战记录决定，页面无法通过篡改展示字段换一张卡；
- 查询归属失败按受控拒绝处理，不伪装成「没有这张卡」——后者会引导用户
  反复澄清，把越权探测变成一次正常的追问。
"""

from __future__ import annotations

from typing import Any

from bankagent.banking.bank_types import (
    BackendResult,
    IntentSpec,
    TrustedContext,
)

SCENARIO = "card"

INTENTS: dict[str, IntentSpec] = {
    "CARD_QUERY": {
        # 不用单字「卡」：它是「日常消费卡」这类卡名的子串，会让「冻结我的
        # 日常消费卡」同时命中查询与冻结，把明确指令变成一次歧义澄清。
        "keywords": ["我的卡片", "有哪些卡", "卡片列表", "查卡", "所有卡片", "几张卡"],
        "slots": {},
        "required": [],
        "operation": "QUERY_CARDS",
        "effect": "READ",
        "risk": "GREEN",
    },
    "CARD_FREEZE": {
        "keywords": ["冻结", "锁卡"],
        "slots": {"card_name": r"冻结\s*(?:我的)?\s*(\S+)"},
        "required": ["card_name"],
        "operation": "FREEZE_CARD",
        "effect": "WRITE",
        # 写操作最低 YELLOW；冻结不涉及金额，没有需要升高的情形。
        "risk": "YELLOW",
    },
    "CARD_UNFREEZE": {
        "keywords": ["解冻", "解锁"],
        "slots": {"card_name": r"解冻\s*(?:我的)?\s*(\S+)"},
        "required": ["card_name"],
        "operation": "UNFREEZE_CARD",
        "effect": "WRITE",
        "risk": "YELLOW",
    },
}

CLARIFY_LABELS = {
    "card_name": "要操作的卡片",
    "card_id": "当前账户下匹配的卡片",
}

# 操作 → 目标状态。UNFREEZE 的目标是 ACTIVE，不是「未冻结」这类中间态。
_TARGET_STATUS: dict[str, str] = {"FREEZE_CARD": "FROZEN", "UNFREEZE_CARD": "ACTIVE"}

# 操作 → (动词, 完成语)。用于 render，不参与判定。
_VERB: dict[str, tuple[str, str]] = {
    "FREEZE_CARD": ("冻结", "已冻结"),
    "UNFREEZE_CARD": ("解冻", "已解冻"),
}

_STATUS_TEXT: dict[str, str] = {"PENDING_ACTIVATION": "待激活", "ACTIVE": "正常", "FROZEN": "冻结"}


def _cards(context: TrustedContext) -> list[dict[str, Any]]:
    """当前账户的卡片投影。

    归属失败是受控拒绝，不是「查询结果为空」：抛 ``PermissionError`` 让公共
    边界统一转成 ``REJECTED`` / ``ACCOUNT_NOT_ACCESSIBLE``，与转账场景
    ``find_contacts`` 的归属语义保持一致。
    """
    from bankagent.banking.bank_backend import query_cards

    result = query_cards(context=context)
    if result["status"] != "COMPLETED":
        raise PermissionError(result.get("error_code") or "ACCOUNT_NOT_ACCESSIBLE")
    return list((result.get("data") or {}).get("cards") or [])


def resolve(candidate_params: dict, context: TrustedContext) -> dict:
    """候选卡名 → 受控参数 ``{card_id}``。

    精确匹配 ``display_name``：零个匹配（查无此卡）与多个匹配（同名卡）都
    **不**写入 ``card_id``，由公共层转入澄清——绝不任选一张。
    """
    params: dict[str, Any] = {}
    name = candidate_params.get("card_name")
    if isinstance(name, str) and name.strip():
        target = name.strip()
        matches = [row for row in _cards(context) if row.get("display_name") == target]
        if len(matches) == 1:
            params["card_id"] = matches[0]["card_id"]
    return params


def validate(operation: str, params: dict) -> bool:
    if operation == "QUERY_CARDS":
        return True
    card_id = params.get("card_id")
    return operation in _TARGET_STATUS and isinstance(card_id, str) and bool(card_id)


def confirmation(*, operation: str, params: dict, candidate_params: dict,
                 context: TrustedContext) -> dict:
    """确认卡展示字段：卡名、当前状态、目标状态。**不含 card_id。**

    当前状态在生成确认卡时重新查一次，而不是复用 ``resolve`` 时的结果——
    确认卡要反映用户此刻看到的真实状态，哪怕期间它被改过。
    """
    card_id = params.get("card_id")
    card = next((row for row in _cards(context) if row.get("card_id") == card_id), None)
    if card is None:
        raise ValueError("卡片绑定已失效，无法生成确认卡")
    return {
        "display_name": card["display_name"],
        "current_status": card["status"],
        "target_status": _TARGET_STATUS[operation],
    }


def execute(operation: str, params: dict, context: TrustedContext) -> BackendResult:
    """分发到后端。授权重查、幂等、归属复检全部在后端锁内完成。"""
    if operation == "QUERY_CARDS":
        from bankagent.banking.bank_backend import query_cards

        return query_cards(context=context)

    from bankagent.banking.bank_backend import freeze_card, unfreeze_card

    if operation == "FREEZE_CARD":
        return freeze_card(context=context, card_id=params["card_id"])  # type: ignore[arg-type]
    if operation == "UNFREEZE_CARD":
        return unfreeze_card(context=context, card_id=params["card_id"])  # type: ignore[arg-type]
    raise ValueError("unsupported card operation")


def render(result: BackendResult) -> str:
    """只解释后端事实；失败或处理中不得显示成功。"""
    operation = result.get("operation")
    if result.get("status") != "COMPLETED":
        return "卡片操作未完成，请稍后重试。"
    data = result.get("data") or {}

    if operation == "QUERY_CARDS":
        cards = data.get("cards") or []
        if not cards:
            return "当前账户下没有可查询的卡片。"
        parts = [
            f"{row['display_name']}（{_STATUS_TEXT.get(row['status'], row['status'])}）"
            for row in cards
        ]
        return "当前卡片：" + "、".join(parts) + "。"

    if operation in _VERB:
        name = data.get("display_name") or "该卡"
        if data.get("changed") is False:
            # 幂等重放或重复操作：返回的是历史回执，卡片本来就是这个状态。
            verb = _VERB[operation][0]
            return f"{name} 已经是{_STATUS_TEXT.get(data.get('status'), data.get('status'))}状态，无需再次{verb}。"
        return f"{name} {_VERB[operation][1]}。"

    return "卡片操作未完成，请稍后重试。"
