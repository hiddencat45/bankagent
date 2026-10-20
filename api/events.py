"""SSE 事件信封：把图的结果翻译成页面的 6 种事件。

契约 §4.2 把事件类型**冻结**为 6 个，并规定：

* 每条事件的 ``data`` 都含同一组 ``thread_id`` / ``request_id`` / ``mode``
* 页面显示的一切必须来自这里，**不得用定时器伪造进度**
* 顺序：首次 ``status`` → 业务事件 → 最终 ``done``
* ``done`` 只表示流结束，**不表示业务成功**

因此本模块只做"结构正确"，不做"业务判断"：谁该发哪种事件由调用方决定，
这里保证每个事件封套完整、事件名合法、序列化稳定。
"""

import json
from typing import Any, Iterable, Literal

__all__ = [
    "CARD_TYPES",
    "MODE_MODEL",
    "MODE_OFFLINE",
    "SSE_EVENTS",
    "STATUS_STEPS",
    "card",
    "done",
    "envelopes",
    "error",
    "format_sse",
    "interrupt",
    "message",
    "status",
]

# 冻结的 6 种事件（契约 §4.2）。
SSE_EVENTS: tuple[str, ...] = (
    "status",
    "message",
    "card",
    "interrupt",
    "error",
    "done",
)

MODE_OFFLINE = "offline"
MODE_MODEL = "model"

# 卡片的 3 种类型（契约 §4.2）。
CARD_TYPES: frozenset[str] = frozenset({"confirm", "evidence", "result"})

# status.step 的允许取值。不保证每次都有全部步骤。
STATUS_STEPS: frozenset[str] = frozenset({
    "started",
    "understood",
    "validated",
    "awaiting_confirmation",
    "awaiting_authentication",
    "executing",
    "finished",
})


def _base(*, thread_id: str, request_id: str, mode: str) -> dict[str, Any]:
    if mode not in (MODE_OFFLINE, MODE_MODEL):
        raise ValueError(f"未知 mode：{mode!r}")
    if not thread_id or not request_id:
        raise ValueError("thread_id 与 request_id 都必须非空")
    return {"thread_id": thread_id, "request_id": request_id, "mode": mode}


def status(*, thread_id: str, request_id: str, mode: str, step: str,
           status_value: str) -> dict[str, Any]:
    """进度事件。``step`` 必须真实发生过，不能提前发。"""
    if step not in STATUS_STEPS:
        raise ValueError(f"未知 step：{step!r}")
    return {
        **_base(thread_id=thread_id, request_id=request_id, mode=mode),
        "step": step,
        "status": status_value,
    }


def message(*, thread_id: str, request_id: str, mode: str, text: str) -> dict[str, Any]:
    """给用户看的一句话。不含内部推理或敏感字段。"""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("message.text 不能为空")
    return {**_base(thread_id=thread_id, request_id=request_id, mode=mode), "text": text}


def card(*, thread_id: str, request_id: str, mode: str, card_type: str,
         payload: dict[str, Any]) -> dict[str, Any]:
    """结构化卡片。类型只能是 confirm / evidence / result。"""
    if card_type not in CARD_TYPES:
        raise ValueError(f"未知 card.type：{card_type!r}")
    if not isinstance(payload, dict):
        raise ValueError("card.payload 必须是对象")
    return {
        **_base(thread_id=thread_id, request_id=request_id, mode=mode),
        "type": card_type,
        "payload": payload,
    }


def interrupt(*, thread_id: str, request_id: str, mode: str, kind: str,
              challenge_id: str, operation_hash: str,
              prompt: str) -> dict[str, Any]:
    """暂停事件。确认卡必须在有 interrupt 时才启用按钮。"""
    if kind not in ("CONFIRMATION", "STRONG_AUTH"):
        raise ValueError(f"未知 interrupt.kind：{kind!r}")
    if not challenge_id or not operation_hash:
        raise ValueError("interrupt 必须带 challenge_id 与 operation_hash")
    return {
        **_base(thread_id=thread_id, request_id=request_id, mode=mode),
        "kind": kind,
        "challenge_id": challenge_id,
        "operation_hash": operation_hash,
        "prompt": prompt,
    }


def error(*, thread_id: str, request_id: str, mode: str, code: str,
          message_text: str) -> dict[str, Any]:
    """流开始后的错误。只给稳定 code 与可展示文案，不给堆栈。"""
    if not code:
        raise ValueError("error.code 不能为空")
    return {
        **_base(thread_id=thread_id, request_id=request_id, mode=mode),
        "code": code,
        "message": message_text,
    }


def done(*, thread_id: str, request_id: str, mode: str,
         status_value: str) -> dict[str, Any]:
    """流结束。**不表示业务成功**，只表示这次 HTTP 流到此为止。"""
    return {
        **_base(thread_id=thread_id, request_id=request_id, mode=mode),
        "status": status_value,
    }


def format_sse(event: str, data: dict[str, Any]) -> str:
    """序列化成 SSE 帧。

    用 ``ensure_ascii=False`` 保留中文，用紧凑分隔符减少体积；
    JSON 保证单行，因此不需要拆 ``data:`` 多行。
    """
    if event not in SSE_EVENTS:
        raise ValueError(f"未知事件类型：{event!r}")
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return f"event: {event}\ndata: {body}\n\n"


def envelopes(events: Iterable[tuple[str, dict[str, Any]]]) -> str:
    """把一串 ``(事件名, data)`` 拼成完整的 SSE 响应体（便于测试与回放）。"""
    return "".join(format_sse(name, data) for name, data in events)


# 类型别名，便于调用方标注顺序约束。
EventOrder = Literal["status", "message", "card", "interrupt", "error", "done"]
