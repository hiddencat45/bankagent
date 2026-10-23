"""真实模型供应商适配器：OpenAI 兼容的 /chat/completions。

为什么是「OpenAI 兼容」而不是某家 SDK：DeepSeek、通义、Kimi、智谱、本地
vLLM/Ollama 都实现同一套协议，换供应商只改 base_url 与模型名，不必为每家
引一个包。这里只用已在依赖里的 httpx，不引入任何供应商 SDK。

三条铁律：

- **凭据只从环境变量读**，不进代码、不进日志、不进异常消息。
- **网络失败与「模型答得不对」是两类错误**：连不上、超时、HTTP 错误抛
  异常，由边界转成 ``MODEL_UNAVAILABLE``（请用户稍后重试）；而拿到了响应
  但内容不是合法候选时返回 ``None``，由边界判成 ``MODEL_OUTPUT_INVALID``
  （请用户重新描述）。混成一种会让用户对着「稍后重试」白等。
- **未配置就是 offline，配置了一半必须报错**。静默降级会让演示时以为接
  了模型、实际在跑关键词，这是最难在答辩现场自证的一类问题。

本模块仍然只产出**候选**。它返回的字典要经过 ``CandidateInterpreter`` 的
严格校验才会变成意图，金额、授权、风险分级一律由 Python 决定。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

DEFAULT_TIMEOUT = 20.0
# 正常候选不到 200 字节；给足余量，但仍要挡住异常巨大的响应体。
MAX_RESPONSE_BYTES = 256 * 1024
# 多数模型会用 ```json 包裹，剥掉再解析；这不是放宽校验，校验在后面。
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)

ENV_BASE_URL = "BANKAGENT_MODEL_BASE_URL"
ENV_API_KEY = "BANKAGENT_MODEL_API_KEY"
ENV_MODEL_NAME = "BANKAGENT_MODEL_NAME"
ENV_TIMEOUT = "BANKAGENT_MODEL_TIMEOUT"

_FORMAT_HINT = (
    "\n\n输出要求：只返回一个 JSON 对象，形如 "
    '{"scenario": <场景名或 null>, "intent": <意图名或 null>, "candidate_params": {...}}。'
    "不要输出 Markdown、代码块、解释或多余字段。"
)


class ProviderConfigError(RuntimeError):
    """配置本身有问题：缺项、URL 不合法、超时非正数。启动时就该失败。"""


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float = DEFAULT_TIMEOUT
    json_mode: bool = True

    def __post_init__(self) -> None:
        if not self.base_url.startswith(("http://", "https://")):
            raise ProviderConfigError("base_url 必须以 http:// 或 https:// 开头")
        if not self.model.strip():
            raise ProviderConfigError("model 不能为空")
        if not self.api_key.strip():
            raise ProviderConfigError("api_key 不能为空")
        if not (0 < self.timeout <= 120):
            raise ProviderConfigError("timeout 必须在 0 到 120 秒之间")

    @property
    def endpoint(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"


def _extract_json(content: str) -> Any:
    """从模型输出里取出候选对象；取不到就返回 None，交给边界判错。"""
    text = (content or "").strip()
    if not text:
        return None
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


class OpenAICompatibleModel:
    """``CandidateModel`` 的真实实现。``transport`` 仅供测试注入。"""

    def __init__(self, config: ProviderConfig, *, transport: httpx.BaseTransport | None = None):
        self._config = config
        # 记最近一次失败，供 health() 快速回报，避免 /health 每次真打模型。
        self._last_error: str | None = None
        self._client = httpx.Client(
            timeout=httpx.Timeout(config.timeout, connect=min(10.0, config.timeout)),
            # 不跟重定向：跨域重定向会把 Authorization 带到别的主机。
            follow_redirects=False,
            transport=transport,
        )

    # -- CandidateModel ---------------------------------------------------

    def health(self) -> bool:
        # 只反映「配置齐全 + 最近一次调用没失败」，不做网络探测。
        return self._last_error is None

    def predict(self, request: dict[str, Any]) -> Any:
        payload = self._payload(request)
        try:
            response = self._client.post(
                self._config.endpoint,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._config.api_key}",
                    "Content-Type": "application/json",
                },
            )
        except httpx.TimeoutException:
            self._last_error = "timeout"
            raise RuntimeError("MODEL_TIMEOUT") from None
        except httpx.HTTPError:
            # 不把底层异常挂成 __cause__：它可能带着完整 URL 与请求头。
            self._last_error = "network"
            raise RuntimeError("MODEL_NETWORK") from None

        if response.status_code != 200:
            # 只报状态码，不回显响应体——错误体里常带请求 id、甚至回显凭据。
            self._last_error = f"http_{response.status_code}"
            raise RuntimeError(f"MODEL_HTTP_{response.status_code}")

        if len(response.content) > MAX_RESPONSE_BYTES:
            self._last_error = "oversized"
            raise RuntimeError("MODEL_RESPONSE_TOO_LARGE")

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            # 响应结构不对：这是协议问题，不是候选问题。
            self._last_error = "shape"
            raise RuntimeError("MODEL_RESPONSE_INVALID") from None

        if not isinstance(content, str):
            self._last_error = "content"
            raise RuntimeError("MODEL_RESPONSE_INVALID") from None

        self._last_error = None
        # 解析不出来就返回 None：边界会判成 MODEL_OUTPUT_INVALID，
        # 提示用户重新描述，而不是让他对着「服务不可用」重试。
        return _extract_json(content)

    def close(self) -> None:
        self._client.close()

    # -- 内部 -------------------------------------------------------------

    def _payload(self, request: dict[str, Any]) -> dict[str, Any]:
        instruction = request.get("instruction") or ""
        # instruction 由公共边界给出，这里只补输出格式，不改判定语义。
        system = instruction if "JSON" in instruction else instruction + _FORMAT_HINT
        user = json.dumps(
            {
                "catalog": request.get("catalog") or [],
                "message": request.get("message") or "",
                "pending": request.get("pending"),
            },
            ensure_ascii=False,
        )
        payload: dict[str, Any] = {
            "model": self._config.model,
            # 意图识别要稳定，温度压低；不需要创造力。
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self._config.json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload


def _parse_timeout(raw: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ProviderConfigError("BANKAGENT_MODEL_TIMEOUT 必须是数字") from None
    if not (0 < value <= 120):
        raise ProviderConfigError("BANKAGENT_MODEL_TIMEOUT 必须在 0 到 120 秒之间")
    return value


def build_model_from_env(env: Mapping[str, str] | None = None) -> OpenAICompatibleModel | None:
    """按环境变量构建模型；全空返回 None（保持 offline）。

    只配了一部分时**抛错而不是返回 None**：这种情况几乎都是漏了某个变量，
    静默回退 offline 会让人以为模型已经在用。
    """
    source = os.environ if env is None else env
    base = (source.get(ENV_BASE_URL) or "").strip()
    key = (source.get(ENV_API_KEY) or "").strip()
    name = (source.get(ENV_MODEL_NAME) or "").strip()

    if not (base or key or name):
        return None

    missing = [
        var
        for var, value in ((ENV_BASE_URL, base), (ENV_API_KEY, key), (ENV_MODEL_NAME, name))
        if not value
    ]
    if missing:
        raise ProviderConfigError(
            "模型配置不完整，缺少：" + "、".join(missing)
            + "。三个变量都留空才会使用 offline 模式。"
        )

    timeout = _parse_timeout((source.get(ENV_TIMEOUT) or "").strip() or str(DEFAULT_TIMEOUT))
    return OpenAICompatibleModel(ProviderConfig(base_url=base, api_key=key, model=name, timeout=timeout))
