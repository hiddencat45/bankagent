"""订阅代扣场景：查询协议与暂停代扣。

和卡片场景一样，本模块只声明意图、把候选协议名解析成受控
``subscription_id``、分发到后端；不改余额、不产生流水、不判定授权。

三个边界：

- ``subscription_id`` 只能来自受控后端查询（``find_subscriptions``），
  **绝不**由模型或 ``candidate_params`` 直接提供；
- 确认卡只展示「对哪条协议做什么」，不含 ``subscription_id``；执行对象由
  服务端绑定的挑战记录决定；
- 暂停是**银行侧不再代扣**，不是终止商户合同，也不退款。渲染时必须说清，
  否则用户会以为订阅已经取消干净了。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import re
from typing import Any, Callable

from bank_types import (BILLS_MAX_RANGE_DAYS, SUPPORTED_CURRENCY,
                        BackendResult, IntentSpec, TrustedContext)

SCENARIO = "subscription"

INTENTS: dict[str, IntentSpec] = {
    "QUERY_SUBSCRIPTIONS": {
        # 不用单字「订阅」：它是「暂停订阅」的子串，会让暂停指令同时命中
        # 查询，把明确指令变成一次歧义澄清。
        "keywords": ["我的订阅", "订阅列表", "有哪些订阅", "查订阅",
                     "订阅协议", "代扣协议", "自动续费"],
        "slots": {"period": r"(本月|上月|近\d+天)"},
        "required": [],  # 未指定期间时看本月，不猜测缺失的业务事实。
        "operation": "QUERY_SUBSCRIPTIONS",
        "effect": "READ",
        "risk": "GREEN",
    },
    "PAUSE_SUBSCRIPTION": {
        # 「暂停」「停掉」单独列出，否则「暂停演示影音会员」这种不带「订阅」
        # 二字的自然说法命中不了。刻意不收单字「取消」「停止」：它们太通用，
        # 会让「取消转账」同时命中转账场景。
        "keywords": ["暂停订阅", "取消订阅", "停止代扣", "暂停代扣", "取消代扣",
                     "停掉订阅", "暂停", "停掉"],
        "slots": {
            # 动词后才能安全抓协议名；中间和结尾的「订阅/代扣/续费」是可选的
            # 补充说法，否则「暂停订阅 影音会员」会把「订阅」抓进协议名。
            "name": r"(?:暂停|取消|停止|停掉)\s*(?:我的)?\s*(?:订阅|代扣|续费)?\s*(.+?)\s*(?:的)?\s*(?:订阅|代扣|续费)?\s*$",
        },
        "required": ["name"],
        "operation": "PAUSE_SUBSCRIPTION",
        "effect": "WRITE",
        # 写操作最低 YELLOW；暂停不涉及金额，没有需要升高的情形。
        "risk": "YELLOW",
    },
}

CLARIFY_LABELS = {
    # 用解析后的键而不是候选键：公共层只在「既没出现在候选里、也没落进
    # params」时才列进澄清。协议名给了但查不到（`name` 在候选里），只有
    # `subscription_id` 能满足这个条件，否则会退化成 FAILED。
    # 不放 `period`：否则暂停协议会被问「还需要确认：时间范围」。
    "subscription_id": "要暂停的代扣协议",
}

_STATUS_TEXT: dict[str, str] = {"ACTIVE": "生效中", "PAUSED": "已暂停"}
_TARGET_STATUS = "PAUSED"

_clock: Callable[[], datetime] = lambda: datetime.now(timezone(timedelta(hours=8)))


def configure_clock(*, clock: Callable[[], datetime]) -> None:
    """服务端启动注入与后端一致的时钟；不接收来自模型或前端的时间基准。"""
    if not callable(clock):
        raise TypeError("clock must be callable")
    global _clock
    _clock = clock


def _period_params(period: Any) -> dict[str, Any]:
    """候选 period → 服务端 start/end；非法候选返回不可通过 validate 的空范围。

    规则与账单一致：不支持的期间不能悄悄退回本月。
    """
    invalid = {"start": None, "end": None}
    if not isinstance(period, str):
        return invalid
    now = _clock()
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("subscription clock must be timezone aware")
    today = now.astimezone(timezone(timedelta(hours=8))).date()
    first = today.replace(day=1)
    period = period.strip()
    if period == "本月":
        end = (date(first.year + 1, 1, 1) if first.month == 12
               else first.replace(month=first.month + 1))
        return {"start": first, "end": end}
    if period == "上月":
        return {"start": (first - timedelta(days=1)).replace(day=1), "end": first}
    match = re.fullmatch(r"近([1-9]\d{0,2})天", period)
    if match and 1 <= int(match[1]) <= BILLS_MAX_RANGE_DAYS:
        end = today + timedelta(days=1)
        return {"start": end - timedelta(days=int(match[1])), "end": end}
    return invalid


def _subscription_id(name: Any, context: TrustedContext) -> str | None:
    """候选协议名 → 受控 ``subscription_id``。

    精确匹配 ``display_name``：零个匹配（查无此协议）与多个匹配都不绑定，
    由公共层转入澄清——绝不任选一条。
    """
    if not isinstance(name, str) or not name.strip():
        return None
    from bank_backend import find_subscriptions

    try:
        matches = find_subscriptions(context=context, name=name.strip())
    except PermissionError:
        # 归属失败是受控拒绝，交给公共边界；这里不伪装成「没有这条协议」。
        raise
    return matches[0]["subscription_id"] if len(matches) == 1 else None


def resolve(candidate_params: dict, context: TrustedContext) -> dict:
    """按候选槽位分流：期间类走查询，名称类走暂停。

    两个意图共用 ``resolve``，只能靠槽位键区分。空候选按查询处理（默认本月），
    其余混杂组合一律返回空参数，让 ``validate`` 拒绝而不是猜一个操作。
    """
    if not isinstance(candidate_params, dict):
        return {}
    keys = set(candidate_params)
    if not keys or keys == {"period"}:
        return _period_params(candidate_params.get("period", "本月"))
    if keys == {"name"}:
        subscription_id = _subscription_id(candidate_params["name"], context)
        return {"subscription_id": subscription_id} if subscription_id else {}
    return {}


def validate(operation: str, params: dict) -> bool:
    if not isinstance(params, dict):
        return False
    if operation == "QUERY_SUBSCRIPTIONS":
        return (set(params) == {"start", "end"}
                and type(params["start"]) is date and type(params["end"]) is date
                and 0 < (params["end"] - params["start"]).days <= BILLS_MAX_RANGE_DAYS)
    if operation == "PAUSE_SUBSCRIPTION":
        subscription_id = params.get("subscription_id")
        return (set(params) == {"subscription_id"}
                and isinstance(subscription_id, str) and bool(subscription_id))
    return False


def _subscription_row(subscription_id: str, context: TrustedContext) -> dict[str, Any] | None:
    """按 id 取当前账户下的协议投影；查不到返回 None。"""
    from bank_backend import query_subscriptions

    today = _clock().astimezone(timezone(timedelta(hours=8))).date()
    first = today.replace(day=1)
    end = (date(first.year + 1, 1, 1) if first.month == 12
           else first.replace(month=first.month + 1))
    result = query_subscriptions(context=context, start=first, end=end)
    if result["status"] != "COMPLETED":
        raise PermissionError(result.get("error_code") or "ACCOUNT_NOT_ACCESSIBLE")
    rows = (result.get("data") or {}).get("subscriptions") or []
    return next((row for row in rows
                 if row.get("subscription_id") == subscription_id), None)


def confirmation(*, operation: str, params: dict, candidate_params: dict,
                 context: TrustedContext) -> dict:
    """确认卡展示字段：协议名、当前状态、目标状态。**不含 subscription_id。**

    当前状态在生成确认卡时重新查一次，而不是复用 ``resolve`` 时的结果。
    """
    row = _subscription_row(params.get("subscription_id"), context)
    if row is None:
        raise ValueError("代扣协议绑定已失效，无法生成确认卡")
    return {
        "display_name": row["display_name"],
        "current_status": row["status"],
        "target_status": _TARGET_STATUS,
    }


def execute(operation: str, params: dict, context: TrustedContext) -> BackendResult:
    """分发到后端。授权重查、幂等、归属复检全部在后端锁内完成。"""
    if operation == "QUERY_SUBSCRIPTIONS":
        from bank_backend import query_subscriptions

        if not validate(operation, params):
            return {"operation": operation, "status": "REJECTED", "data": None,
                    "error_code": "INVALID_DATE_RANGE"}
        return query_subscriptions(context=context, start=params["start"],
                                   end=params["end"])
    if operation == "PAUSE_SUBSCRIPTION":
        from bank_backend import pause_subscription

        return pause_subscription(context=context,
                                  subscription_id=params["subscription_id"])
    raise ValueError("unsupported subscription operation")


def _money(amount_minor: int) -> str:
    return f"{amount_minor // 100}.{amount_minor % 100:02d}"


def render(result: BackendResult) -> str:
    """只解释后端事实；失败或处理中不得显示成功。"""
    operation = result.get("operation")
    if result.get("status") != "COMPLETED":
        return {
            "INVALID_DATE_RANGE": "请提供有效的时间范围，例如本月、上月或近7天。",
            "TOO_MANY_TRANSACTIONS": "该时间范围扣款笔数过多，请缩短查询范围。",
            "SUBSCRIPTION_NOT_ACCESSIBLE": "无法访问当前账户的代扣协议。",
            "ACCOUNT_NOT_ACCESSIBLE": "无法访问当前账户的代扣协议。",
        }.get(result.get("error_code"), "代扣操作尚未完成，请稍后重试。")

    data = result.get("data") or {}
    if operation == "QUERY_SUBSCRIPTIONS":
        rows = data.get("subscriptions") or []
        if not rows:
            return "当前账户下没有已登记的代扣协议。"
        parts = []
        for row in rows:
            text = (f"{row['display_name']}（{_STATUS_TEXT.get(row['status'], row['status'])}，"
                    f"{_money(row['amount_minor'])} 元/期")
            if row.get("paid_minor"):
                text += f"，本期已扣 {_money(row['paid_minor'])} 元"
            parts.append(text + "）")
        total = data.get("total_minor")
        text = "当前代扣协议：" + "、".join(parts) + "。"
        if isinstance(total, int) and total > 0:
            text += f"本期合计扣款 {_money(total)} 元。"
        return text

    if operation == "PAUSE_SUBSCRIPTION":
        name = data.get("display_name") or "该协议"
        if data.get("changed") is False:
            return f"{name} 已经是暂停状态，无需再次暂停。"
        # 说清边界：这是银行侧不再代扣，不等于商户合同终止或退款。
        return f"{name} 已暂停代扣，后续不会再自动扣款；商户侧合同需另行取消。"

    return "代扣操作尚未完成，请稍后重试。"
