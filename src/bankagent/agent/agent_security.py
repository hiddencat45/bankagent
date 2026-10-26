"""服务端安全层：操作哈希、挑战登记与授权查询。

契约 §3.4 把这几件事划给 A：

- ``compute_operation_hash`` 是**唯一的**纯函数，A 用它算初始哈希、B 注入后端复查；
  两边必须算出同一个值，所以算法只能有一份。
- 挑战表记录待确认/待认证的操作；授权查询 ``lookup_authorization`` 交给后端注入。
- 记录里**不含** OTP、密码或生物特征；凭证只在 API 层短暂消费后丢弃（§4.3）。

三条硬约束：

1. **resume 载荷不是授权凭证。** 它只是"给服务端验证的输入"。恢复后的节点读
   服务端记录，不读 ``decision``、不读 ``otp``。
2. **终态不可翻转。** 批准后再拒绝、拒绝后再批准都是 ``CHALLENGE_INVALID``，
   不改变已完成的业务。
3. **同挑战重复提交相同终态返回已保存状态**，便于 HTTP 重试幂等。

本模块不导入图模块、场景模块或 API，只依赖 ``bank_types``，保持可测试。
"""

from __future__ import annotations

import hashlib
import json
import threading
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable
from uuid import uuid4

from bankagent.banking.bank_types import (
    CHALLENGE_TIMEOUT_MINUTES,
    SUPPORTED_CURRENCY,
    RiskLevel,
    TrustedContext,
)

__all__ = [
    "ChallengeError",
    "ChallengeStore",
    "compute_operation_hash",
    "SG_TZ",
]

# 演示统一使用新加坡时区（契约 §0）。只作为默认时钟，可注入替换。
SG_TZ = timezone(timedelta(hours=8))

# 只有写操作需要挑战。GREEN 只读不登记。
_CHALLENGEABLE_RISKS: frozenset[str] = frozenset({"YELLOW", "RED"})

# 终态集合：一旦离开 PENDING 就不能再变。
_TERMINAL: frozenset[str] = frozenset({"APPROVED", "REJECTED", "CANCELLED"})


class ChallengeError(Exception):
    """挑战校验失败。

    ``code`` 直接对应契约 §4.5 的错误码，API 层据此返回 409 或 400，
    不再自行猜测原因。
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail

    def __str__(self) -> str:  # pragma: no cover - 仅日志用
        return f"{self.code}: {self.detail}" if self.detail else self.code


# ---------------------------------------------------------------------------
# 操作哈希：唯一实现
# ---------------------------------------------------------------------------


def _canonical(value: Any) -> Any:
    """把参数转成可稳定序列化的形式。

    金额一律整数分，所以这里**不接受 float**——一旦有 float 混进来，
    哈希会把二进制误差固化进授权绑定，两边还可能算出不同的值。
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, Decimal):
        # Decimal 按十进制字面量输出，避免 1.10 与 1.1 算出不同哈希。
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, float):
        raise TypeError("float is not allowed in operation params; use integer minor units")
    raise TypeError(f"unsupported param type for hashing: {type(value).__name__}")


def compute_operation_hash(
    context: TrustedContext,
    operation: str,
    params: dict[str, Any],
) -> str:
    """计算绑定「用户 + 账户 + 请求 + 操作 + 全部参数」的哈希。

    稳定 JSON 规则：``sort_keys=True``、紧凑分隔符、``ensure_ascii=False``、
    禁止 NaN/Infinity。任何一处不同都会得到不同哈希，从而让后端拒绝执行。
    """
    if not isinstance(operation, str) or not operation:
        raise ValueError("operation must be a non-empty string")
    if not isinstance(params, dict):
        raise ValueError("params must be a dict")

    payload = {
        "account_id": context.account_id,
        "operation": operation,
        "params": _canonical(params),
        "request_id": context.request_id,
        "user_id": context.user_id,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# ---------------------------------------------------------------------------
# 挑战与授权记录
# ---------------------------------------------------------------------------


class ChallengeStore:
    """服务端挑战表，兼作后端的授权查询来源。

    ``lock`` 应与后端写入共用同一把可重入锁（契约 §3.4 要求"同一进程内互斥"），
    避免撤销/重置与扣款竞态。默认自建一把 ``RLock``，测试与 Demo 单进程足够。
    """

    def __init__(
        self,
        *,
        lock: threading.RLock | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._lock = lock if lock is not None else threading.RLock()
        self._clock = clock if clock is not None else (lambda: datetime.now(SG_TZ))
        self._records: dict[str, dict[str, Any]] = {}
        # (user_id, request_id, operation_hash) → challenge_id，用于幂等登记。
        self._by_key: dict[tuple[str, str, str], str] = {}

    # -- 内部 -------------------------------------------------------------

    def _now(self) -> datetime:
        now = self._clock()
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise ValueError("challenge clock must return a timezone aware datetime")
        return now

    def _record(self, challenge_id: str) -> dict[str, Any]:
        record = self._records.get(challenge_id)
        if record is None:
            raise ChallengeError("CHALLENGE_INVALID", "unknown challenge")
        return record

    @staticmethod
    def _is_expired(record: dict[str, Any], now: datetime) -> bool:
        return record["expires_at"] <= now

    # -- 登记 -------------------------------------------------------------

    def register(
        self,
        *,
        context: TrustedContext,
        operation: str,
        params: dict[str, Any],
        operation_hash: str,
        risk_level: RiskLevel,
        ttl_minutes: int = CHALLENGE_TIMEOUT_MINUTES,
    ) -> dict[str, Any]:
        """登记待确认挑战；同一 ``(user, request, operation_hash)`` 幂等。

        幂等保证来自契约 §4.3：``interrupt()`` 恢复时节点会重新执行，
        API 可能重复登记，不能因此生成两个挑战或两把幂等键。
        已经过期的待处理挑战会被替换成新挑战，避免旧卡片复活。
        """
        if risk_level not in _CHALLENGEABLE_RISKS:
            raise ValueError(f"risk {risk_level!r} does not require a challenge")
        if not isinstance(operation_hash, str) or not operation_hash:
            raise ValueError("operation_hash must be a non-empty string")
        if not isinstance(ttl_minutes, int) or ttl_minutes <= 0:
            raise ValueError("ttl_minutes must be a positive int")

        with self._lock:
            now = self._now()
            key = (context.user_id, context.request_id, operation_hash)
            existing_id = self._by_key.get(key)
            if existing_id is not None:
                existing = self._records.get(existing_id)
                # 仍在有效期内的待处理挑战直接复用；终态也复用（幂等重放）。
                if existing is not None and not (
                    existing["decision"] == "PENDING" and self._is_expired(existing, now)
                ):
                    return deepcopy(existing)

            challenge_id = f"ch-{uuid4().hex}"
            record = {
                "challenge_id": challenge_id,
                "user_id": context.user_id,
                "account_id": context.account_id,
                "request_id": context.request_id,
                "operation": operation,
                "params": deepcopy(params),
                "operation_hash": operation_hash,
                "risk_level": risk_level,
                # 幂等键由服务端生成并固定在记录上；恢复与重试都复用它。
                "idempotency_key": f"idem-{uuid4().hex}",
                "decision": "PENDING",
                "expires_at": now + timedelta(minutes=ttl_minutes),
            }
            self._records[challenge_id] = record
            self._by_key[key] = challenge_id
            return deepcopy(record)

    # -- 提交决定 ---------------------------------------------------------

    def decide(
        self,
        *,
        challenge_id: str,
        user_id: str,
        request_id: str,
        operation_hash: str,
        decision: str,
        authenticated: bool = False,
    ) -> dict[str, Any]:
        """校验并落定用户决定。

        ``decision`` 只接受 ``"approve"`` / ``"reject"``。这是**输入**，
        不是授权凭证——落定后的记录才是后端可查的授权事实。

        RED 挑战的 approve 必须带 ``authenticated=True``；该布尔值只能由
        API 在独立认证校验通过后传入，不能来自客户端载荷（§4.3 明确禁止
        用客户端布尔值或固定口令充当认证结果）。
        """
        if decision not in {"approve", "reject"}:
            raise ChallengeError("INVALID_REQUEST", f"unknown decision {decision!r}")

        with self._lock:
            record = self._record(challenge_id)
            if record["user_id"] != user_id or record["request_id"] != request_id:
                # 归属不符与不存在同样处理，避免探测他人挑战是否存在。
                raise ChallengeError("CHALLENGE_INVALID", "ownership mismatch")
            if record["operation_hash"] != operation_hash:
                # 参数被改过：必须重新确认，不能沿用旧决定。
                raise ChallengeError("CHALLENGE_STATE_MISMATCH", "operation hash changed")

            now = self._now()
            target = "APPROVED" if decision == "approve" else "REJECTED"
            current = record["decision"]

            # 重复提交相同终态 → 返回已保存状态（幂等）。
            if current == target:
                return deepcopy(record)
            # 终态不可翻转。
            if current in _TERMINAL:
                raise ChallengeError("CHALLENGE_INVALID", "challenge already settled")

            if self._is_expired(record, now):
                raise ChallengeError("CHALLENGE_INVALID", "challenge expired")

            if target == "APPROVED" and record["risk_level"] == "RED" and not authenticated:
                # 强认证未通过时不能落成 APPROVED。
                raise ChallengeError("CHALLENGE_INVALID", "strong authentication required")

            record["decision"] = target
            return deepcopy(record)

    # -- 取消 -------------------------------------------------------------

    def cancel(self, *, challenge_id: str, user_id: str, request_id: str) -> dict[str, Any]:
        """取消待处理挑战，让同一会话可以重新办理（§1.5 RUN_BUSY）。

        已终态的挑战保持不变：取消不能抹掉已完成的业务。
        """
        with self._lock:
            record = self._record(challenge_id)
            if record["user_id"] != user_id or record["request_id"] != request_id:
                raise ChallengeError("CHALLENGE_INVALID", "ownership mismatch")
            if record["decision"] == "PENDING":
                record["decision"] = "CANCELLED"
            return deepcopy(record)

    # -- 查询 -------------------------------------------------------------

    def lookup(self, authorization_ref: str) -> dict[str, Any] | None:
        """授权查询，注入给后端使用（契约 §3.4 的 ``lookup_authorization``）。

        返回**快照**而非存储对象，调用方改不到内部状态。
        """
        if not isinstance(authorization_ref, str) or not authorization_ref:
            return None
        with self._lock:
            record = self._records.get(authorization_ref)
            return deepcopy(record) if record is not None else None

    def pending(self, *, user_id: str, request_id: str) -> dict[str, Any] | None:
        """该会话是否有未处理的挑战；用于 RUN_BUSY 判定。"""
        with self._lock:
            now = self._now()
            for record in self._records.values():
                if (record["user_id"] == user_id
                        and record["request_id"] == request_id
                        and record["decision"] == "PENDING"
                        and not self._is_expired(record, now)):
                    return deepcopy(record)
            return None

    def invalidate_all(self) -> None:
        """重置演示数据时调用，让旧挑战与旧授权全部失效（§3.5）。

        清空而不是标记：旧确认卡从此查不到记录，无法继续扣款。
        """
        with self._lock:
            self._records.clear()
            self._by_key.clear()
