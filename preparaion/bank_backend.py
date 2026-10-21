"""内存模拟后端。只接收服务端上下文，不连接真实银行或决定用户授权。

启动时由 A 注入已校验数据工厂、授权快照查询、操作哈希函数和共享 RLock。
API 的授权终态修改/整体验示重置必须持有同一锁；本模块不依赖图或场景。
未配置时失败关闭。进程重启丢失业务变更与幂等结果。
"""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from threading import RLock
from uuid import uuid4

from bank_types import (
    BILLS_MAX_RANGE_DAYS, MAX_BILL_TRANSACTIONS, SUPPORTED_CURRENCY,
    TRANSFER_SINGLE_LIMIT_MINOR, YELLOW_DAILY_LIMIT_MINOR,
    BackendResult, SubscriptionRecord, TrustedContext, WriteContext,
)


def _result(operation: str, data=None, error=None) -> BackendResult:
    return {"operation": operation, "status": "REJECTED" if error else "COMPLETED",
            "data": data, "error_code": error}


class BankBackend:
    """单个模拟实例；工厂数据是后端私有副本，所有读写使用共享互斥锁。"""

    def __init__(self, *, data_factory, lookup_authorization=None,
                 operation_hash=None, lock=None, clock=None):
        self.lock = lock if lock is not None else RLock()
        self._factory = data_factory
        self._lookup = lookup_authorization or (lambda _: None)
        self._hash = operation_hash
        self._clock = clock or (lambda: datetime.now(timezone(timedelta(hours=8))))
        self._data = deepcopy(data_factory())
        self._completed = {}

    def _owned(self, context):
        if not isinstance(context, TrustedContext):
            return False
        if not all(isinstance(v, str) and v for v in (
                context.user_id, context.account_id, context.request_id)):
            return False
        account = self._data["accounts"].get(context.account_id)
        return bool(account and account["user_id"] == context.user_id)

    def _now(self):
        value = self._clock()
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError("backend clock must be timezone aware")
        return value.astimezone(timezone(timedelta(hours=8)))

    def _daily_total(self, account_id, today):
        return sum(t["amount_minor"] for t in self._data["transactions"]
                   if t["account_id"] == account_id and t["kind"] == "TRANSFER_OUT"
                   and datetime.fromisoformat(t["occurred_at"]).date() == today)

    def get_balance(self, *, context: TrustedContext) -> BackendResult:
        with self.lock:
            if not self._owned(context):
                return _result("GET_BALANCE", error="ACCOUNT_NOT_ACCESSIBLE")
            return _result("GET_BALANCE", {
                "balance_minor": self._data["accounts"][context.account_id]["balance_minor"],
                "currency": SUPPORTED_CURRENCY,
                "daily_transfer_total_minor": self._daily_total(
                    context.account_id, self._now().date()),
            })

    def find_contacts(self, *, context: TrustedContext, name: str) -> list[dict[str, str]]:
        with self.lock:
            if not self._owned(context):
                raise PermissionError("ACCOUNT_NOT_ACCESSIBLE")
            if not isinstance(name, str) or not name.strip():
                return []
            return [{"contact_id": key, "display_name": row["display_name"]}
                    for key, row in sorted(self._data["contacts"].items())
                    if row["user_id"] == context.user_id and row["display_name"] == name.strip()]

    def query_bills(self, *, context: TrustedContext, start: date, end: date) -> BackendResult:
        with self.lock:
            if not self._owned(context):
                return _result("QUERY_BILLS", error="ACCOUNT_NOT_ACCESSIBLE")
            if (type(start) is not date or type(end) is not date
                    or not 0 < (end - start).days <= BILLS_MAX_RANGE_DAYS):
                return _result("QUERY_BILLS", error="INVALID_DATE_RANGE")
            selected = []
            for t in self._data["transactions"]:
                if (t["account_id"] == context.account_id
                        and start <= datetime.fromisoformat(t["occurred_at"]).date() < end):
                    selected.append(t)
                    if len(selected) > MAX_BILL_TRANSACTIONS:
                        return _result("QUERY_BILLS", error="TOO_MANY_TRANSACTIONS")
            selected.sort(key=lambda t: (t["occurred_at"], t["transaction_id"]))
            categories, windows, anomalies = {}, {}, []
            for t in selected:
                if t["kind"] != "EXPENSE":
                    continue
                cat = t["category"]
                categories[cat] = categories.get(cat, 0) + t["amount_minor"]
                if not t["merchant"]:
                    continue
                key = (t["merchant"], t["amount_minor"])
                now = datetime.fromisoformat(t["occurred_at"])
                window = windows.get(key)
                if window is None or (now - window[0]).total_seconds() > 60:
                    window = (now, [])
                    windows[key] = window
                window[1].append(t["transaction_id"])
                if len(window[1]) == 2:
                    anomalies.append({"type": "POSSIBLE_DUPLICATE", "evidence": window[1]})
            fields = ("transaction_id", "occurred_at", "kind", "amount_minor", "category", "merchant")
            data = {"start": start.isoformat(), "end": end.isoformat(),
                    "currency": SUPPORTED_CURRENCY, "total_minor": sum(categories.values()),
                    "by_category": categories,
                    "top_category": min(categories, key=lambda c: (-categories[c], c)) if categories else None,
                    "transactions": [{f: t[f] for f in fields} for t in selected],
                    "anomalies": anomalies}
            return _result("QUERY_BILLS", deepcopy(data))

    def execute_transfer(self, *, context: WriteContext, contact_id: str,
                         amount_minor: int, currency: str = SUPPORTED_CURRENCY) -> BackendResult:
        with self.lock:
            def reject(code):
                return _result("TRANSFER", error=code)
            if not self._owned(context):
                return reject("ACCOUNT_NOT_ACCESSIBLE")
            if not isinstance(context, WriteContext) or not context.authorization_ref:
                return reject("AUTHORIZATION_REQUIRED")
            if not isinstance(context.idempotency_key, str) or not context.idempotency_key:
                return reject("AUTHORIZATION_INVALID")
            if type(amount_minor) is not int or amount_minor <= 0:
                return reject("INVALID_AMOUNT")
            if currency != SUPPORTED_CURRENCY:
                return reject("UNSUPPORTED_CURRENCY")
            if not isinstance(contact_id, str):
                return reject("CONTACT_NOT_ACCESSIBLE")
            params = {"contact_id": contact_id, "amount_minor": amount_minor, "currency": currency}
            key = (context.user_id, context.account_id, context.idempotency_key)
            fingerprint = (context.request_id, "TRANSFER", contact_id, amount_minor, currency)
            previous = self._completed.get(key)
            if previous:
                return deepcopy(previous[1]) if previous[0] == fingerprint else reject("IDEMPOTENCY_CONFLICT")
            contact = self._data["contacts"].get(contact_id)
            if not contact or contact["user_id"] != context.user_id:
                return reject("CONTACT_NOT_ACCESSIBLE")
            now = self._now()
            record = deepcopy(self._lookup(context.authorization_ref))
            if not isinstance(record, dict) or self._hash is None:
                return reject("AUTHORIZATION_INVALID")
            identity = {"user_id": context.user_id, "account_id": context.account_id,
                        "request_id": context.request_id, "idempotency_key": context.idempotency_key,
                        "operation": "TRANSFER", "params": params, "decision": "APPROVED"}
            expiry = record.get("expires_at")
            if (any(record.get(k) != v for k, v in identity.items())
                    or not record.get("challenge_id") or record.get("risk_level") not in {"YELLOW", "RED"}
                    or not isinstance(expiry, datetime) or expiry.utcoffset() is None or expiry <= now):
                return reject("AUTHORIZATION_INVALID")
            base_context = TrustedContext(context.user_id, context.account_id, context.request_id)
            expected_hash = self._hash(base_context, "TRANSFER", params)
            if not isinstance(expected_hash, str) or not expected_hash or record.get("operation_hash") != expected_hash:
                return reject("AUTHORIZATION_INVALID")
            if amount_minor > TRANSFER_SINGLE_LIMIT_MINOR:
                return reject("TRANSFER_LIMIT_EXCEEDED")
            total = self._daily_total(context.account_id, now.date()) + amount_minor
            if total > YELLOW_DAILY_LIMIT_MINOR and record["risk_level"] != "RED":
                return reject("REAUTHORIZATION_REQUIRED")
            account = self._data["accounts"][context.account_id]
            if amount_minor > account["balance_minor"]:
                return reject("INSUFFICIENT_BALANCE")
            # 在锁内先构造完整副本与幂等结果，全部成功后一起发布，不留半笔账。
            updated = deepcopy(self._data)
            balance = account["balance_minor"] - amount_minor
            updated["accounts"][context.account_id]["balance_minor"] = balance
            transaction_id = f"txn-{uuid4().hex}"
            updated["transactions"].append({"transaction_id": transaction_id,
                "account_id": context.account_id, "occurred_at": now.isoformat(),
                "kind": "TRANSFER_OUT", "amount_minor": amount_minor,
                "category": "转账", "merchant": None})
            result = _result("TRANSFER", {"transaction_id": transaction_id,
                "recipient": contact["display_name"], "amount_minor": amount_minor,
                "currency": currency, "remaining_balance_minor": balance})
            completed = {**self._completed, key: (fingerprint, deepcopy(result))}
            self._data, self._completed = updated, completed
            return result

    def reset_demo_data(self) -> None:
        """仅恢复内部数据；A 必须在同一锁内另行使会话/授权/Checkpoint 失效。"""
        with self.lock:
            replacement = deepcopy(self._factory())
            self._data, self._completed = replacement, {}


_backend: BankBackend | None = None


def configure_backend(**dependencies) -> BankBackend:
    """仅供服务端启动：data_factory、lookup_authorization、operation_hash、lock、clock。

    operation_hash 签名为 (TrustedContext, operation: str, params: dict) -> str，
    lookup_authorization 为 (authorization_ref: str) -> dict | None。
    配置后不得在请求处理中更换实例；API 只能调用下面的受控业务函数。
    """
    global _backend
    _backend = BankBackend(**dependencies)
    return _backend


def _configured() -> BankBackend:
    if _backend is None:
        raise RuntimeError("backend not configured")
    return _backend


def get_balance(*, context: TrustedContext) -> BackendResult:
    return _configured().get_balance(context=context)


def find_contacts(*, context: TrustedContext, name: str) -> list[dict[str, str]]:
    return _configured().find_contacts(context=context, name=name)


def query_bills(*, context: TrustedContext, start: date, end: date) -> BackendResult:
    return _configured().query_bills(context=context, start=start, end=end)


def execute_transfer(*, context: WriteContext, contact_id: str,
                     amount_minor: int, currency: str = SUPPORTED_CURRENCY) -> BackendResult:
    return _configured().execute_transfer(context=context, contact_id=contact_id,
                                         amount_minor=amount_minor, currency=currency)


def reset_demo_data() -> None:
    _configured().reset_demo_data()


# 以下接口属于卡片/订阅契约提案，确认后另一个 feat/ PR 实现。
# 目前不注册场景、不启用白名单、不更换数据集，不把占位函数当成功能力。
# 共用已建立的 TrustedContext/WriteContext、BackendResult 和整数分。

def query_cards(*, context: TrustedContext) -> BackendResult:
    """QUERY_CARDS，READ/GREEN；data 为 bank_types.CardsData。

    只返回当前账户的卡，按 card_id 排序；空集为 {"cards": []}。
    账户归属失败为 REJECTED/ACCOUNT_NOT_ACCESSIBLE。
    场景以 display_name 精确匹配候选，零个或多个匹配都澄清，不任选。
    """
    raise NotImplementedError("QUERY_CARDS is not implemented")


def freeze_card(*, context: WriteContext, card_id: str) -> BackendResult:
    """FREEZE_CARD，WRITE/YELLOW；data 为 bank_types.CardChangeData。

    ACTIVE -> FROZEN，仅临时冻结，不是永久挂失。已冻结返回 COMPLETED、
    changed=False；仍须验证授权，不因无变更跳过校验。
    失败及幂等语义同 unfreeze_card；不改变余额或创建资金流水。
    """
    raise NotImplementedError("FREEZE_CARD is not implemented")


def unfreeze_card(*, context: WriteContext, card_id: str) -> BackendResult:
    """UNFREEZE_CARD，WRITE/YELLOW；data 为 bank_types.CardChangeData。

    FROZEN -> ACTIVE；已激活返回 COMPLETED、changed=False。
    card_id 只由 query_cards 受控解析；不存在或不属账户统一返回
    REJECTED/CARD_NOT_ACCESSIBLE。账户、授权、幂等错误沿用转账错误码。
    新写入在共享锁内重查授权/期限/操作参数；同键同参数返回首次结果，
    同键异参数为 IDEMPOTENCY_CONFLICT，状态与幂等结果原子保存。
    """
    raise NotImplementedError("UNFREEZE_CARD is not implemented")


def query_subscriptions(*, context: TrustedContext, start: date,
                        end: date) -> BackendResult:
    """QUERY_SUBSCRIPTIONS，READ/GREEN；data 为 bank_types.SubscriptionsData。

    查询当前账户已登记的全部协议（含暂停项），按 subscription_id 排序；
    payments 仅包含 [start, end) 内明确关联的 EXPENSE，按时间/流水ID排序。
    paid_minor 为这些流水之和，total_minor 为各协议合计；暂停不改旧流水。
    协议与流水须同账户且一笔流水最多归属一个协议，不能只凭同名商户推断。
    空集返回零总额和空列表；没有当期扣款的协议仍显示，paid_minor 为零。
    日期范围、时区和最大跨度沿用 query_bills；关联流水最多
    MAX_BILL_TRANSACTIONS 笔，超限不截断。
    错误为 ACCOUNT_NOT_ACCESSIBLE、INVALID_DATE_RANGE、TOO_MANY_TRANSACTIONS。
    """
    raise NotImplementedError("QUERY_SUBSCRIPTIONS is not implemented")


def find_subscriptions(*, context: TrustedContext,
                       name: str) -> list[SubscriptionRecord]:
    """服务端名称解析，非新增场景操作；不依赖消费期间或流水数量。

    当前账户内精确匹配 display_name，含已暂停项，按 subscription_id 排序。
    无匹配返回 []，多匹配由场景澄清；归属失败同 find_contacts，抛
    PermissionError("ACCOUNT_NOT_ACCESSIBLE")，由公共 resolve 边界转码。
    """
    raise NotImplementedError("subscription lookup is not implemented")


def pause_subscription(*, context: WriteContext,
                       subscription_id: str) -> BackendResult:
    """PAUSE_SUBSCRIPTION，WRITE/YELLOW；data 为 bank_types.SubscriptionChangeData。

    ACTIVE -> PAUSED，next_payment_date 置 None；已暂停仍查授权后返回
    COMPLETED、changed=False。这是模拟银行侧暂停代扣，不承诺终止商户合同、
    退款或已接通自动扣款调度；原期间消费及余额不变。
    名称由 find_subscriptions 受控解析，歧义须澄清；不存在或不属当前账户
    统一为 SUBSCRIPTION_NOT_ACCESSIBLE。其余失败和原子幂等语义同卡片写入。
    """
    raise NotImplementedError("PAUSE_SUBSCRIPTION is not implemented")
