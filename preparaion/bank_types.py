"""公共类型、枚举与常量：银行 Agent 的共享契约层。

本模块是**叶子模块**（leaf module），按《阶段0-接口草案》§5.1 与
《场景扩展与分工》§1 的约定：

- 只依赖 Python 标准库，**不导入**图模块、后端、``scenarios``、API 或 LangGraph；
- 只放声明与常量，**不放**业务执行、存储、初始化或哈希算法；
- 图与后端都从这里导入同一份类型，**不各复制一份**。

这样做的原因：``scenarios/*.execute()`` 必须导入后端，如果后端再反向导入图
就会形成循环导入。把共享声明放在无依赖的叶子上，两边都能安全引用。

约定来源（已合并进 main 的契约文档）：

- 金额一律用**整数分**，字段名带 ``_minor`` 后缀，禁止 ``float``；
- 时间范围左闭右开 ``[start, end)``，时区 ``Asia/Singapore``；
- 可信上下文只由服务端注入，模型与前端一律不可写。

本文件只做声明，不改变任何现有行为；旧教学文件 ``bank_agent_graph.py``
保留自己的旧版 State，按契约 §3.2「旧教学文件暂不改」，另行迁移。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict

__all__ = [
    # 类型别名
    "TopLevelStatus",
    "BackendStatus",
    "RiskLevel",
    "Effect",
    # TypedDict / dataclass
    "BankAgentState",
    "IntentSpec",
    "BackendResult",
    "TrustedContext",
    "WriteContext",
    "CardStatus",
    "SubscriptionStatus",
    "CardSummary",
    "CardsData",
    "CardChangeData",
    "SubscriptionRecord",
    "SubscriptionPayment",
    "SubscriptionSummary",
    "SubscriptionsData",
    "SubscriptionChangeData",
    "StateChangeConfirmation",
    # 常量
    "YELLOW_DAILY_LIMIT_MINOR",
    "TRANSFER_SINGLE_LIMIT_MINOR",
    "MAX_BILL_TRANSACTIONS",
    "CLARIFICATION_TIMEOUT_MINUTES",
    "CHALLENGE_TIMEOUT_MINUTES",
    "BILLS_MAX_RANGE_DAYS",
    "SUPPORTED_CURRENCY",
    "UNTRUSTED_STATE_FIELDS",
    "SERVER_ONLY_DATA_FIELDS",
]


# ---------------------------------------------------------------------------
# 类型别名
# ---------------------------------------------------------------------------

# 图顶层状态：由公共调度器设置，与后端 result["status"] 是两套取值，不能混用。
# 映射规则见契约 §1.4：后端 status 直接映射到同名顶层 status，
# 后端抛异常由公共边界转成 FAILED。
TopLevelStatus = Literal[
    "PROCESSING",
    "NEEDS_CLARIFICATION",
    "AWAITING_CONFIRMATION",
    "AWAITING_AUTHENTICATION",
    "COMPLETED",
    "REJECTED",
    "FAILED",
    "PENDING",
]

# 后端结果状态：由 B 的后端返回，写在 BackendResult["status"]。
# PENDING 本阶段不返回，仅保留取值。
BackendStatus = Literal["COMPLETED", "REJECTED", "FAILED", "PENDING"]

# 风险等级。READ 才能是 GREEN；WRITE 至少 YELLOW；DENY 表示策略直接拒绝。
# 场景钩子只能升高等级，不得降低，见契约 §2.2。
RiskLevel = Literal["GREEN", "YELLOW", "RED", "DENY"]

# 操作效果：只读还是写入。
Effect = Literal["READ", "WRITE"]


# ---------------------------------------------------------------------------
# 公共状态
# ---------------------------------------------------------------------------


class BankAgentState(TypedDict, total=False):
    """图运行期状态。

    ``total=False`` 表示所有键都是可选的：不同节点只写入自己负责的字段，
    LangGraph 负责合并。

    注意 ``thread_id`` **不在这里**——它是 Checkpoint 的会话键，只放在
    ``config["configurable"]``，避免出现两个来源。
    """

    # ── 可信上下文：服务端注入，模型与前端一律不可写 ──
    user_id: str
    account_id: str
    request_id: str

    # ── 用户输入 ──
    message: str

    # ── 候选理解：未受信任，不得直接成为执行参数 ──
    scenario: str
    intent: str
    candidate_params: dict[str, Any]
    missing_fields: list[str]

    # ── 已校验操作：实体已解析，参数已规范化 ──
    operation: str
    params: dict[str, Any]

    # ── 安全与结果：只由公共安全层与后端生成 ──
    risk_level: RiskLevel
    operation_hash: str
    challenge_id: str
    authorized: bool
    result: dict[str, Any]
    status: TopLevelStatus

    # ── 输出 ──
    response: str


class IntentSpec(TypedDict):
    """场景内单个意图的声明。"""

    keywords: list[str]   # 离线规则模式的匹配词
    slots: dict[str, str]  # 槽位名 → 提取用正则
    required: list[str]    # 缺失则澄清
    operation: str         # 会汇总进 ALLOWED_OPERATIONS
    effect: Effect
    risk: RiskLevel        # 静态最低风险


class BackendResult(TypedDict):
    """后端统一结果。

    - ``COMPLETED``：``data`` 是该操作的成功结构，``error_code`` 为 ``None``；
    - ``REJECTED`` / ``FAILED``：``data`` 为 ``None``，``error_code`` 必填；
    - ``PENDING``：本阶段三个操作不返回，仅保留取值。

    返回值必须可 JSON 序列化：日期用 ISO 字符串，金额用整数分。
    """

    operation: str
    status: BackendStatus
    data: dict[str, Any] | None
    error_code: str | None


# ---------------------------------------------------------------------------
# 可信上下文
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrustedContext:
    """只读操作的上下文，由服务端根据已认证会话构造。

    ``frozen=True`` 防止下游代码顺手改写身份字段——一旦被改写，
    归属校验就失去了意义。
    """

    user_id: str
    account_id: str
    request_id: str


@dataclass(frozen=True)
class WriteContext(TrustedContext):
    """写操作的上下文。

    ``authorization_ref`` 指向服务端授权记录，**本身不证明已授权**：
    后端必须按契约 §3.4 用 ``lookup_authorization`` 重查记录，确认
    decision、有效期、参数绑定与认证强度。

    ``idempotency_key`` 由服务端按本次逻辑写操作生成，首次执行与
    HTTP 重试复用同一个键，不能每次恢复随机生成。

    凭证（OTP、密码、生物特征）**不得**进入本类型。
    """

    authorization_ref: str
    idempotency_key: str


# ---------------------------------------------------------------------------
# 卡片与订阅的最小数据契约；不代表对应运行能力已经启用
# ---------------------------------------------------------------------------

CardStatus = Literal["ACTIVE", "FROZEN"]
SubscriptionStatus = Literal["ACTIVE", "PAUSED"]


class CardSummary(TypedDict):
    """后端返回的模拟卡；card_id 只由服务端解析，不作为模型候选。"""

    card_id: str
    display_name: str
    status: CardStatus


class CardsData(TypedDict):
    cards: list[CardSummary]


class CardChangeData(CardSummary):
    previous_status: CardStatus
    changed: bool


class SubscriptionRecord(TypedDict):
    """已登记的月度代扣协议；金额是每期约定额，不是历史消费合计。"""

    subscription_id: str
    display_name: str
    status: SubscriptionStatus
    amount_minor: int
    currency: str
    next_payment_date: str | None  # ISO 日期；暂停后为 None，不承诺商户侧取消


class SubscriptionPayment(TypedDict):
    transaction_id: str
    occurred_at: str
    amount_minor: int


class SubscriptionSummary(SubscriptionRecord):
    paid_minor: int
    payments: list[SubscriptionPayment]  # 指定期间的实际流水，笔数取 len(payments)


class SubscriptionsData(TypedDict):
    start: str
    end: str
    currency: str
    total_minor: int  # 各协议 paid_minor 之和，不是下一期预计额
    subscriptions: list[SubscriptionSummary]


class SubscriptionChangeData(SubscriptionRecord):
    previous_status: SubscriptionStatus
    changed: bool


class StateChangeConfirmation(TypedDict):
    """新增状态操作的 confirm payload；原 TRANSFER 卡保持原格式。

    服务端从已绑定操作及受控查询生成；不含实体 ID，不接受前端修改。
    current_status 是生成卡片时的状态，target_status 由 operation 唯一确定。
    display_name 不保证唯一；同名对象的选择与可区分展示须先完成接口对齐，
    不能仅凭展示名确定执行对象。
    """

    operation: Literal["FREEZE_CARD", "UNFREEZE_CARD", "PAUSE_SUBSCRIPTION"]
    display_name: str
    current_status: CardStatus | SubscriptionStatus
    target_status: CardStatus | SubscriptionStatus
    risk_level: Literal["YELLOW", "RED"]
    challenge_id: str
    operation_hash: str
    expires_at: str


# ---------------------------------------------------------------------------
# 公共常量
# ---------------------------------------------------------------------------
# 阈值只定义在这一处：A 算初始风险、B 在锁内复查，都必须引用同一常量，
# 否则两边各写一个数会导致风控漂移（契约 §3.4）。

# 当日累计转出（含本笔）不超过此值 → YELLOW，超过 → RED。
# 100000 分 = 1000.00 元，与教学代码 projected_total <= 1000 元等价。
YELLOW_DAILY_LIMIT_MINOR = 100_000

# 单笔转账上限，超过即 DENY。
# 1000000 分 = 10000.00 元，与教学代码 amount > 10_000 元等价。
TRANSFER_SINGLE_LIMIT_MINOR = 1_000_000

# 账单查询单次最多返回的交易条数。超限返回 TOO_MANY_TRANSACTIONS，
# 要求用户缩短范围；**不静默截断**统计、明细或异常证据。
MAX_BILL_TRANSACTIONS = 100

# 澄清续轮的期限（分钟）。超时后按新请求处理，不复用旧槽位与旧授权。
CLARIFICATION_TIMEOUT_MINUTES = 30

# 确认/强认证挑战的有效期（分钟）。
CHALLENGE_TIMEOUT_MINUTES = 5

# 账单查询允许的最大日期跨度（天），左闭右开。
BILLS_MAX_RANGE_DAYS = 366

# 本阶段只支持人民币。
SUPPORTED_CURRENCY = "CNY"


# ---------------------------------------------------------------------------
# 不可写字段清单
# ---------------------------------------------------------------------------
# 供 API 层与公共安全层做拒绝校验，避免各处各写一份名单（契约 §1.3）。

# 这些字段只由服务端生成，模型与 API 请求一律不可写；收到即拒绝，
# 不做「忽略后继续」——静默忽略会掩盖前端 bug。
UNTRUSTED_STATE_FIELDS: frozenset[str] = frozenset(
    {
        "user_id",
        "account_id",
        "request_id",
        "contact_id",
        "card_id",
        "subscription_id",
        "product_code",
        "risk_level",
        "operation_hash",
        "challenge_id",
        "authorized",
        "balance",
        "result",
        "idempotency_key",
        "authorization_ref",
        "daily_transfer_total_minor",
    }
)

# 只供服务端风控与后端内部使用，不得进入 Prompt、SSE、render 或页面。
# 对外结果必须做安全投影（例如 GET_BALANCE 只投影 balance_minor / currency）。
SERVER_ONLY_DATA_FIELDS: frozenset[str] = frozenset(
    {
        "daily_transfer_total_minor",
    }
)
