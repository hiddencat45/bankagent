"""请求校验：只接受「一句话」或「一次恢复」，绝不接受可信字段。

对应契约 §4.1。这个模块的关键词是**拒绝**——凡是拿不准的一律拒绝，
因为参数里混进 ``user_id`` 或 ``authorized`` 就意味着信任边界破了。

设计取舍：不抛裸 ``ValueError``，统一抛带 HTTP 状态码的 :class:`ApiError`，
让服务器层直接映射，不用再猜每个异常该返回 400 还是 409。
"""

from dataclasses import dataclass
from typing import Any, Literal

from bank_types import UNTRUSTED_STATE_FIELDS

__all__ = [
    "ApiError",
    "ChatRequest",
    "UNTRUSTED_REQUEST_FIELDS",
    "UNTRUSTED_RESUME_FIELDS",
    "parse_chat_request",
]

# 契约 §4.1：公开请求不得包含这些字段，收到即拒。
#
# ``thread_id`` 与 ``challenge_id`` 允许出现，但它们只是**服务端引用的回传**，
# 服务器必须重新校验归属，不能当成可信 ID。
UNTRUSTED_REQUEST_FIELDS: frozenset[str] = UNTRUSTED_STATE_FIELDS | {
    "balance_minor", "operation", "params",
}

# challenge_id 是 resume 中唯一允许回传的服务端引用。
UNTRUSTED_RESUME_FIELDS: frozenset[str] = (
    UNTRUSTED_REQUEST_FIELDS - {"challenge_id"}
) | {"approved", "auth_token", "token", "created_at", "decided_at"}

# 顶层允许的键，其余一律视为客户端 bug。
_ALLOWED_REQUEST_KEYS: frozenset[str] = frozenset({"thread_id", "message", "resume"})
_ALLOWED_RESUME_KEYS: frozenset[str] = frozenset({"challenge_id", "decision", "otp"})

_DECISIONS = frozenset({"approve", "reject"})


class ApiError(Exception):
    """带 HTTP 状态码与错误码的 API 异常。

    ``code`` 是给前端判断用的稳定标识，``message`` 只用于展示，
    两者都不含内部细节或堆栈（契约 §4.1）。
    """

    def __init__(self, code: str, message: str, http_status: int) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass(frozen=True)
class ChatRequest:
    """校验通过的请求。字段与契约 §4.1 一一对应。"""

    thread_id: str | None
    message: str | None
    resume: "ResumePayload | None"

    @property
    def is_resume(self) -> bool:
        return self.resume is not None


@dataclass(frozen=True)
class ResumePayload:
    """恢复意图。

    ``otp`` **不保存原文到任何持久结构**：调用方消费后应立即丢弃，
    契约 §4.3 第 5 条。这里保留在估算用的对象里只是因为要传给
    ``ChallengeStore.decide``，用完即弃。
    """

    challenge_id: str
    decision: Literal["approve", "reject"]
    otp: str | None


def _require_object(payload: Any, *, what: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApiError("INVALID_REQUEST", f"{what}必须是 JSON 对象。", 400)
    return payload


def _reject_unknown_keys(payload: dict[str, Any], allowed: frozenset[str], *,
                         what: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ApiError(
            "INVALID_REQUEST",
            f"{what}包含未知字段：{'、'.join(unknown)}。",
            400,
        )


def _reject_untrusted(payload: dict[str, Any], untrusted: frozenset[str], *,
                      what: str) -> None:
    """命中可信字段就拒，不做静默忽略。

    先查未知键再查这个会更友好，但**顺序反过来才对**：如果客户端传了
    ``user_id``，报 ``UNTRUSTED_FIELD`` 比报"未知字段"更能说明问题性质。
    """
    hits = sorted(set(payload) & untrusted)
    if hits:
        raise ApiError(
            "UNTRUSTED_FIELD",
            f"{what}不得包含可信字段：{'、'.join(hits)}。",
            400,
        )


def parse_chat_request(payload: Any) -> ChatRequest:
    """解析并校验 ``POST /agent/chat`` 的请求体。

    只接受两种形态（契约 §4.1）：

    * 非空 ``message`` + 无 ``resume``
    * ``message`` 为 ``None`` 或缺失 + 完整 ``resume``

    同时提供两者、或两者都缺，都拒绝。
    """
    payload = _require_object(payload, what="请求体")
    _reject_untrusted(payload, UNTRUSTED_REQUEST_FIELDS, what="请求体")
    _reject_unknown_keys(payload, _ALLOWED_REQUEST_KEYS, what="请求体")

    thread_id = payload.get("thread_id")
    if thread_id is not None and (not isinstance(thread_id, str) or not thread_id.strip()):
        raise ApiError("INVALID_REQUEST", "thread_id 必须是非空字符串。", 400)

    message = payload.get("message")
    resume_raw = payload.get("resume")

    if message is not None and not isinstance(message, str):
        raise ApiError("INVALID_REQUEST", "message 必须是字符串或 null。", 400)
    if resume_raw is not None and not isinstance(resume_raw, dict):
        raise ApiError("INVALID_REQUEST", "resume 必须是对象或 null。", 400)

    has_message = isinstance(message, str) and message.strip() != ""
    has_resume = resume_raw is not None

    if has_message and has_resume:
        raise ApiError(
            "INVALID_REQUEST",
            "message 与 resume 不能同时提供：一次请求只能办理一件事。",
            400,
        )
    if not has_message and not has_resume:
        raise ApiError(
            "INVALID_REQUEST",
            "必须提供非空 message，或提供 resume。",
            400,
        )

    resume = _parse_resume(resume_raw) if has_resume else None

    return ChatRequest(
        thread_id=thread_id.strip() if isinstance(thread_id, str) else None,
        message=message.strip() if has_message else None,
        resume=resume,
    )


def _parse_resume(raw: dict[str, Any]) -> ResumePayload:
    _reject_untrusted(raw, UNTRUSTED_RESUME_FIELDS, what="resume")
    _reject_unknown_keys(raw, _ALLOWED_RESUME_KEYS, what="resume")

    challenge_id = raw.get("challenge_id")
    if not isinstance(challenge_id, str) or not challenge_id.strip():
        raise ApiError("INVALID_REQUEST", "resume.challenge_id 必须是非空字符串。", 400)

    decision = raw.get("decision")
    if not isinstance(decision, str) or decision not in _DECISIONS:
        raise ApiError(
            "INVALID_REQUEST",
            "resume.decision 只能是 approve 或 reject。",
            400,
        )

    otp = raw.get("otp")
    if otp is not None and not isinstance(otp, str):
        raise ApiError("INVALID_REQUEST", "resume.otp 必须是字符串或 null。", 400)

    return ResumePayload(
        challenge_id=challenge_id.strip(),
        decision=decision,
        otp=otp or None,
    )
