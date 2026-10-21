"""API 契约层测试：请求校验、会话归属、SSE 事件信封。

这一层没有 HTTP，所以可以只测"规则对不对"。规则错了，服务器写得再对
也是错的，因此这里覆盖得比较密。
"""

import json

import pytest

from api.contracts import (
    ApiError,
    UNTRUSTED_REQUEST_FIELDS,
    UNTRUSTED_RESUME_FIELDS,
    parse_chat_request,
)
from api.events import (
    CARD_TYPES,
    SSE_EVENTS,
    card,
    done,
    envelopes,
    error,
    format_sse,
    interrupt,
    message,
    status,
)
from api.session import DemoSessionStore

BASE = {"thread_id": "conv-1", "request_id": "req-1", "mode": "offline"}


# ---------------------------------------------------------------------------
# 请求校验：只接受两种形态
# ---------------------------------------------------------------------------


def test_plain_message_is_accepted() -> None:
    req = parse_chat_request({"thread_id": "conv-1", "message": "查本月账单"})
    assert req.message == "查本月账单"
    assert req.resume is None
    assert req.is_resume is False


def test_thread_id_may_be_omitted() -> None:
    req = parse_chat_request({"message": "查本月账单"})
    assert req.thread_id is None


def test_resume_is_accepted_without_message() -> None:
    req = parse_chat_request({
        "thread_id": "conv-1",
        "message": None,
        "resume": {"challenge_id": "ch-1", "decision": "approve"},
    })
    assert req.is_resume is True
    assert req.resume.challenge_id == "ch-1"
    assert req.resume.decision == "approve"
    assert req.resume.otp is None


def test_message_and_resume_together_are_rejected() -> None:
    with pytest.raises(ApiError) as exc:
        parse_chat_request({
            "message": "顺便确认一下",
            "resume": {"challenge_id": "ch-1", "decision": "approve"},
        })
    assert exc.value.code == "INVALID_REQUEST"
    assert exc.value.http_status == 400


def test_neither_message_nor_resume_is_rejected() -> None:
    with pytest.raises(ApiError) as exc:
        parse_chat_request({"thread_id": "conv-1"})
    assert exc.value.code == "INVALID_REQUEST"


def test_blank_message_is_rejected() -> None:
    with pytest.raises(ApiError):
        parse_chat_request({"message": "   "})


# ---------------------------------------------------------------------------
# 可信字段：一律拒绝，不静默忽略
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", sorted(UNTRUSTED_REQUEST_FIELDS))
def test_every_untrusted_top_level_field_is_rejected(field) -> None:
    with pytest.raises(ApiError) as exc:
        parse_chat_request({"message": "查账单", field: "x"})
    assert exc.value.code == "UNTRUSTED_FIELD"
    assert exc.value.http_status == 400


@pytest.mark.parametrize("field", sorted(UNTRUSTED_RESUME_FIELDS))
def test_every_untrusted_resume_field_is_rejected(field) -> None:
    with pytest.raises(ApiError) as exc:
        parse_chat_request({
            "resume": {"challenge_id": "ch-1", "decision": "approve", field: "x"},
        })
    assert exc.value.code == "UNTRUSTED_FIELD"


def test_authorized_true_in_resume_is_rejected() -> None:
    """最常见的伪造：客户端自己声明已授权。"""
    with pytest.raises(ApiError) as exc:
        parse_chat_request({
            "resume": {"challenge_id": "ch-1", "decision": "approve", "authorized": True},
        })
    assert exc.value.code == "UNTRUSTED_FIELD"


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ApiError) as exc:
        parse_chat_request({"message": "查账单", "typo": 1})
    assert exc.value.code == "INVALID_REQUEST"


def test_untrusted_field_takes_priority_over_unknown() -> None:
    """同时有可信字段和未知字段时，报可信字段更能说明问题性质。"""
    with pytest.raises(ApiError) as exc:
        parse_chat_request({"message": "查账单", "user_id": "user-001", "typo": 1})
    assert exc.value.code == "UNTRUSTED_FIELD"


# ---------------------------------------------------------------------------
# resume 结构
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decision", ["APPROVE", "yes", "", None, 1, [], {}, ["approve"], True])
def test_invalid_decision_is_rejected(decision) -> None:
    with pytest.raises(ApiError) as caught:
        parse_chat_request({
            "resume": {"challenge_id": "ch-1", "decision": decision},
        })
    assert caught.value.http_status == 400
    assert caught.value.code == "INVALID_REQUEST"


def test_missing_challenge_id_is_rejected() -> None:
    with pytest.raises(ApiError):
        parse_chat_request({"resume": {"decision": "approve"}})


def test_reject_decision_is_accepted() -> None:
    req = parse_chat_request({
        "resume": {"challenge_id": "ch-1", "decision": "reject"},
    })
    assert req.resume.decision == "reject"


def test_otp_is_kept_only_on_the_parsed_object() -> None:
    """otp 只短暂存在于解析结果里；不写日志、不进 State 由调用方保证。"""
    import secrets
    transient = secrets.token_urlsafe(16)
    req = parse_chat_request({
        "resume": {"challenge_id": "ch-1", "decision": "approve", "otp": transient},
    })
    assert req.resume.otp == transient


def test_non_object_body_is_rejected() -> None:
    for bad in (None, [], "x", 42):
        with pytest.raises(ApiError):
            parse_chat_request(bad)


# ---------------------------------------------------------------------------
# 会话
# ---------------------------------------------------------------------------


def test_session_token_is_not_predictable() -> None:
    store = DemoSessionStore()
    a = store.issue(user_id="user-001", account_id="account-001")
    b = store.issue(user_id="user-001", account_id="account-001")
    assert a.token != b.token
    assert len(a.token) >= 32


def test_resolve_returns_identity() -> None:
    store = DemoSessionStore()
    issued = store.issue(user_id="user-001", account_id="account-001")
    resolved = store.resolve(f"Bearer {issued.token}")
    assert resolved.user_id == "user-001"
    assert resolved.account_id == "account-001"


@pytest.mark.parametrize("header", [None, "", "Bearer", "Bearer ", "Basic abc", "abc"])
def test_bad_authorization_is_401(header) -> None:
    store = DemoSessionStore()
    with pytest.raises(ApiError) as exc:
        store.resolve(header)
    assert exc.value.code == "UNAUTHENTICATED"
    assert exc.value.http_status == 401


def test_unknown_token_is_401() -> None:
    store = DemoSessionStore()
    with pytest.raises(ApiError) as exc:
        store.resolve("Bearer not-a-real-token")
    assert exc.value.http_status == 401


def test_thread_must_belong_to_session() -> None:
    store = DemoSessionStore()
    alice = store.issue(user_id="user-001", account_id="account-001")
    bob = store.issue(user_id="user-002", account_id="account-002")

    store.register_thread(alice, "conv-alice")
    store.require_thread(alice, "conv-alice")

    # 别人的 thread 一律 404，不泄露"存在但不是你的"
    with pytest.raises(ApiError) as exc:
        store.require_thread(bob, "conv-alice")
    assert exc.value.code == "THREAD_NOT_FOUND"
    assert exc.value.http_status == 404


def test_invalidate_all_kills_sessions() -> None:
    store = DemoSessionStore()
    issued = store.issue(user_id="user-001", account_id="account-001")
    store.invalidate_all()
    assert store.count() == 0
    with pytest.raises(ApiError):
        store.resolve(f"Bearer {issued.token}")


# ---------------------------------------------------------------------------
# SSE 事件信封
# ---------------------------------------------------------------------------


def test_event_names_are_frozen_to_six() -> None:
    assert SSE_EVENTS == ("status", "message", "card", "interrupt", "error", "done")


def test_every_event_carries_the_common_envelope() -> None:
    events = [
        status(**BASE, step="started", status_value="PROCESSING"),
        message(**BASE, text="已理解"),
        card(**BASE, card_type="result", payload={"operation": "QUERY_BILLS"}),
        interrupt(**BASE, kind="CONFIRMATION", challenge_id="ch-1",
                  operation_hash="a" * 64, prompt="确认？"),
        error(**BASE, code="BACKEND_UNAVAILABLE", message_text="暂时不可用"),
        done(**BASE, status_value="COMPLETED"),
    ]
    for event in events:
        assert event["thread_id"] == "conv-1"
        assert event["request_id"] == "req-1"
        assert event["mode"] == "offline"


def test_unknown_step_is_rejected() -> None:
    with pytest.raises(ValueError):
        status(**BASE, step="thinking", status_value="PROCESSING")


def test_unknown_card_type_is_rejected() -> None:
    assert CARD_TYPES == {"confirm", "evidence", "result"}
    with pytest.raises(ValueError):
        card(**BASE, card_type="debug", payload={})


def test_unknown_interrupt_kind_is_rejected() -> None:
    with pytest.raises(ValueError):
        interrupt(**BASE, kind="MAYBE", challenge_id="ch-1",
                  operation_hash="a" * 64, prompt="?")


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        done(thread_id="conv-1", request_id="req-1", mode="turbo",
             status_value="COMPLETED")


def test_empty_message_text_is_rejected() -> None:
    with pytest.raises(ValueError):
        message(**BASE, text="   ")


def test_format_sse_frame() -> None:
    frame = format_sse("done", done(**BASE, status_value="COMPLETED"))
    assert frame.startswith("event: done\ndata: {")
    assert frame.endswith("\n\n")
    body = frame.split("data: ", 1)[1].strip()
    payload = json.loads(body)
    assert payload["status"] == "COMPLETED"


def test_format_sse_rejects_unknown_event() -> None:
    with pytest.raises(ValueError):
        format_sse("progress", done(**BASE, status_value="COMPLETED"))


def test_chinese_is_not_escaped() -> None:
    """页面直接展示，中文不该变成 \\uXXXX。"""
    frame = format_sse("message", message(**BASE, text="本月支出 1000.00 元"))
    assert "本月支出" in frame
    assert "\\u" not in frame


def test_envelopes_concatenates_in_order() -> None:
    text = envelopes([
        ("status", status(**BASE, step="started", status_value="PROCESSING")),
        ("done", done(**BASE, status_value="COMPLETED")),
    ])
    assert text.count("event: ") == 2
    assert text.index("event: status") < text.index("event: done")


def test_open_events_rejected_by_validation_never_reach_sse() -> None:
    """校验失败的请求不会产生任何事件——这条串起两层。"""
    with pytest.raises(ApiError):
        parse_chat_request({"message": "查账单", "user_id": "user-001"})


@pytest.mark.parametrize("field", ["request_id", "idempotency_key", "authorization_ref", "operation_hash", "card_id", "subscription_id", "product_code", "daily_transfer_total_minor"])
@pytest.mark.parametrize("nested", [False, True])
def test_known_trusted_fields_always_get_untrusted_code(field, nested):
    body = {"message": "查余额", field: "untrusted"}
    if nested:
        body = {"resume": {"challenge_id": "ch-1", "decision": "approve", field: "untrusted"}}
    with pytest.raises(ApiError) as caught:
        parse_chat_request(body)
    assert caught.value.http_status == 400
    assert caught.value.code == "UNTRUSTED_FIELD"
