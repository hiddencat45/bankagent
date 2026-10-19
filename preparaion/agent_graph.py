"""主图接入：把场景注册器、安全层与后端串成可运行的 LangGraph 工作流。

这是**新模块**，按契约 §3.2「旧教学文件暂不改」保留 ``bank_agent_graph.py``
原样不动（它的 11 条测试继续跑）。区别：

| 项 | 旧教学图 | 本模块 |
|---|---|---|
| 状态 | 自己的旧 State | ``bank_types.BankAgentState`` |
| 计划 | ``plan: list`` | ``operation`` + ``params``（单操作） |
| 金额 | ``float`` 元 | 整数分 ``amount_minor`` |
| 场景 | 写死在节点里 | 由注册器发现与校验 |
| 授权 | 比对 ``resume`` 载荷里的固定口令 | **只读服务端记录** |
| 恢复令牌 | ``auth_token == "demo-otp-ok"`` | 不存在这个概念 |

## 三个必须守住的边界

1. **模型/候选参数只提供候选。** ``scenario``/``intent``/``candidate_params``
   全部是未受信任输入；``operation`` 与 ``params`` 由 Python 依据注册器声明
   生成，``params`` 里的目标 ID 只能来自受控后端查询。
2. **``interrupt()`` 的 resume 载荷不是授权凭证**（契约 §4.3）。恢复后的节点
   用服务端 ``ChallengeStore`` 查记录，**不读** ``decision``、**不读** ``otp``。
3. **状态映射不等于成功**（契约 §1.4）。后端 ``REJECTED``/``FAILED`` 必须
   如实映射成顶层 ``REJECTED``/``FAILED``，不能因为函数正常返回就标 `COMPLETED`。
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agent_security import ChallengeStore, compute_operation_hash
from bank_types import (
    CLARIFICATION_TIMEOUT_MINUTES,
    SERVER_ONLY_DATA_FIELDS,
    BankAgentState,
    BackendResult,
    TopLevelStatus,
    TrustedContext,
    WriteContext,
)
from scenarios import REGISTRY, ScenarioError, ScenarioRegistry

__all__ = [
    "build_graph",
    "BankAgentRuntime",
    "SG_TZ",
    "STATUS_MAP",
]

SG_TZ = timezone(timedelta(hours=8))

# 契约 §1.4：后端结果状态 → 图顶层状态。一一对应，不允许额外发明。
STATUS_MAP: dict[str, TopLevelStatus] = {
    "COMPLETED": "COMPLETED",
    "REJECTED": "REJECTED",
    "FAILED": "FAILED",
    "PENDING": "PENDING",
}

# 只读操作走直接执行；写操作必须经挑战。
_WRITE_EFFECT = "WRITE"

# 主图安全层自己产生的错误码与文案。这些不属于任何场景的业务错误，
# 因此不要求各场景的 render 处理——场景只解释自己后端返回的错误码。
_PUBLIC_ERROR_TEXT: dict[str, str] = {
    "MISSING_TRUSTED_CONTEXT": "缺少可信登录身份或请求编号，请重新登录后再试。",
    "INVALID_REQUEST": "请求内容不完整，请重新描述您要办理的业务。",
    "UNSUPPORTED_INTENT": "抱歉，我暂时只能办理余额查询、转账和账单查询。",
    "OPERATION_NOT_ALLOWED": "该操作不在允许范围内，已停止办理。",
    "POLICY_DENIED": "这笔操作不符合当前安全策略，已停止办理。",
    "RISK_EVALUATION_FAILED": "暂时无法完成风险评估，为安全起见未执行，请稍后重试。",
    "ACCOUNT_NOT_ACCESSIBLE": "无法访问当前账户，请确认登录状态后重试。",
    "INVALID_PARAMS": "您提供的信息有误，请重新确认后再试。",
    "USER_CANCELLED": "您已取消这笔操作，账户未发生任何变动。",
    "AUTHORIZATION_REQUIRED": "这笔操作尚未确认，账户未发生任何变动。",
    "INTERNAL": "系统处理异常，操作未执行，请稍后重试。",
}


class BankAgentRuntime:
    """图运行期依赖：注入而非全局，方便测试替换。

    不放进 State：这些是服务端设施，不是一次对话的业务字段。
    """

    def __init__(
        self,
        *,
        registry: ScenarioRegistry | None = None,
        challenges: ChallengeStore | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.registry = registry if registry is not None else REGISTRY
        self.clock = clock if clock is not None else (lambda: datetime.now(SG_TZ))
        self.challenges = challenges if challenges is not None else ChallengeStore(clock=self.clock)
        # 澄清续轮的期限元数据，按 (user_id, thread_id) 记，**不进 State**
        # （契约 §1.5：澄清期限保存在服务端待补任务元数据中）。
        self._clarify_deadlines: dict[tuple[str, str], datetime] = {}

    # -- 澄清期限 ---------------------------------------------------------

    def remember_clarification(self, user_id: str, thread_id: str) -> None:
        self._clarify_deadlines[(user_id, thread_id)] = self.clock() + timedelta(
            minutes=CLARIFICATION_TIMEOUT_MINUTES
        )

    def clarification_open(self, user_id: str, thread_id: str) -> bool:
        deadline = self._clarify_deadlines.get((user_id, thread_id))
        return deadline is not None and deadline > self.clock()

    def forget_clarification(self, user_id: str, thread_id: str) -> None:
        self._clarify_deadlines.pop((user_id, thread_id), None)


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------


def _cleared() -> dict[str, Any]:
    """新一轮要清空的字段（契约 §1.5）。

    只清业务字段，不动 ``user_id``/``account_id``/``request_id``/``message``：
    那四个由服务端与 API 层写入。
    """
    return {
        "scenario": "",
        "intent": "",
        "candidate_params": {},
        "missing_fields": [],
        "operation": "",
        "params": {},
        "risk_level": "GREEN",
        "operation_hash": "",
        "challenge_id": "",
        "authorized": False,
        "result": {},
        "response": "",
    }


def _rejected(operation: str, error_code: str) -> BackendResult:
    return {"operation": operation, "status": "REJECTED", "data": None,
            "error_code": error_code}


def _safe_projection(params: dict[str, Any]) -> dict[str, Any]:
    """把参数投影成可展示的形式，剔除服务端专用字段（契约 §1.3）。"""
    return {k: v for k, v in params.items() if k not in SERVER_ONLY_DATA_FIELDS}


def _thread_id(config: RunnableConfig | None) -> str:
    """从 Checkpoint 配置取会话键；缺失时用空串（单会话测试可用）。"""
    if not isinstance(config, dict):
        return ""
    configurable = config.get("configurable") or {}
    value = configurable.get("thread_id")
    return value if isinstance(value, str) else ""


def _extract_slots(message: str, slots: dict[str, str]) -> dict[str, Any]:
    """按场景声明里给的候选正则提取槽位。

    只做提取，**不做校验**：提取结果一律进 ``candidate_params``，
    由 ``resolve`` 与 ``validate`` 决定是否可用。
    """
    found: dict[str, Any] = {}
    for name, pattern in slots.items():
        match = re.search(pattern, message)
        if match:
            # 有分组取第一组，否则取整个匹配
            found[name] = match.group(1) if match.groups() else match.group(0)
    return found


# ---------------------------------------------------------------------------
# 节点
# ---------------------------------------------------------------------------


def build_graph(runtime: BankAgentRuntime | None = None, *, checkpointer=None):
    """构造并编译主图。

    节点顺序：校验上下文 → 识别意图 → 解析实体 → （澄清 | 策略）→
    （只读执行 | 确认/认证中断）→ 执行写操作 → 组织回复。
    """
    rt = runtime if runtime is not None else BankAgentRuntime()
    registry = rt.registry

    # -- 1. 可信上下文 ---------------------------------------------------

    def load_context(state: BankAgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
        """校验服务端注入的上下文，并清理上一轮的业务字段。

        缺少 ``user_id``/``account_id``/``request_id`` 直接拒绝——这三个只能
        由服务端注入，任何"请求里带了就算"的做法都会破掉归属校验。
        """
        user_id = state.get("user_id")
        account_id = state.get("account_id")
        request_id = state.get("request_id")
        message = state.get("message")

        if not all(isinstance(v, str) and v for v in (user_id, account_id, request_id)):
            return {
                **_cleared(),
                "status": "REJECTED",
                "result": _rejected("", "MISSING_TRUSTED_CONTEXT"),
                "response": "缺少可信登录身份或请求编号，请重新登录后再试。",
            }
        if not isinstance(message, str) or not message.strip():
            return {
                **_cleared(),
                "status": "REJECTED",
                "result": _rejected("", "INVALID_REQUEST"),
                "response": "请说明您要办理的业务。",
            }

        return {**_cleared(), "status": "PROCESSING"}

    def route_context(state: BankAgentState) -> Literal["continue", "end"]:
        return "continue" if state.get("status") == "PROCESSING" else "end"

    # -- 2. 意图识别 -----------------------------------------------------

    def understand_intent(state: BankAgentState) -> dict[str, Any]:
        """用注册器的关键词收集**全部**候选，再决定意图。

        不按模块名顺序取第一个：多个不同操作同时命中时要求用户明确，
        猜错会直接把用户带到错误的业务流程。
        """
        message = state["message"]
        hits = registry.match_intents(message)
        if not hits:
            return {
                "status": "REJECTED",
                "result": _rejected("", "UNSUPPORTED_INTENT"),
                "response": "抱歉，我暂时只能办理余额查询、转账和账单查询。",
            }

        # 命中多个不同操作 → 不能猜。
        operations = set()
        for scenario_name, intent_name, _ in hits:
            spec = registry.get(scenario_name)
            operations.add(spec.intents[intent_name]["operation"])
        if len(operations) > 1:
            labels = "、".join(sorted(
                registry.get(s).intents[i]["operation"]
                for s, i, _ in hits
            ))
            return {
                "status": "NEEDS_CLARIFICATION",
                "missing_fields": [],
                "response": f"您的需求可以对应多件事（{labels}），请明确要先办哪一件？",
            }

        scenario_name, intent_name, _ = hits[0]
        spec = registry.get(scenario_name)
        intent_spec = spec.intents[intent_name]

        candidates = _extract_slots(message, intent_spec["slots"])
        return {
            "scenario": scenario_name,
            "intent": intent_name,
            "candidate_params": candidates,
            "missing_fields": [],
        }

    def route_intent(state: BankAgentState) -> Literal["clarify", "end", "resolve"]:
        status = state.get("status")
        if status in {"REJECTED", "NEEDS_CLARIFICATION"}:
            return "clarify" if status == "NEEDS_CLARIFICATION" else "end"
        return "resolve"

    # -- 3. 实体解析 -----------------------------------------------------

    def resolve_entities(state: BankAgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
        """调用场景 ``resolve`` 把候选槽位变成已校验参数。

        受控拒绝由注册器统一转码（B 的 ``find_contacts`` 抛 ``PermissionError``
        时也在这一层变成 ``ACCOUNT_NOT_ACCESSIBLE``）。
        """
        scenario_name = state["scenario"]
        spec = registry.get(scenario_name)
        intent_spec = spec.intents[state["intent"]]
        operation = intent_spec["operation"]

        context = TrustedContext(
            state["user_id"], state["account_id"], state["request_id"]
        )

        try:
            resolved = registry.resolve_params(
                scenario_name, state.get("candidate_params", {}), context
            )
        except ScenarioError as exc:
            code = str(exc) or "INVALID_PARAMS"
            return {
                "operation": operation,
                "params": {},
                "status": "REJECTED",
                "result": _rejected(operation, code),
            }

        # 缺失槽位：只按「候选里缺了必填槽位」判定。
        #
        # 这里**不**把 ``validate`` 失败一律当成缺信息。原因：``validate`` 同时
        # 检查形状与取值范围，超单笔上限之类的失败是**策略问题**，应该交给
        # 风险层判 DENY，而不是问用户"还需要确认：params"——那既看不懂，
        # 也会把用户挡在拒绝之前。
        candidates = state.get("candidate_params", {})
        missing = [slot for slot in intent_spec["required"] if slot not in candidates]

        # 再补一层：必填槽位给了值、但服务端解析不出对应实体（查无此人/重名）。
        #
        # 判据用 ``clarify_labels`` 的键：那些是「用户可补充的实体标识」。
        # 一个键既没出现在候选里、也没落进 params，才说明实体没解析出来。
        # 注意不能拿 ``required`` 里的槽位名去比对 params——``recipient_name``
        # 与 ``amount`` 会被转换成 ``contact_id`` 与 ``amount_minor``，
        # 它们永远不会是 params 的键，那样判会误报"缺信息"。
        if not missing and spec.validate is not None and not spec.validate(operation, resolved):
            missing = [
                key for key in spec.clarify_labels
                if key not in candidates and key not in resolved
            ]

        if missing:
            if config is not None:
                rt.remember_clarification(state["user_id"], _thread_id(config))
            labels = [spec.clarify_labels.get(slot, slot) for slot in missing]
            return {
                "operation": operation,
                "params": resolved,
                "missing_fields": missing,
                "status": "NEEDS_CLARIFICATION",
                "response": f"还需要确认：{'、'.join(labels)}。",
            }

        return {"operation": operation, "params": resolved, "missing_fields": []}

    def route_resolution(state: BankAgentState) -> Literal["clarify", "security", "end"]:
        status = state.get("status")
        if status == "NEEDS_CLARIFICATION":
            return "clarify"
        if status == "REJECTED":
            return "end"
        return "security"

    # -- 4. 安全策略 -----------------------------------------------------

    def security_policy(state: BankAgentState) -> dict[str, Any]:
        """确定风险等级与操作哈希。

        风险由注册器计算（静态声明 + 场景钩子，只能升高）。钩子抛错时按
        **失败关闭**处理：拿不到可信数据就不放行。
        """
        scenario_name = state["scenario"]
        operation = state["operation"]
        params = state.get("params", {})

        # 操作必须属于当前场景且在白名单内。
        try:
            registry.check_operation(scenario_name, operation)
        except ScenarioError:
            return {
                "risk_level": "DENY",
                "result": _rejected(operation, "OPERATION_NOT_ALLOWED"),
                "status": "REJECTED",
            }

        context = TrustedContext(
            state["user_id"], state["account_id"], state["request_id"]
        )

        try:
            risk_level = registry.evaluate_risk(scenario_name, operation, params, context)
        except (ScenarioError, ValueError):
            # 失败关闭：算不出风险就不执行。
            return {
                "risk_level": "DENY",
                "result": _rejected(operation, "RISK_EVALUATION_FAILED"),
                "status": "FAILED",
            }

        if risk_level == "DENY":
            return {
                "risk_level": "DENY",
                "result": _rejected(operation, "POLICY_DENIED"),
                "status": "REJECTED",
            }

        operation_hash = compute_operation_hash(context, operation, params)
        return {"risk_level": risk_level, "operation_hash": operation_hash}

    def route_security(
        state: BankAgentState,
    ) -> Literal["green", "yellow", "red", "deny"]:
        if state.get("status") in {"REJECTED", "FAILED"}:
            return "deny"
        return {
            "GREEN": "green",
            "YELLOW": "yellow",
            "RED": "red",
            "DENY": "deny",
        }[state["risk_level"]]

    # -- 5. 只读执行 -----------------------------------------------------

    def execute_query(state: BankAgentState) -> dict[str, Any]:
        """绿色只读操作直接执行，不需要挑战。"""
        return _run_scenario(state, write=False)

    # -- 6. 中断：确认与强认证 -------------------------------------------

    def _interrupt_and_verify(state: BankAgentState, kind: str) -> dict[str, Any]:
        """暂停并等待，然后**只读服务端记录**决定是否授权。

        关键：``interrupt()`` 返回的载荷可能被客户端伪造，因此这里只把它
        当作"有结果回来了"的信号，真正的授权事实来自 ``ChallengeStore``。
        目标 ID 与金额来自已绑定的 ``params``，操作哈希在中断前算好。
        """
        scenario_name = state["scenario"]
        operation = state["operation"]
        params = state.get("params", {})
        context = TrustedContext(
            state["user_id"], state["account_id"], state["request_id"]
        )
        operation_hash = state["operation_hash"]
        risk_level = state["risk_level"]

        # 幂等登记：恢复时节点会重跑，不能生成两个挑战（契约 §4.3）。
        record = rt.challenges.register(
            context=context,
            operation=operation,
            params=params,
            operation_hash=operation_hash,
            risk_level=risk_level,
        )
        challenge_id = record["challenge_id"]

        interrupt({
            "kind": kind,
            "challenge_id": challenge_id,
            "operation_hash": operation_hash,
            "operation": operation,
            "risk_level": risk_level,
            # 只展示安全投影，避免服务端专用字段进入卡片。
            "params": _safe_projection(params),
        })

        # —— 以下恢复后执行；授权只认服务端记录 ——
        settled = rt.challenges.lookup(challenge_id)
        authorized = (
            isinstance(settled, dict)
            and settled.get("decision") == "APPROVED"
            and settled.get("operation_hash") == operation_hash
            and settled.get("challenge_id") == challenge_id
        )

        if not authorized:
            return {
                "challenge_id": challenge_id,
                "authorized": False,
                "status": "REJECTED",
                "result": _rejected(operation, "USER_CANCELLED"),
            }

        # 已批准：登记授权引用与幂等键，供执行节点构造 WriteContext。
        return {
            "challenge_id": challenge_id,
            "authorized": True,
            "params": {
                **params,
                # 这两个是服务端设施，只在本进程内传给后端，不来自候选参数。
                "_authorization_ref": challenge_id,
                "_idempotency_key": settled["idempotency_key"],
            },
        }

    def interrupt_for_confirmation(state: BankAgentState) -> dict[str, Any]:
        return _interrupt_and_verify(state, "CONFIRMATION")

    def interrupt_for_authentication(state: BankAgentState) -> dict[str, Any]:
        return _interrupt_and_verify(state, "STRONG_AUTH")

    def route_authorization(state: BankAgentState) -> Literal["execute", "reject"]:
        return "execute" if state.get("authorized") else "reject"

    # -- 7. 写操作执行 ---------------------------------------------------

    def execute_operation(state: BankAgentState) -> dict[str, Any]:
        """恢复后执行写操作；授权已在中断节点核验过。"""
        if not state.get("authorized"):
            return {
                "status": "REJECTED",
                "result": _rejected(state["operation"], "AUTHORIZATION_REQUIRED"),
            }
        return _run_scenario(state, write=True)

    # -- 共用：调用场景执行 ----------------------------------------------

    def _run_scenario(state: BankAgentState, *, write: bool) -> dict[str, Any]:
        scenario_name = state["scenario"]
        operation = state["operation"]
        raw_params = dict(state.get("params", {}))
        auth_ref = raw_params.pop("_authorization_ref", "")
        idem_key = raw_params.pop("_idempotency_key", "")

        if write:
            context: Any = WriteContext(
                state["user_id"], state["account_id"], state["request_id"],
                authorization_ref=auth_ref, idempotency_key=idem_key,
            )
        else:
            context = TrustedContext(
                state["user_id"], state["account_id"], state["request_id"]
            )

        try:
            result = registry.execute(scenario_name, operation, raw_params, context)
        except ScenarioError:
            return {
                "status": "FAILED",
                "result": _rejected(operation, "INTERNAL"),
            }

        # 契约 §1.4：后端状态如实映射，不能因为返回了就标 COMPLETED。
        return {"status": STATUS_MAP.get(result["status"], "FAILED"), "result": result}

    # -- 8. 澄清与拒绝 ---------------------------------------------------

    def ask_clarification(state: BankAgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
        if config is not None:
            rt.remember_clarification(state["user_id"], _thread_id(config))
        return {"status": "NEEDS_CLARIFICATION"}

    def reject_operation(state: BankAgentState) -> dict[str, Any]:
        """统一拒绝出口：策略拒绝、用户取消、授权失败都走这里。

        **保留已有的 FAILED**：风险评估失败、内部异常属于系统故障，
        不能伪装成"业务拒绝"。两者对用户和监控的含义完全不同。
        """
        current = state.get("status")
        if current in {"REJECTED", "FAILED"}:
            return {"status": current}
        return {"status": "REJECTED"}

    # -- 9. 组织回复 -----------------------------------------------------

    def compose_response(state: BankAgentState) -> dict[str, Any]:
        """只依据结构化结果组织回复，失败或处理中不得表述成功。

        已有 ``response``（例如上下文缺失、意图不明）时保留，不覆盖成
        "操作未完成"这类模糊措辞。

        **公共层的拒绝原因由这里统一解释**：``USER_CANCELLED``、
        ``POLICY_DENIED``、``OPERATION_NOT_ALLOWED`` 等是主图安全层的产出，
        不是场景的业务错误码，因此不让每个场景各写一份文案——场景只解释
        自己后端返回的错误码。
        """
        if state.get("response"):
            return {}

        scenario_name = state.get("scenario")
        result = state.get("result") or {}
        status = state.get("status")
        error_code = result.get("error_code")

        # 先处理主图自己的错误码，避免落到场景的通用兜底文案。
        public_text = _PUBLIC_ERROR_TEXT.get(error_code)
        if public_text is not None:
            return {"response": public_text}

        if scenario_name and result.get("operation"):
            try:
                text = registry.render(scenario_name, result)
            except (ScenarioError, KeyError):
                text = "操作未完成，请稍后重试。"
            return {"response": text}

        if status == "REJECTED":
            return {"response": "该请求未获准办理。"}
        return {"response": f"操作未完成，状态：{status}。"}

    # -- 图组装 ----------------------------------------------------------

    builder = StateGraph(BankAgentState)

    builder.add_node("load_context", load_context)
    builder.add_node("understand_intent", understand_intent)
    builder.add_node("resolve_entities", resolve_entities)
    builder.add_node("ask_clarification", ask_clarification)
    builder.add_node("security_policy", security_policy)
    builder.add_node("execute_query", execute_query)
    builder.add_node("interrupt_for_confirmation", interrupt_for_confirmation)
    builder.add_node("interrupt_for_authentication", interrupt_for_authentication)
    builder.add_node("execute_operation", execute_operation)
    builder.add_node("reject_operation", reject_operation)
    builder.add_node("compose_response", compose_response)

    builder.add_edge(START, "load_context")
    builder.add_conditional_edges(
        "load_context", route_context,
        {"continue": "understand_intent", "end": "compose_response"},
    )
    builder.add_conditional_edges(
        "understand_intent", route_intent,
        {"resolve": "resolve_entities", "clarify": "ask_clarification",
         "end": "compose_response"},
    )
    builder.add_conditional_edges(
        "resolve_entities", route_resolution,
        {"clarify": "ask_clarification", "security": "security_policy",
         "end": "compose_response"},
    )
    builder.add_edge("ask_clarification", END)

    builder.add_conditional_edges(
        "security_policy", route_security,
        {"green": "execute_query", "yellow": "interrupt_for_confirmation",
         "red": "interrupt_for_authentication", "deny": "reject_operation"},
    )
    builder.add_edge("execute_query", "compose_response")

    builder.add_conditional_edges(
        "interrupt_for_confirmation", route_authorization,
        {"execute": "execute_operation", "reject": "reject_operation"},
    )
    builder.add_conditional_edges(
        "interrupt_for_authentication", route_authorization,
        {"execute": "execute_operation", "reject": "reject_operation"},
    )
    builder.add_edge("execute_operation", "compose_response")
    builder.add_edge("reject_operation", "compose_response")
    builder.add_edge("compose_response", END)

    # 中断/恢复必须有 checkpointer；不传时用内存实现，方便单测与演示。
    if checkpointer is None:
        from langgraph.checkpoint.memory import InMemorySaver
        checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)
