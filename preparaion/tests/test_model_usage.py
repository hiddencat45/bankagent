"""模型调用的可观测性：证明「真的在调」而不是「看起来在调」。

``/health`` 的 ``model: ok`` 不足以回答这个问题——它只反映配置齐全、上次
没失败，从没调用过同样是 ok。计费口径的 ``calls`` 才是凭据：没有真实请求
就不会增长。
"""

from datetime import datetime

import httpx
from fastapi.testclient import TestClient

from agent_security import SG_TZ
from api.server import create_app
from model_providers import OpenAICompatibleModel, ProviderConfig
from test_api_http import chat, login

CLOCK = lambda: datetime(2026, 10, 18, 12, tzinfo=SG_TZ)
API_KEY = "sk-secret-test-do-not-leak"
BASE = "https://api.example.test/v1"


def _reply(content, prompt=10, completion=5):
    return httpx.Response(200, json={
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion},
    })


def _model(handler):
    return OpenAICompatibleModel(
        ProviderConfig(base_url=BASE, api_key=API_KEY, model="test-model"),
        transport=httpx.MockTransport(handler))


def test_offline_reports_zero_calls():
    with TestClient(create_app(demo=True, clock=CLOCK), base_url="http://localhost") as client:
        usage = client.get("/model/usage").json()
    assert usage == {"mode": "offline", "calls": 0, "prompt_tokens": 0, "completion_tokens": 0}


def test_calls_are_counted_only_after_a_real_request():
    def handler(request):
        return _reply('{"scenario": "balance", "intent": "BALANCE_QUERY", "candidate_params": {}}')

    app = create_app(demo=True, clock=CLOCK, candidate_model=_model(handler))
    with TestClient(app, base_url="http://localhost") as client:
        before = client.get("/model/usage").json()
        chat(client, login(client), message="我的余额")
        after = client.get("/model/usage").json()

    assert before["calls"] == 0
    assert after["calls"] == 1
    assert after["prompt_tokens"] == 10
    assert after["completion_tokens"] == 5
    assert after["mode"] == "model"


def test_health_stays_ok_without_ever_calling_the_model():
    """这条钉住 /health 的局限：没调用过它也说 ok，所以不能拿它当证据。"""
    app = create_app(demo=True, clock=CLOCK, candidate_model=_model(
        lambda request: _reply('{"scenario": null, "intent": null, "candidate_params": {}}')))
    with TestClient(app, base_url="http://localhost") as client:
        assert client.get("/health").json()["model"] == "ok"
        assert client.get("/model/usage").json()["calls"] == 0


def test_failed_calls_do_not_inflate_the_counter():
    """网络层失败不算一次成功调用——否则计数就失去意义了。"""
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    model = _model(handler)
    try:
        model.predict({"instruction": "json", "message": "x", "catalog": [], "pending": None})
    except RuntimeError:
        pass
    assert model.stats()["calls"] == 0
