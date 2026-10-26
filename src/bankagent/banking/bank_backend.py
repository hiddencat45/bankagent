"""内存模拟后端。只接收服务端上下文，不连接真实银行或决定用户授权。

启动时由 A 注入已校验数据工厂、授权快照查询、操作哈希函数和共享 RLock。
API 的授权终态修改/整体验示重置必须持有同一锁；本模块不依赖图或场景。
未配置时失败关闭。进程重启丢失业务变更与幂等结果。
"""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from threading import RLock
from uuid import uuid4

from bankagent.banking.bank_types import (
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
            def reject(code, **detail):
                # 带上判断依据，让场景层能说清「为什么不行」而不只是「不行」。
                # 空 detail 仍给 None，保持既有结果形状。
                return _result("TRANSFER", data=detail or None, error=code)
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
                return reject("TRANSFER_LIMIT_EXCEEDED", amount_minor=amount_minor,
                              limit_minor=TRANSFER_SINGLE_LIMIT_MINOR)
            spent_today = self._daily_total(context.account_id, now.date())
            total = spent_today + amount_minor
            if total > YELLOW_DAILY_LIMIT_MINOR and record["risk_level"] != "RED":
                return reject("REAUTHORIZATION_REQUIRED", daily_total_minor=spent_today,
                              amount_minor=amount_minor, limit_minor=YELLOW_DAILY_LIMIT_MINOR)
            account = self._data["accounts"][context.account_id]
            if amount_minor > account["balance_minor"]:
                return reject("INSUFFICIENT_BALANCE", balance_minor=account["balance_minor"],
                              amount_minor=amount_minor)
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

    def query_cards(self, *, context: TrustedContext) -> BackendResult:
        with self.lock:
            if not self._owned(context):
                return _result("QUERY_CARDS", error="ACCOUNT_NOT_ACCESSIBLE")
            return _result("QUERY_CARDS", {"cards": [
                {"card_id": key, "display_name": row["display_name"], "status": row["status"]}
                for key, row in sorted(self._data["cards"].items())
                if row["account_id"] == context.account_id
            ]})

    def freeze_card(self, *, context: WriteContext, card_id: str) -> BackendResult:
        return self._change_card_status(context, card_id, "FREEZE_CARD")

    def unfreeze_card(self, *, context: WriteContext, card_id: str) -> BackendResult:
        return self._change_card_status(context, card_id, "UNFREEZE_CARD")

    def _change_card_status(self, context, card_id, operation):
        with self.lock:
            def reject(code):
                return _result(operation, error=code)
            if not self._owned(context):
                return reject("ACCOUNT_NOT_ACCESSIBLE")
            if not isinstance(context, WriteContext) or not context.authorization_ref:
                return reject("AUTHORIZATION_REQUIRED")
            if not isinstance(context.idempotency_key, str) or not context.idempotency_key:
                return reject("AUTHORIZATION_INVALID")
            if not isinstance(card_id, str):
                return reject("CARD_NOT_ACCESSIBLE")
            params = {"card_id": card_id}
            key = (context.user_id, context.account_id, context.idempotency_key)
            fingerprint = (context.request_id, operation, card_id)
            previous = self._completed.get(key)
            if previous:
                return deepcopy(previous[1]) if previous[0] == fingerprint else reject("IDEMPOTENCY_CONFLICT")
            card = self._data["cards"].get(card_id)
            if not card or card["account_id"] != context.account_id:
                return reject("CARD_NOT_ACCESSIBLE")
            record = deepcopy(self._lookup(context.authorization_ref))
            if not isinstance(record, dict) or self._hash is None:
                return reject("AUTHORIZATION_INVALID")
            identity = {"user_id": context.user_id, "account_id": context.account_id,
                        "request_id": context.request_id, "idempotency_key": context.idempotency_key,
                        "operation": operation, "params": params, "decision": "APPROVED"}
            expiry = record.get("expires_at")
            if (any(record.get(k) != v for k, v in identity.items())
                    or not record.get("challenge_id") or record.get("risk_level") not in {"YELLOW", "RED"}
                    or not isinstance(expiry, datetime) or expiry.utcoffset() is None or expiry <= self._now()):
                return reject("AUTHORIZATION_INVALID")
            base_context = TrustedContext(context.user_id, context.account_id, context.request_id)
            expected_hash = self._hash(base_context, operation, params)
            if not isinstance(expected_hash, str) or not expected_hash or record.get("operation_hash") != expected_hash:
                return reject("AUTHORIZATION_INVALID")
            target = {"FREEZE_CARD": "FROZEN", "UNFREEZE_CARD": "ACTIVE"}[operation]
            # 先构造状态与回执，最后一次发布；不产生资金流水或修改余额。
            updated = deepcopy(self._data)
            updated["cards"][card_id]["status"] = target
            result = _result(operation, {"card_id": card_id, "display_name": card["display_name"],
                "status": target, "previous_status": card["status"], "changed": card["status"] != target})
            completed = {**self._completed, key: (fingerprint, deepcopy(result))}
            self._data, self._completed = updated, completed
            return result

    def query_subscriptions(self, *, context: TrustedContext, start: date,
                            end: date) -> BackendResult:
        with self.lock:
            if not self._owned(context):
                return _result("QUERY_SUBSCRIPTIONS", error="ACCOUNT_NOT_ACCESSIBLE")
            if (type(start) is not date or type(end) is not date
                    or not 0 < (end - start).days <= BILLS_MAX_RANGE_DAYS):
                return _result("QUERY_SUBSCRIPTIONS", error="INVALID_DATE_RANGE")
            summaries, total = [], 0
            for subscription_id in sorted(self._data["subscriptions"]):
                row = self._data["subscriptions"][subscription_id]
                if row["account_id"] != context.account_id:
                    continue
                payments = []
                for transaction in self._data["transactions"]:
                    # 只认显式外键：同名商户不足以判定归属
                    if transaction["subscription_id"] != subscription_id:
                        continue
                    if (transaction["account_id"] != context.account_id
                            or transaction["kind"] != "EXPENSE"):
                        continue
                    if not start <= datetime.fromisoformat(
                            transaction["occurred_at"]).date() < end:
                        continue
                    payments.append({"transaction_id": transaction["transaction_id"],
                                     "occurred_at": transaction["occurred_at"],
                                     "amount_minor": transaction["amount_minor"]})
                    if len(payments) > MAX_BILL_TRANSACTIONS:
                        return _result("QUERY_SUBSCRIPTIONS",
                                       error="TOO_MANY_TRANSACTIONS")
                payments.sort(key=lambda p: (p["occurred_at"], p["transaction_id"]))
                paid = sum(p["amount_minor"] for p in payments)
                total += paid
                # 暂停不改旧流水：仍按外键统计历史扣款。
                summaries.append({
                    "subscription_id": subscription_id,
                    "display_name": row["display_name"],
                    "status": row["status"],
                    "amount_minor": row["amount_minor"],
                    "currency": row["currency"],
                    "next_payment_date": row["next_payment_date"],
                    "paid_minor": paid,
                    "payments": payments,
                })
            return _result("QUERY_SUBSCRIPTIONS", {
                "start": start.isoformat(), "end": end.isoformat(),
                "currency": SUPPORTED_CURRENCY, "total_minor": total,
                "subscriptions": summaries,
            })

    def find_subscriptions(self, *, context: TrustedContext,
                           name: str) -> list[SubscriptionRecord]:
        with self.lock:
            if not self._owned(context):
                raise PermissionError("ACCOUNT_NOT_ACCESSIBLE")
            if not isinstance(name, str) or not name.strip():
                return []
            return [{"subscription_id": subscription_id,
                     "display_name": row["display_name"],
                     "status": row["status"],
                     "amount_minor": row["amount_minor"],
                     "currency": row["currency"],
                     "next_payment_date": row["next_payment_date"]}
                    for subscription_id, row in sorted(self._data["subscriptions"].items())
                    if row["account_id"] == context.account_id
                    and row["display_name"] == name]

    def pause_subscription(self, *, context: WriteContext,
                           subscription_id: str) -> BackendResult:
        operation = "PAUSE_SUBSCRIPTION"
        with self.lock:
            def reject(code):
                return _result(operation, error=code)
            if not self._owned(context):
                return reject("ACCOUNT_NOT_ACCESSIBLE")
            if not isinstance(context, WriteContext) or not context.authorization_ref:
                return reject("AUTHORIZATION_REQUIRED")
            if not isinstance(context.idempotency_key, str) or not context.idempotency_key:
                return reject("AUTHORIZATION_INVALID")
            if not isinstance(subscription_id, str):
                return reject("SUBSCRIPTION_NOT_ACCESSIBLE")
            params = {"subscription_id": subscription_id}
            key = (context.user_id, context.account_id, context.idempotency_key)
            fingerprint = (context.request_id, operation, subscription_id)
            previous = self._completed.get(key)
            if previous:
                return deepcopy(previous[1]) if previous[0] == fingerprint else reject(
                    "IDEMPOTENCY_CONFLICT")
            row = self._data["subscriptions"].get(subscription_id)
            if not row or row["account_id"] != context.account_id:
                return reject("SUBSCRIPTION_NOT_ACCESSIBLE")
            record = deepcopy(self._lookup(context.authorization_ref))
            if not isinstance(record, dict) or self._hash is None:
                return reject("AUTHORIZATION_INVALID")
            identity = {"user_id": context.user_id, "account_id": context.account_id,
                        "request_id": context.request_id,
                        "idempotency_key": context.idempotency_key,
                        "operation": operation, "params": params, "decision": "APPROVED"}
            expiry = record.get("expires_at")
            if (any(record.get(k) != v for k, v in identity.items())
                    or not record.get("challenge_id")
                    or record.get("risk_level") not in {"YELLOW", "RED"}
                    or not isinstance(expiry, datetime) or expiry.utcoffset() is None
                    or expiry <= self._now()):
                return reject("AUTHORIZATION_INVALID")
            base_context = TrustedContext(context.user_id, context.account_id,
                                          context.request_id)
            expected_hash = self._hash(base_context, operation, params)
            if (not isinstance(expected_hash, str) or not expected_hash
                    or record.get("operation_hash") != expected_hash):
                return reject("AUTHORIZATION_INVALID")
            # 先构造状态与回执，最后一次发布；暂停不改余额、不产生资金流水。
            updated = deepcopy(self._data)
            updated["subscriptions"][subscription_id]["status"] = "PAUSED"
            updated["subscriptions"][subscription_id]["next_payment_date"] = None
            result = _result(operation, {
                "subscription_id": subscription_id,
                "display_name": row["display_name"],
                "status": "PAUSED",
                "amount_minor": row["amount_minor"],
                "currency": row["currency"],
                "next_payment_date": None,
                "previous_status": row["status"],
                "changed": row["status"] != "PAUSED",
            })
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


# 卡片接口按 #26 提案在本功能分支实现，订阅接口仍为占位。
# 尚未接入图/API/页面，不注册可用场景，不把后端完成当作页面已交付。
# 共用已建立的 TrustedContext/WriteContext、BackendResult 和整数分。

def query_cards(*, context: TrustedContext) -> BackendResult:
    """QUERY_CARDS，READ/GREEN；data 为 bank_types.CardsData。

    只返回当前账户的卡，按 card_id 排序；空集为 {"cards": []}。
    账户归属失败为 REJECTED/ACCOUNT_NOT_ACCESSIBLE。
    场景以 display_name 精确匹配候选，零个或多个匹配都澄清，不任选。
    """
    return _configured().query_cards(context=context)


def freeze_card(*, context: WriteContext, card_id: str) -> BackendResult:
    """FREEZE_CARD，WRITE/YELLOW；data 为 bank_types.CardChangeData。

    ACTIVE -> FROZEN，仅临时冻结，不是永久挂失。已冻结返回 COMPLETED、
    changed=False；仍须验证授权，不因无变更跳过校验。
    失败及幂等语义同 unfreeze_card；不改变余额或创建资金流水。
    本轮仅模拟卡片状态，没有刷卡扣款路径，也不联动账户转账或代扣协议。
    """
    return _configured().freeze_card(context=context, card_id=card_id)


def unfreeze_card(*, context: WriteContext, card_id: str) -> BackendResult:
    """UNFREEZE_CARD，WRITE/YELLOW；data 为 bank_types.CardChangeData。

    FROZEN -> ACTIVE；已激活返回 COMPLETED、changed=False。
    card_id 只由 query_cards 受控解析；不存在或不属账户统一返回
    REJECTED/CARD_NOT_ACCESSIBLE。账户、授权、幂等错误沿用转账错误码。
    新写入在共享锁内重查授权/期限/操作参数；同键同参数返回首次结果，
    同键异参数为 IDEMPOTENCY_CONFLICT，状态与幂等结果原子保存。
    首次结果是历史操作回执，不代表当前状态；冻结后解冻，再重放原冻结
    只能返回原回执，不得再次冻结。当前状态另用 query_cards 查询。
    """
    return _configured().unfreeze_card(context=context, card_id=card_id)


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
    return _configured().query_subscriptions(context=context, start=start, end=end)


def find_subscriptions(*, context: TrustedContext,
                       name: str) -> list[SubscriptionRecord]:
    """服务端名称解析，非新增场景操作；不依赖消费期间或流水数量。

    当前账户内精确匹配 display_name，含已暂停项，按 subscription_id 排序。
    无匹配返回 []，多匹配由场景澄清；归属失败同 find_contacts，抛
    PermissionError("ACCOUNT_NOT_ACCESSIBLE")，由公共 resolve 边界转码。
    """
    return _configured().find_subscriptions(context=context, name=name)


def pause_subscription(*, context: WriteContext,
                       subscription_id: str) -> BackendResult:
    """PAUSE_SUBSCRIPTION，WRITE/YELLOW；data 为 bank_types.SubscriptionChangeData。

    ACTIVE -> PAUSED，next_payment_date 置 None；已暂停仍查授权后返回
    COMPLETED、changed=False。这是模拟银行侧暂停代扣，不承诺终止商户合同、
    退款；本轮仅改模拟状态，尚未模拟后续扣款执行，原期间消费及余额不变。
    名称由 find_subscriptions 受控解析，歧义须澄清；不存在或不属当前账户
    统一为 SUBSCRIPTION_NOT_ACCESSIBLE。其余失败和原子幂等语义同卡片写入。
    """
    return _configured().pause_subscription(context=context,
                                            subscription_id=subscription_id)
