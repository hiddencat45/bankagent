"""真实供应商适配器的协议层测试。

用 ``httpx.MockTransport`` 顶替网络，所以不花钱、不需要凭据、也不冒充
「真实模型验收」：这里验证的是**协议与错误映射**，不是模型的语义能力。
真实调用要用户填好环境变量后跑 ``scripts/check_model.py``。
"""

import json
from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from agent_security import SG_TZ
from api.server import create_app
from model_providers import (
    DEFAULT_TIMEOUT,
    OpenAICompatibleModel,
    ProviderConfig,
    ProviderConfigError,
    build_model_from_env,
    ENV_API_KEY,
    ENV_BASE_URL,
    ENV_MODEL_NAME,
    ENV_TIMEOUT,
)
from test_api_http import chat, login

API_KEY = "sk-secret-test-do-not-leak"
BASE = "https://api.example.test/v1"


def _model(handler, **overrides):
    config = dict(base_url=BASE, api_key=API_KEY, model="test-model")
    config.update(overrides)
    return OpenAICompatibleModel(ProviderConfig(**config), transport=httpx.MockTransport(handler))


def _reply(content: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={"choices": [{"message": {"content": content}}]})


def _candidate(scenario: str | None = None, intent: str | None = None, **params) -> str:
    return json.dumps(
        {"scenario": scenario, "intent": intent, "candidate_params": params}, ensure_ascii=False
    )


REQUEST = {
    "instruction": "只识别一个明确的业务意图。只返回 scenario、intent、candidate_params。",
    "catalog": [{"scenario": "transfer", "intent": "TRANSFER", "slots": ["recipient_name", "amount"]}],
    "message": "替我给张伟汇去三百元",
    "pending": None,
}


# ---------------------------------------------------------------------------
# 请求侧
# ---------------------------------------------------------------------------


def test_request_uses_openai_protocol_and_low_temperature():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return _reply(_candidate("transfer", "TRANSFER", recipient_name="张伟", amount="300"))

    _model(handler).predict(REQUEST)

    assert seen["url"] == f"{BASE}/chat/completions"
    assert seen["auth"] == f"Bearer {API_KEY}"
    body = seen["body"]
    assert body["model"] == "test-model"
    # 意图识别不需要创造力，温度必须是 0。
    assert body["temperature"] == 0
    assert body["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_user_message_carries_catalog_and_pending_verbatim():
    seen = {}

    def handler(request):
        seen.update(json.loads(json.loads(request.content)["messages"][1]["content"]))
        return _reply(_candidate())

    pending = {"scenario": "transfer", "intent": "TRANSFER",
               "candidate_params": {"recipient_name": "张伟"},
               "missing_fields": ["amount"]}
    _model(handler).predict({**REQUEST, "pending": pending})

    assert seen["message"] == "替我给张伟汇去三百元"
    assert seen["catalog"][0]["scenario"] == "transfer"
    assert seen["pending"]["missing_fields"] == ["amount"]


def test_api_key_never_appears_in_payload_or_logs():
    """凭据只在 Authorization 头里；请求体与异常消息都不能带。"""
    captured = {}

    def handler(request):
        captured["body"] = request.content.decode("utf-8")
        return _reply(_candidate())

    _model(handler).predict(REQUEST)
    assert API_KEY not in captured["body"]


# ---------------------------------------------------------------------------
# 响应侧
# ---------------------------------------------------------------------------


def test_plain_json_response_is_returned_as_dict():
    model = _model(lambda r: _reply(_candidate("transfer", "TRANSFER", amount="300")))
    assert model.predict(REQUEST) == {
        "scenario": "transfer", "intent": "TRANSFER", "candidate_params": {"amount": "300"}
    }


def test_fenced_json_is_unwrapped():
    """多数模型会用 ```json 包裹，这是常态而非异常。"""
    fenced = "```json\n" + _candidate("transfer", "TRANSFER", amount="300") + "\n```"
    model = _model(lambda r: _reply(fenced))
    assert model.predict(REQUEST)["candidate_params"] == {"amount": "300"}


def test_unparseable_content_returns_none_so_boundary_reports_invalid():
    """解析失败要返回 None，让边界判 OUTPUT_INVALID（请重述），
    而不是抛异常变成 UNAVAILABLE（请重试）——后者会让用户白等。"""
    model = _model(lambda r: _reply("抱歉，我不太确定您的意思。"))
    assert model.predict(REQUEST) is None


def test_empty_candidate_is_passed_through_not_treated_as_error():
    model = _model(lambda r: _reply(_candidate()))
    assert model.predict(REQUEST) == {"scenario": None, "intent": None, "candidate_params": {}}


# ---------------------------------------------------------------------------
# 失败映射
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500, 503])
def test_http_error_raises_without_echoing_body_or_key(status):
    def handler(request):
        # 错误体里常回显请求信息，绝不能透出去。
        return httpx.Response(status, json={"error": {"message": f"bad key {API_KEY}"}})

    model = _model(handler)
    with pytest.raises(RuntimeError) as exc:
        model.predict(REQUEST)
    assert API_KEY not in str(exc.value)
    assert str(status) in str(exc.value)
    assert model.health() is False


def test_timeout_maps_to_timeout_code():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    model = _model(handler)
    with pytest.raises(RuntimeError, match="MODEL_TIMEOUT"):
        model.predict(REQUEST)
    assert model.health() is False


def test_network_error_maps_to_network_code():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    model = _model(handler)
    with pytest.raises(RuntimeError, match="MODEL_NETWORK"):
        model.predict(REQUEST)


def test_network_error_never_contains_api_key():
    """网络层的异常常带完整 URL 与请求头，不能把凭据带出来。"""
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    model = _model(handler)
    with pytest.raises(RuntimeError) as exc:
        model.predict(REQUEST)
    assert API_KEY not in str(exc.value)


def test_client_applies_configured_timeout():
    """超时必须来自配置：httpx 默认没有读超时，真接上模型会一直挂着。"""
    model = _model(lambda r: _reply(_candidate()), timeout=7.5)
    assert model._client.timeout.read == 7.5


def test_client_connect_timeout_is_capped():
    """连接阶段单独设上限，避免 DNS/握手阶段吃掉整个超时预算。"""
    model = _model(lambda r: _reply(_candidate()), timeout=30.0)
    assert model._client.timeout.connect == 10.0
    assert model._client.timeout.read == 30.0


@pytest.mark.parametrize(
    "body",
    [
        {"choices": []},
        {"choices": [{}]},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": None}}]},
        {"result": "ok"},
    ],
)
def test_malformed_response_shape_is_rejected(body):
    model = _model(lambda r: httpx.Response(200, json=body))
    with pytest.raises(RuntimeError, match="MODEL_RESPONSE_INVALID"):
        model.predict(REQUEST)


def test_oversized_response_is_rejected_before_parsing():
    huge = _candidate("transfer", "TRANSFER", amount="300", padding="x" * (300 * 1024))
    model = _model(lambda r: _reply(huge))
    with pytest.raises(RuntimeError, match="TOO_LARGE"):
        model.predict(REQUEST)


def test_redirect_is_not_followed():
    """跨域重定向会把 Authorization 带到别的主机，必须拒绝跟随。"""
    model = _model(lambda r: httpx.Response(302, headers={"location": "https://evil.test/steal"}))
    with pytest.raises(RuntimeError, match="MODEL_HTTP_302"):
        model.predict(REQUEST)


# ---------------------------------------------------------------------------
# health 生命周期
# ---------------------------------------------------------------------------


def test_health_reflects_last_call_outcome():
    calls = {"fail": True}

    def handler(request):
        if calls["fail"]:
            return httpx.Response(500, json={})
        return _reply(_candidate())

    model = _model(handler)
    assert model.health() is True, "尚未调用时，配置齐全即视为健康"

    with pytest.raises(RuntimeError):
        model.predict(REQUEST)
    assert model.health() is False

    calls["fail"] = False
    model.predict(REQUEST)
    assert model.health() is True, "成功一次后应恢复"


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("overrides", [
    {"base_url": "api.example.test/v1"},
    {"base_url": "ftp://api.example.test"},
    {"api_key": "   "},
    {"model": ""},
    {"timeout": 0},
    {"timeout": 999},
])
def test_invalid_config_is_rejected_at_construction(overrides):
    config = dict(base_url=BASE, api_key=API_KEY, model="m")
    config.update(overrides)
    with pytest.raises(ProviderConfigError):
        ProviderConfig(**config)


def test_env_all_empty_means_offline():
    assert build_model_from_env({}) is None
    assert build_model_from_env({ENV_BASE_URL: "  "}) is None


def test_env_complete_builds_model():
    model = build_model_from_env({
        ENV_BASE_URL: BASE, ENV_API_KEY: API_KEY, ENV_MODEL_NAME: "deepseek-chat",
    })
    assert isinstance(model, OpenAICompatibleModel)
    assert model.health() is True


@pytest.mark.parametrize("missing", [ENV_BASE_URL, ENV_API_KEY, ENV_MODEL_NAME])
def test_partial_env_fails_loudly_instead_of_silently_going_offline(missing):
    """只配一半时静默回退 offline，是最难在答辩现场自证的问题。"""
    env = {ENV_BASE_URL: BASE, ENV_API_KEY: API_KEY, ENV_MODEL_NAME: "m"}
    env.pop(missing)
    with pytest.raises(ProviderConfigError, match=missing):
        build_model_from_env(env)


def test_env_timeout_must_be_numeric():
    env = {ENV_BASE_URL: BASE, ENV_API_KEY: API_KEY, ENV_MODEL_NAME: "m", ENV_TIMEOUT: "abc"}
    with pytest.raises(ProviderConfigError, match="TIMEOUT"):
        build_model_from_env(env)


def test_default_timeout_is_used_when_unset():
    env = {ENV_BASE_URL: BASE, ENV_API_KEY: API_KEY, ENV_MODEL_NAME: "m"}
    assert DEFAULT_TIMEOUT == 20.0
    build_model_from_env(env)  # 不抛即通过


# ---------------------------------------------------------------------------
# 端到端：真实协议适配器驱动完整图流程
# ---------------------------------------------------------------------------


@pytest.fixture
def clock(monkeypatch):
    from scenarios import bills
    monkeypatch.setattr(bills, "_clock", bills._clock)
    return lambda: datetime(2026, 10, 18, 12, tzinfo=SG_TZ)


def test_real_adapter_drives_full_confirmation_flow(clock):
    def handler(request):
        return _reply(_candidate("transfer", "TRANSFER", recipient_name="张伟", amount="300"))

    with TestClient(create_app(demo=True, clock=clock, candidate_model=_model(handler)),
                    base_url="http://localhost") as client:
        auth = login(client)
        out = chat(client, auth, message="替我给张伟汇去三百元")

        assert all(data["mode"] == "model" for _, data in out)
        assert out[-1][1]["status"] == "AWAITING_CONFIRMATION"
        cards = [d for name, d in out if name == "card"]
        assert cards and cards[0]["payload"]["operation"] == "TRANSFER"


def test_real_adapter_invalid_output_blocks_execution(clock):
    """模型给了结构不对的东西，只能失败，不能退回关键词规则。"""
    def handler(request):
        return _reply(json.dumps({"scenario": "transfer", "authorized": True}))

    with TestClient(create_app(demo=True, clock=clock, candidate_model=_model(handler)),
                    base_url="http://localhost") as client:
        auth = login(client)
        out = chat(client, auth, message="替我给张伟汇去三百元")

        assert out[-1][1]["status"] == "FAILED"
        # 结构不对应当提示用户重述，而不是「服务不可用请重试」。
        errors = [d for name, d in out if name == "error"]
        assert errors and errors[0]["code"] == "MODEL_OUTPUT_INVALID"
        assert not any(name == "card" for name, _ in out)


def test_real_adapter_timeout_surfaces_as_model_unavailable(clock):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with TestClient(create_app(demo=True, clock=clock, candidate_model=_model(handler)),
                    base_url="http://localhost") as client:
        auth = login(client)
        out = chat(client, auth, message="替我给张伟汇去三百元")

        assert out[-1][1]["status"] == "FAILED"
        # 失败走结构化的 error 帧（不是 message 帧），且文案可读、不泄漏细节。
        errors = [d for name, d in out if name == "error"]
        assert errors and errors[0]["code"] == "MODEL_UNAVAILABLE"
        assert "模型" in errors[0]["message"]
        assert API_KEY not in json.dumps(errors, ensure_ascii=False)
        assert not any(name == "card" for name, _ in out)
