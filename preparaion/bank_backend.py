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
    BackendResult, TrustedContext, WriteContext,
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
