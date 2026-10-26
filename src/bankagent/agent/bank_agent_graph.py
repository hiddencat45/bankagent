"""银行 Agent 的第一版 LangGraph 教学示例。

这份代码只用于说明 State、Node、条件边、Checkpoint 和 interrupt 的协作方式。
它使用规则函数模拟大模型，使用内存常量模拟银行后端，不应直接用于真实资金业务。
真实系统还需要独立的身份认证、数据库事务、幂等控制、审计和风控服务。
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


RiskLevel = Literal["GREEN", "YELLOW", "RED", "DENY"]


class BankAgentState(TypedDict, total=False):
    # 第一组是可信请求上下文。真实系统应由 FastAPI 根据服务端 Session 注入，
    # 不能从用户自然语言、前端可编辑字段或模型输出中取得 user_id 和 account_id。
    user_id: str
    account_id: str
    request_id: str
    message: str
    daily_transfer_total: float
    balance: float
    context_valid: bool

    # 第二组是语言理解产生的候选信息。这里的数据仍然不可信，
    # 必须经过实体解析、字段完整性检查和确定性计划校验后才能进入安全策略。
    intent: str
    recipient_name: str | None
    contact_id: str | None
    amount: float | None
    missing_fields: list[str]

    # 第三组是 Python 程序生成的计划与安全决策。
    # risk_level、operation_hash 和 authorized 都不能由大模型自行填写。
    plan: list[dict[str, Any]]
    plan_valid: bool
    risk_level: RiskLevel
    operation_hash: str
    challenge_id: str
    authorized: bool

    # 第四组是流程结果。result 保存结构化事实，response 只负责向用户解释事实。
    # 只有可信执行节点写入 COMPLETED 后，回复节点才可以宣称操作成功。
    status: str
    result: dict[str, Any]
    response: str


# 以下常量模拟服务端数据。联系人 ID、余额和工具白名单在真实系统中
# 应来自数据库或受控服务，而不是写入 Prompt 让模型自行决定。
CONTACTS = {
    "张伟": "contact-001",
    "李娜": "contact-002",
}
ALLOWED_OPERATIONS = {"GET_BALANCE", "PREPARE_TRANSFER"}
DEMO_BALANCE = 5000.0


def load_context(state: BankAgentState) -> dict[str, Any]:
    """加载可信上下文，并清理同一 thread 上一次运行留下的瞬态字段。

    输入中的 user_id 和 request_id 在教学示例中被视为 FastAPI 已验证的数据。
    如果缺少任何一个字段，本节点会把 context_valid 设为 False，后续条件边
    将直接进入拒绝回复，不再调用意图理解或业务执行节点。

    reset 很重要：LangGraph 会把新输入合并到同一 thread 的历史 State。
    如果不清空旧的 status、result 和 authorized，新请求暂停时可能错误展示
    上一笔请求的成功结果。节点只返回需要更新的字段，LangGraph 负责合并。
    """
    reset = {
        "status": "PROCESSING",
        "result": {},
        "response": "",
        "authorized": False,
        "plan": [],
        "plan_valid": False,
        "operation_hash": "",
        "challenge_id": "",
    }

    if not state.get("user_id") or not state.get("request_id"):
        return {
            **reset,
            "context_valid": False,
            "status": "REJECTED",
            "result": {"reason": "missing_trusted_context"},
        }

    return {
        **reset,
        "context_valid": True,
        "account_id": "account-001",
        "balance": DEMO_BALANCE,
        "daily_transfer_total": state.get("daily_transfer_total", 0.0),
    }


def route_context(state: BankAgentState) -> Literal["continue", "reject"]:
    """根据可信上下文校验结果选择路径，不在路由函数中修改 State。"""
    return "continue" if state.get("context_valid") else "reject"


def understand_intent(state: BankAgentState) -> dict[str, Any]:
    """用离线规则模拟大模型的结构化意图识别。

    真实实现可以替换为支持 structured output 的聊天模型，但输出仍然只能是
    候选意图和候选参数。本节点不查询余额、不批准操作，也不执行任何转账。
    为了让示例可以离线运行，这里只识别“查询余额”和“给某人转若干元”。
    """
    message = state["message"].strip()

    if "余额" in message:
        return {
            "intent": "BALANCE_QUERY",
            "recipient_name": None,
            "amount": None,
            "missing_fields": [],
        }

    if "转" in message:
        # 两个正则只承担演示中的槽位提取：第一个提取“给谁”，第二个提取“多少钱”。
        # 未匹配到关键字段时不猜测默认值，而是记录到 missing_fields 等待用户补充。
        recipient_match = re.search(r"给\s*(.+?)\s*转", message)
        amount_match = re.search(r"转\s*(\d+(?:\.\d+)?)\s*元?", message)
        recipient = recipient_match.group(1).strip() if recipient_match else None
        amount = float(amount_match.group(1)) if amount_match else None

        missing: list[str] = []
        if not recipient:
            missing.append("recipient")
        if amount is None:
            missing.append("amount")

        return {
            "intent": "TRANSFER",
            "recipient_name": recipient,
            "amount": amount,
            "missing_fields": missing,
        }

    return {
        "intent": "UNKNOWN",
        "recipient_name": None,
        "amount": None,
        "missing_fields": [],
    }


def resolve_entities(state: BankAgentState) -> dict[str, Any]:
    """把模型提取的联系人姓名解析为服务端联系人 ID。

    模型只能提供“张伟”这样的搜索词，不能直接构造 contact_id。真实系统应调用
    通讯录服务并处理重名、手机号尾号等歧义；本示例用 CONTACTS 字典模拟查询。
    找不到联系人时，将 known_recipient 加入缺失字段并转入澄清路径。
    """
    if state["intent"] != "TRANSFER":
        return {}

    recipient = state.get("recipient_name")
    missing = list(state.get("missing_fields", []))
    contact_id = CONTACTS.get(recipient or "")

    if recipient and contact_id is None:
        missing.append("known_recipient")

    return {
        "contact_id": contact_id,
        "missing_fields": missing,
    }


def route_information(
    state: BankAgentState,
) -> Literal["clarify", "create_plan"]:
    """根据信息是否完整选择“澄清”或“创建计划”。

    路由函数只返回路径标签，不修改 State，也不执行查询、扣款等副作用。
    这样节点职责和图的连边关系可以分别测试，避免把业务逻辑藏在路由函数中。
    """
    return "clarify" if state.get("missing_fields") else "create_plan"


def ask_clarification(state: BankAgentState) -> dict[str, Any]:
    """把内部缺失字段转换为用户能够理解的澄清提示。

    此节点结束当前运行，等待用户下一轮补充信息。生产系统可把缺失字段保存在
    Checkpoint 中；下一轮使用同一 thread_id 时，再合并用户补充的内容。
    """
    labels = {
        "recipient": "收款人",
        "known_recipient": "通讯录中的有效收款人",
        "amount": "金额",
    }
    fields = [labels.get(item, item) for item in state["missing_fields"]]
    return {
        "status": "NEEDS_CLARIFICATION",
        "response": f"还需要确认：{'、'.join(fields)}。",
    }


def create_plan(state: BankAgentState) -> dict[str, Any]:
    """根据候选意图创建一个最小的结构化计划。

    查询余额映射为 GET_BALANCE；转账只映射为 PREPARE_TRANSFER，明确表示模型
    只能提出和准备转账，不能直接调用 execute_transfer。未知意图故意映射为
    UNSUPPORTED，交给下一节点的白名单规则拒绝。
    """
    if state["intent"] == "BALANCE_QUERY":
        plan = [{"operation": "GET_BALANCE", "parameters": {}}]
    elif state["intent"] == "TRANSFER":
        plan = [
            {
                "operation": "PREPARE_TRANSFER",
                "parameters": {
                    "contact_id": state["contact_id"],
                    "amount": state["amount"],
                    "currency": "CNY",
                },
            }
        ]
    else:
        plan = [{"operation": "UNSUPPORTED", "parameters": {}}]

    return {"plan": plan}


def validate_plan(state: BankAgentState) -> dict[str, Any]:
    """使用确定性 Python 规则校验计划，而不是让模型自我批准。

    先检查计划只能包含一个白名单操作；转账计划还必须包含正数金额和已经由
    服务端解析出的 contact_id。plan_valid 只是“计划格式和基础参数有效”，
    不代表用户已经授权，也不代表余额和风控已经通过。
    """
    plan = state.get("plan", [])
    valid = len(plan) == 1 and plan[0].get("operation") in ALLOWED_OPERATIONS

    if valid and plan[0]["operation"] == "PREPARE_TRANSFER":
        amount = plan[0]["parameters"].get("amount")
        valid = (
            isinstance(amount, (int, float))
            and amount > 0
            and bool(plan[0]["parameters"].get("contact_id"))
        )

    return {"plan_valid": valid}


def route_plan(state: BankAgentState) -> Literal["security", "reject"]:
    """有效计划进入安全策略，无效计划进入明确拒绝节点。"""
    return "security" if state.get("plan_valid") else "reject"


def reject_plan(state: BankAgentState) -> dict[str, Any]:
    """记录计划无效或当前示例不支持该操作，供回复节点统一解释。"""
    return {
        "status": "REJECTED",
        "result": {"reason": "unsupported_or_invalid_plan"},
    }


def security_policy(state: BankAgentState) -> dict[str, Any]:
    """在模型之外确定风险等级，并为写操作创建绑定本次操作的挑战。

    GET_BALANCE 是绿色查询；转账按“当日累计加本次金额”分为黄色和红色；
    单笔超过教学阈值 10000 元时直接 DENY。真实系统的阈值应来自版本化策略配置。

    operation_hash 绑定用户、付款账户、联系人、金额、币种和 request_id。
    恢复 interrupt 时必须同时匹配 challenge_id 与 operation_hash，防止用户确认后
    参数被替换。这里使用 float 只是为了缩短示例；真实金额应使用 Decimal 或分。
    """
    operation = state["plan"][0]["operation"]

    if operation == "GET_BALANCE":
        return {"risk_level": "GREEN"}

    if operation != "PREPARE_TRANSFER":
        return {"risk_level": "DENY"}

    amount = float(state["plan"][0]["parameters"]["amount"])
    projected_total = state["daily_transfer_total"] + amount
    if amount > 10_000:
        return {"risk_level": "DENY"}
    risk_level: RiskLevel = "YELLOW" if projected_total <= 1000 else "RED"

    hash_payload = {
        "user_id": state["user_id"],
        "account_id": state["account_id"],
        "contact_id": state["contact_id"],
        "amount": amount,
        "currency": "CNY",
        "request_id": state["request_id"],
    }
    operation_hash = hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "risk_level": risk_level,
        "operation_hash": operation_hash,
        "challenge_id": f"challenge-{state['request_id']}",
    }


def route_security(
    state: BankAgentState,
) -> Literal["green", "yellow", "red", "deny"]:
    """把安全策略结果映射为图中的四条显式路径。"""
    return {
        "GREEN": "green",
        "YELLOW": "yellow",
        "RED": "red",
        "DENY": "deny",
    }[state["risk_level"]]


def execute_query(state: BankAgentState) -> dict[str, Any]:
    """执行绿色只读操作，并返回结构化查询结果。

    余额来自 load_context 注入的模拟服务端数据，而不是模型输出。此节点只读取，
    不创建确认挑战，也不修改账户状态。
    """
    return {
        "status": "COMPLETED",
        "result": {
            "operation": "GET_BALANCE",
            "balance": state["balance"],
            "currency": "CNY",
        },
    }


def interrupt_for_confirmation(state: BankAgentState) -> dict[str, Any]:
    """暂停黄色操作，等待用户在可信界面完成明确确认。

    interrupt() 会保存当前 State 和执行位置，并把可展示的挑战信息返回给调用方。
    使用同一个 thread_id 和 Command(resume=...) 恢复时，本函数会从头重新执行，
    此时 interrupt() 返回外部提交的 decision。因此 interrupt 之前不能发送短信、
    扣款或执行其他不可重复的副作用。

    本示例要求 approved、challenge_id 和 operation_hash 同时匹配。真实系统还应在
    恢复接口验证当前登录用户，并从服务端确认表读取不可伪造的授权记录。
    """
    decision = interrupt(
        {
            "kind": "CONFIRMATION",
            "challenge_id": state["challenge_id"],
            "operation_hash": state["operation_hash"],
            "recipient": state["recipient_name"],
            "amount": state["amount"],
        }
    )
    authorized = (
        isinstance(decision, dict)
        and decision.get("approved") is True
        and decision.get("challenge_id") == state["challenge_id"]
        and decision.get("operation_hash") == state["operation_hash"]
    )
    return {"authorized": authorized}


def interrupt_for_authentication(state: BankAgentState) -> dict[str, Any]:
    """暂停红色操作，等待独立强认证服务返回认证结果。

    中断信息只包含挑战 ID、操作哈希、可用认证方式和金额，不包含 OTP、密码或
    生物信息。恢复载荷必须是字典，并同时匹配挑战、操作哈希和演示认证令牌。
    固定令牌 demo-otp-ok 仅用于离线教学，不能出现在真实系统中。
    """
    authentication = interrupt(
        {
            "kind": "STRONG_AUTH",
            "challenge_id": state["challenge_id"],
            "operation_hash": state["operation_hash"],
            "methods": ["OTP", "FACE"],
            "amount": state["amount"],
        }
    )
    # 真实系统应在这里查询独立认证服务签发的短期凭证，而不是比较固定字符串。
    # OTP、支付密码和生物特征不得写入 State、Prompt、Checkpoint 或普通日志。
    authorized = (
        isinstance(authentication, dict)
        and authentication.get("challenge_id") == state["challenge_id"]
        and authentication.get("operation_hash") == state["operation_hash"]
        and authentication.get("auth_token") == "demo-otp-ok"
    )
    return {"authorized": authorized}


def route_authorization(
    state: BankAgentState,
) -> Literal["execute", "reject"]:
    """只有服务端验证后的 authorized=True 才能进入执行节点。"""
    return "execute" if state.get("authorized") else "reject"


def execute_operation(state: BankAgentState) -> dict[str, Any]:
    """模拟可信银行后端在执行前重新检查授权和余额。

    即使图已经走到执行节点，也不能只依赖此前的路由结果；执行边界必须再次检查
    authorized，并重新读取余额。真实实现还需要数据库事务、唯一幂等键、限额、
    账户状态和授权有效期复检。本示例只计算返回值，不会真正持久化扣款。
    """
    if not state.get("authorized"):
        return {
            "status": "REJECTED",
            "result": {"reason": "missing_authorization"},
        }

    amount = float(state["amount"])
    if amount > state["balance"]:
        return {
            "status": "FAILED",
            "result": {"reason": "insufficient_balance"},
        }

    return {
        "status": "COMPLETED",
        "result": {
            "operation": "TRANSFER",
            "recipient": state["recipient_name"],
            "amount": amount,
            "currency": "CNY",
            "remaining_balance": state["balance"] - amount,
        },
    }


def reject_operation(state: BankAgentState) -> dict[str, Any]:
    """统一处理策略拒绝、用户拒绝、挑战不匹配和认证失败。"""
    return {
        "status": "REJECTED",
        "result": {"reason": "denied_or_not_authorized"},
    }


def compose_response(state: BankAgentState) -> dict[str, Any]:
    """根据结构化执行结果生成面向用户的自然语言回复。

    回复节点不再调用工具，也不能自行改写 status。只有 result 明确来自查询或执行
    节点且 status=COMPLETED 时才表述成功，从而避免模型编造余额或交易结果。
    """
    status = state["status"]
    result = state.get("result", {})

    if status == "COMPLETED" and result.get("operation") == "GET_BALANCE":
        response = f"当前可用余额为 {result['balance']:.2f} CNY。"
    elif status == "COMPLETED" and result.get("operation") == "TRANSFER":
        response = (
            f"已向 {result['recipient']} 转账 {result['amount']:.2f} CNY，"
            f"剩余余额 {result['remaining_balance']:.2f} CNY。"
        )
    elif result.get("reason") == "missing_trusted_context":
        response = "缺少可信登录身份或请求编号。"
    elif result.get("reason") == "unsupported_or_invalid_plan":
        response = "当前示例不支持这个请求。"
    else:
        response = f"操作未完成，状态：{status}。"

    return {"response": response}


def build_graph():
    """注册全部节点和边，并编译第一版单 Agent 工作流。

    普通边表达固定顺序，条件边根据 State 选择路径。InMemorySaver 让黄色和红色
    节点可以暂停和恢复，但进程退出后数据会丢失；生产环境应替换为 PostgreSQL
    Checkpointer，同时继续把余额、授权和交易结果保存在独立业务数据库中。
    """
    builder = StateGraph(BankAgentState)

    # 第一部分：注册节点。字符串名称用于日志、可视化、Checkpoint 和条件边目标。

    builder.add_node("load_context", load_context)
    builder.add_node("understand_intent", understand_intent)
    builder.add_node("resolve_entities", resolve_entities)
    builder.add_node("ask_clarification", ask_clarification)
    builder.add_node("create_plan", create_plan)
    builder.add_node("validate_plan", validate_plan)
    builder.add_node("reject_plan", reject_plan)
    builder.add_node("security_policy", security_policy)
    builder.add_node("execute_query", execute_query)
    builder.add_node("interrupt_for_confirmation", interrupt_for_confirmation)
    builder.add_node("interrupt_for_authentication", interrupt_for_authentication)
    builder.add_node("execute_operation", execute_operation)
    builder.add_node("reject_operation", reject_operation)
    builder.add_node("compose_response", compose_response)

    # 第二部分：入口先校验可信上下文。校验失败直接组织拒绝回复，
    # 校验成功才允许模型理解用户输入。
    builder.add_edge(START, "load_context")
    builder.add_conditional_edges(
        "load_context",
        route_context,
        {
            "continue": "understand_intent",
            "reject": "compose_response",
        },
    )
    # 第三部分：模型只输出候选字段，随后由服务端解析联系人并检查信息完整性。
    builder.add_edge("understand_intent", "resolve_entities")
    builder.add_conditional_edges(
        "resolve_entities",
        route_information,
        {
            "clarify": "ask_clarification",
            "create_plan": "create_plan",
        },
    )
    builder.add_edge("ask_clarification", END)

    # 第四部分：先生成计划，再用白名单和确定性参数规则校验计划。
    builder.add_edge("create_plan", "validate_plan")
    builder.add_conditional_edges(
        "validate_plan",
        route_plan,
        {
            "security": "security_policy",
            "reject": "reject_plan",
        },
    )
    builder.add_edge("reject_plan", "compose_response")

    # 第五部分：安全策略把操作分成绿色、黄色、红色和拒绝四条路径。
    builder.add_conditional_edges(
        "security_policy",
        route_security,
        {
            "green": "execute_query",
            "yellow": "interrupt_for_confirmation",
            "red": "interrupt_for_authentication",
            "deny": "reject_operation",
        },
    )
    builder.add_edge("execute_query", "compose_response")

    # 第六部分：黄色和红色流程恢复后都要检查 authorized，
    # 验证失败进入统一拒绝节点，验证成功才进入模拟执行节点。
    builder.add_conditional_edges(
        "interrupt_for_confirmation",
        route_authorization,
        {
            "execute": "execute_operation",
            "reject": "reject_operation",
        },
    )
    builder.add_conditional_edges(
        "interrupt_for_authentication",
        route_authorization,
        {
            "execute": "execute_operation",
            "reject": "reject_operation",
        },
    )
    builder.add_edge("execute_operation", "compose_response")
    builder.add_edge("reject_operation", "compose_response")
    builder.add_edge("compose_response", END)

    # 编译阶段检查图结构，并启用内存 Checkpoint 以支持 interrupt 暂停和恢复。
    return builder.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    # 直接运行本文件时只演示绿色余额查询，因此不需要处理 interrupt 恢复。
    graph = build_graph()
    config = {"configurable": {"thread_id": "demo-balance"}}
    final_state = graph.invoke(
        {
            "user_id": "user-001",
            "message": "查询余额",
            "request_id": "req-demo",
            "daily_transfer_total": 0.0,
        },
        config,
    )
    print(final_state["response"])
