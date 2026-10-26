"""转账场景：把教学图里的转账逻辑按契约收敛为场景模块。

本模块只做三件事：把候选槽位解析成受控参数、声明风险、分发到后端。
它**不**扣款、不写余额、不判定授权——那些是后端与公共安全层的职责。

与旧教学文件 ``bank_agent_graph.py`` 的关系：

- 操作名从 ``PREPARE_TRANSFER`` 改为契约约定的 ``TRANSFER``，表示贯穿
  准备、确认、执行的业务操作；``execute_transfer`` 仍是服务端私有函数；
- 金额从 ``float`` 元改为**整数分** ``amount_minor``，换算用 ``Decimal``，
  超过两位小数直接拒绝，不暗自四舍五入；
- 风险阈值引用 ``bank_types`` 的常量，不在这里另写一份。

按契约 §3.2，旧教学文件本次不改；本模块是新的场景实现，两者暂时共存，
由注册器决定主图使用哪一套。
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any

from bankagent.banking.bank_types import (
    SUPPORTED_CURRENCY,
    TRANSFER_SINGLE_LIMIT_MINOR,
    YELLOW_DAILY_LIMIT_MINOR,
    BackendResult,
    IntentSpec,
    RiskLevel,
    TrustedContext,
)

SCENARIO = "transfer"

INTENTS: dict[str, IntentSpec] = {
    "TRANSFER": {
        # 离线规则模式的匹配词。真实模型可理解同义表达，keywords 不限制它。
        "keywords": ["转", "转账", "汇", "打钱"],
        "slots": {
            "recipient_name": r"给\s*(.+?)\s*转",
            "amount": r"转(?:账)?\s*([+\-0-9][^\s元，。！？!?；;]*)",
        },
        "required": ["recipient_name", "amount"],
        "operation": "TRANSFER",
        "effect": "WRITE",
        # 写操作最低 YELLOW；本场景的 risk 钩子只能在此基础上升高。
        "risk": "YELLOW",
    }
}

CLARIFY_LABELS = {
    "recipient_name": "收款人",
    "amount": "金额",
    "contact_id": "通讯录中的有效收款人",
}

# 金额允许的最大小数位。超过即拒绝，不做四舍五入——资金计算不能悄悄改数。
_MAX_DECIMAL_PLACES = 2


def _to_minor(amount: Any) -> int | None:
    """把候选金额转成整数分；非法输入返回 ``None``，由调用方进入澄清/拒绝。

    只用 ``Decimal`` 解析，避免 ``float`` 的二进制误差（例如 0.1 + 0.2）。
    """
    if amount is None or isinstance(amount, bool):
        return None

    if isinstance(amount, int):
        # 整数按「元」解释，与用户口语「转 300 元」一致。
        value = Decimal(amount)
    elif isinstance(amount, float):
        # 显式拒绝 float：契约禁止 float 金额，这里不静默转换。
        return None
    elif isinstance(amount, Decimal):
        value = amount
    elif isinstance(amount, str):
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", amount.strip()):
            return None
        try:
            value = Decimal(amount.strip())
        except (InvalidOperation, ValueError):
            return None
    else:
        return None

    if not value.is_finite() or value <= 0:
        return None

    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and -exponent > _MAX_DECIMAL_PLACES:
        return None  # 超过两位小数，拒绝而不是四舍五入

    minor = value * 100
    if minor != minor.to_integral_value():
        return None
    return int(minor)


def resolve(candidate_params: dict, context: TrustedContext) -> dict:
    """候选槽位 → 受控参数 ``{contact_id, amount_minor, currency}``。

    ``contact_id`` 必须来自受控后端查询（``find_contacts``），
    **绝不能**由模型或 ``candidate_params`` 直接提供。查不到联系人或
    存在重名时，返回缺少 ``contact_id`` 的结果，由公共层转入澄清。

    ``find_contacts`` 在归属失败时会抛 ``PermissionError``（B 的契约选择）；
    本函数**不捕获**它，交由注册器在公共边界统一转成
    ``REJECTED`` / ``ACCOUNT_NOT_ACCESSIBLE``，避免各场景重复处理。
    """
    params: dict[str, Any] = {}

    # 金额：候选值只接受字符串/整数/Decimal，float 直接视为非法。
    amount_minor = _to_minor(candidate_params.get("amount"))
    if amount_minor is not None:
        params["amount_minor"] = amount_minor

    # 币种固定 CNY，不接受候选指定其它币种。
    params["currency"] = SUPPORTED_CURRENCY

    # 联系人：只接受姓名搜索词，由后端解析成 ID。
    recipient = candidate_params.get("recipient_name")
    if isinstance(recipient, str) and recipient.strip():
        from bankagent.banking.bank_backend import find_contacts

        matches = find_contacts(context=context, name=recipient.strip())
        if len(matches) == 1:
            params["contact_id"] = matches[0]["contact_id"]
        # 0 条：查不到；多条：重名歧义。两种情况都不写入 contact_id，
        # 由公共层根据缺失字段进入澄清——不任选一条。

    return params


def validate(operation: str, params: dict) -> bool:
    """附加业务校验：参数形状与取值范围。"""
    if operation != "TRANSFER" or not isinstance(params, dict):
        return False
    if set(params) != {"contact_id", "amount_minor", "currency"}:
        return False
    if not isinstance(params["contact_id"], str) or not params["contact_id"]:
        return False
    if type(params["amount_minor"]) is not int or params["amount_minor"] <= 0:
        return False
    if params["currency"] != SUPPORTED_CURRENCY:
        return False
    # 单笔上限：超过即视为配置外的请求，交给风险层判 DENY。
    return params["amount_minor"] <= TRANSFER_SINGLE_LIMIT_MINOR


def risk(operation: str, params: dict, context: TrustedContext) -> RiskLevel:
    """在静态最低 YELLOW 之上按业务事实升高风险。

    - 单笔超过上限 → DENY；
    - 当日累计（含本笔）超过 YELLOW 阈值 → RED（需要强认证）。

    当日累计必须来自**服务端**后端查询，不接受客户端提供的累计值。
    查询失败时不降级为 YELLOW，而是抛错让上层失败——安全相关不允许降级。
    """
    if operation != "TRANSFER":
        return "DENY"

    amount_minor = params.get("amount_minor")
    if type(amount_minor) is not int or amount_minor <= 0:
        return "DENY"
    if amount_minor > TRANSFER_SINGLE_LIMIT_MINOR:
        return "DENY"

    from bankagent.banking.bank_backend import get_balance

    balance_result = get_balance(context=context)
    if balance_result.get("status") != "COMPLETED":
        # 拿不到可信累计量时不能假设「今天还没转过钱」。
        raise ValueError("cannot evaluate transfer risk without trusted daily total")

    data = balance_result.get("data") or {}
    daily_total = data.get("daily_transfer_total_minor")
    if type(daily_total) is not int or daily_total < 0:
        raise ValueError("backend returned invalid daily_transfer_total_minor")

    projected = daily_total + amount_minor
    return "RED" if projected > YELLOW_DAILY_LIMIT_MINOR else "YELLOW"


def confirmation(*, operation: str, params: dict, candidate_params: dict,
                 context: TrustedContext) -> dict:
    """确认卡展示字段：收款人姓名、金额、币种。

    ``params['contact_id']`` 是已绑定的受控结果。这里按同一次姓名候选回查
    后端再核对这个 ID，**不把内部 ID 当展示名**，也不重新解析一个新的收款人
    （确认卡必须反映用户将要确认的那笔操作，不能悄悄换人）。

    核对不上说明绑定事实与查询结果不一致，直接抛错让上层按失败处理——
    弹一张收款人为空的确认卡让用户去点"确认"更危险。
    """
    from bankagent.banking.bank_backend import find_contacts

    contact_id = params.get("contact_id")
    name = candidate_params.get("recipient_name")
    recipient = None
    if isinstance(contact_id, str) and contact_id and isinstance(name, str) and name.strip():
        for row in find_contacts(context=context, name=name.strip()):
            if row["contact_id"] == contact_id:
                recipient = row["display_name"]
                break
    if recipient is None:
        raise ValueError("收款人绑定已失效，无法生成确认卡")

    return {
        "recipient": recipient,
        "amount_minor": params.get("amount_minor"),
        "currency": params.get("currency"),
    }


def execute(operation: str, params: dict, context: TrustedContext) -> BackendResult:
    """分发到后端执行转账。

    本函数只转发；授权重查、幂等、余额复检全部在后端锁内完成。
    ``context`` 必须是 ``WriteContext``，由公共层构造——这里不做类型放宽。
    """
    if operation != "TRANSFER":
        raise ValueError("unsupported transfer operation")
    if not validate(operation, params):
        return {
            "operation": operation,
            "status": "REJECTED",
            "data": None,
            "error_code": "INVALID_AMOUNT",
        }

    from bankagent.banking.bank_backend import execute_transfer

    return execute_transfer(
        context=context,  # type: ignore[arg-type]
        contact_id=params["contact_id"],
        amount_minor=params["amount_minor"],
        currency=params["currency"],
    )


def _money(minor: Any) -> str | None:
    """整数分转「元.分」文本；拒绝走 float，避免 0.1+0.2 那类差错。"""
    if type(minor) is not int or minor < 0:
        return None
    return f"{minor // 100}.{minor % 100:02d}"


def _rejection_detail(code: str, detail: dict) -> str | None:
    """后端给了判断依据就把话说清楚；没给就返回 None，由兜底文案接手。

    只解释**能证实**的部分：余额不足时说清余额和本次金额，超限时说清上限，
    累计超标时把今天已转的也报出来。后端没带数据时一律退回原来的简单文案。
    """
    if code == "INSUFFICIENT_BALANCE":
        balance = _money(detail.get("balance_minor"))
        amount = _money(detail.get("amount_minor"))
        if balance and amount:
            return f"账户余额 {balance} 元，不足以支付这笔 {amount} 元，转账未执行。"
    elif code == "REAUTHORIZATION_REQUIRED":
        spent = _money(detail.get("daily_total_minor"))
        amount = _money(detail.get("amount_minor"))
        limit = _money(detail.get("limit_minor"))
        if spent and amount and limit:
            return (f"今天已经转出 {spent} 元，再转 {amount} 元会超过 {limit} 元的"
                    f"当日累计限额，需要重新进行强认证。")
    elif code == "TRANSFER_LIMIT_EXCEEDED":
        amount = _money(detail.get("amount_minor"))
        limit = _money(detail.get("limit_minor"))
        if amount and limit:
            return f"这笔 {amount} 元超过单笔上限 {limit} 元，转账未执行。"
    return None


def render(result: BackendResult) -> str:
    """只解释后端事实；失败或处理中不得显示成功。"""
    if result.get("operation") != "TRANSFER":
        return "转账未完成。"

    status = result.get("status")
    if status != "COMPLETED":
        code = result.get("error_code")
        detail = result.get("data")
        explained = _rejection_detail(code, detail if isinstance(detail, dict) else {})
        if explained is not None:
            return explained
        return {
            "AUTHORIZATION_REQUIRED": "这笔转账还没有完成确认，请先确认后再提交。",
            "AUTHORIZATION_INVALID": "确认已失效或不匹配，请重新发起转账。",
            "IDEMPOTENCY_CONFLICT": "同一请求的转账参数不一致，已拒绝以避免重复扣款。",
            "INSUFFICIENT_BALANCE": "账户余额不足，转账未执行。",
            "TRANSFER_LIMIT_EXCEEDED": "单笔金额超过上限，转账未执行。",
            "REAUTHORIZATION_REQUIRED": "当日累计金额较高，需要重新进行强认证。",
            "INVALID_AMOUNT": "转账金额无效，请重新输入。",
            "UNSUPPORTED_CURRENCY": "暂不支持该币种。",
            "CONTACT_NOT_ACCESSIBLE": "无法使用该收款人，请重新选择。",
            "RECIPIENT_ACCOUNT_INVALID": "收款账户未绑定、不可用或与付款账户相同，转账未执行。",
            "ACCOUNT_NOT_ACCESSIBLE": "无法访问当前账户。",
        }.get(result.get("error_code"), "转账未完成，请稍后重试。")

    data = result.get("data")
    if not isinstance(data, dict):
        return "转账结果暂不可用。"

    amount = data.get("amount_minor")
    remaining = data.get("remaining_balance_minor")
    recipient = data.get("recipient")
    if (type(amount) is not int or amount <= 0
            or type(remaining) is not int or remaining < 0
            or not isinstance(recipient, str) or not recipient
            or data.get("currency") != SUPPORTED_CURRENCY
            or result.get("error_code") is not None):
        return "转账结果暂不可用。"

    # 展示也不经过 float：整数分拆成元与分两部分。
    amount_text = f"{amount // 100}.{amount % 100:02d}"
    remaining_text = f"{remaining // 100}.{remaining % 100:02d}"
    return (
        f"已向 {recipient} 转账 {amount_text} 元，"
        f"剩余余额 {remaining_text} 元。"
    )
