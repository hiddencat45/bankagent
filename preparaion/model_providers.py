"""真实模型供应商适配器：OpenAI 兼容的 /chat/completions。

默认按 **DeepSeek** 调好（base_url `https://api.deepseek.com`、模型
`deepseek-flash`），同时保持对其它 OpenAI 兼容供应商可用：换 `base_url`
与模型名即可。

三条铁律：

- **凭据只从环境变量读**，不进代码、不进日志、不进异常消息。
- **网络失败与「模型答得不对」是两类错误**：连不上、超时、HTTP 错误抛
  异常，由边界转成 ``MODEL_UNAVAILABLE``（请用户稍后重试）；而拿到了响应
  但内容不是合法候选时返回 ``None``，由边界判成 ``MODEL_OUTPUT_INVALID``
  （请用户重新描述）。混成一种会让用户对着「稍后重试」白等。
- **未配置就是 offline，配置了一半必须报错**。静默降级会让演示时以为接
  了模型、实际在跑关键词，这是最难在答辩现场自证的一类问题。

DeepSeek 有三处与「想当然的 OpenAI 兼容」不同，都按官方文档处理：

1. **思考模式默认开启**（``thinking.type`` 默认 ``enabled``），而**思考模式
   下 ``temperature`` 不生效**。意图识别要的是稳定复现，开着思考模式等于
   把 ``temperature: 0`` 白设了，还更慢更贵。因此对 DeepSeek 默认发
   ``thinking: {"type": "disabled"}``。
2. **``max_tokens`` 不设时非思考模式默认 8K**，而候选输出不到 200 字节。
   显式设小值，既防截断也控成本。
3. **JSON 模式要求提示词里出现 ``json`` 字样并给出格式样例**，否则模型会
   一直吐空白直到撞上 token 上限，看起来像「卡住」。提示词里两者都有；
   另外文档明说 JSON 模式有概率返回空内容，所以空响应会重试一次。

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
DEFAULT_MAX_TOKENS = 512
# 正常候选不到 200 字节；给足余量，但仍要挡住异常巨大的响应体。
MAX_RESPONSE_BYTES = 256 * 1024
# 多数模型会用 ```json 包裹，剥掉再解析；这不是放宽校验，校验在后面。
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)
# 空响应是 DeepSeek JSON 模式已知的偶发现象，重试一次而不是直接判失败。
_EMPTY_RETRIES = 1

ENV_BASE_URL = "BANKAGENT_MODEL_BASE_URL"
ENV_API_KEY = "BANKAGENT_MODEL_API_KEY"
ENV_MODEL_NAME = "BANKAGENT_MODEL_NAME"
ENV_TIMEOUT = "BANKAGENT_MODEL_TIMEOUT"
ENV_MAX_TOKENS = "BANKAGENT_MODEL_MAX_TOKENS"
ENV_THINKING = "BANKAGENT_MODEL_THINKING"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL_NAME = "deepseek-flash"

_FORMAT_HINT = (
    "\n\n输出要求：只返回一个 json 对象，不要输出 Markdown、代码块、解释或多余字段。格式样例："
    '{"scenario": "transfer", "intent": "TRANSFER", '
    '"candidate_params": {"recipient_name": "张伟", "amount": "300"}}。'
    "无法识别时返回："
    '{"scenario": null, "intent": null, "candidate_params": {}}'
)

_RETRY = object()


class ProviderConfigError(RuntimeError):
    """配置本身有问题：缺项、URL 不合法、数值越界。启动时就该失败。"""


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_MODEL_NAME
    timeout: float = DEFAULT_TIMEOUT
    json_mode: bool = True
    max_tokens: int = DEFAULT_MAX_TOKENS
    # None 表示不发送 thinking 字段（非 DeepSeek 供应商可能不认识它）。
    thinking: str | None = None

    def __post_init__(self) -> None:
        if not self.base_url.startswith(("http://", "https://")):
            raise ProviderConfigError("base_url 必须以 http:// 或 https:// 开头")
        if not self.model.strip():
            raise ProviderConfigError("model 不能为空")
        if not self.api_key.strip():
            raise ProviderConfigError("api_key 不能为空")
        if not (0 < self.timeout <= 120):
            raise ProviderConfigError("timeout 必须在 0 到 120 秒之间")
        if not (1 <= self.max_tokens <= 393216):
            raise ProviderConfigError("max_tokens 必须在 1 到 393216 之间")
        if self.thinking not in (None, "enabled", "disabled"):
            raise ProviderConfigError("thinking 只能是 enabled、disabled 或留空")

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
        # 计费口径的调用统计。用途很具体：让「到底有没有真的调模型」这件事
        # 可以直接查，而不是靠 health() 猜——后者只反映「配置齐全 + 上次没失败」，
        # 从没调用过也返回 True。
        self._calls = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0
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

    def stats(self) -> dict[str, int]:
        """累计调用次数与供应商计的 token 数。

        ``calls`` 是**成功拿到响应**的次数（含重试后成功的）。它跟
        ``health()`` 的区别就在于：从没调用过时这里是 0，而 health 仍是 True。
        """
        return {"calls": self._calls, "prompt_tokens": self._prompt_tokens,
                "completion_tokens": self._completion_tokens}

    @property
    def last_error(self) -> str | None:
        """最近一次失败的技术原因，供冒烟脚本诊断。

        不进入任何对用户可见的文案：边界只报 MODEL_UNAVAILABLE，供应商
        细节（状态码、网络错误）留在这里给运维和调试看。
        """
        return self._last_error

    def predict(self, request: dict[str, Any]) -> Any:
        payload = self._payload(request)
        text_mode = request.get("format") == "text"
        for attempt in range(_EMPTY_RETRIES + 1):
            outcome = self._attempt(payload, text_mode=text_mode)
            if outcome is not _RETRY:
                return outcome
            if attempt < _EMPTY_RETRIES:
                # 空响应是供应商侧偶发问题，不算用户输入错误，也不记成故障。
                continue
        self._last_error = "empty"
        return None

    def close(self) -> None:
        self._client.close()

    # -- 内部 -------------------------------------------------------------

    def _attempt(self, payload: dict[str, Any], *, text_mode: bool = False) -> Any:
        """一次调用。返回候选 / ``None`` / ``_RETRY``；协议级问题抛异常。"""
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
            choice = body["choices"][0]
            content = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            self._last_error = "shape"
            raise RuntimeError("MODEL_RESPONSE_INVALID") from None

        # 撞上 max_tokens 时 content 是半截 JSON：解析必然失败，但那会用
        # 「请重新描述」误导用户——重述一次还是会截断。这是配置问题。
        if choice.get("finish_reason") == "length":
            self._last_error = "truncated"
            raise RuntimeError("MODEL_RESPONSE_TRUNCATED")

        if not isinstance(content, str):
            self._last_error = "content"
            raise RuntimeError("MODEL_RESPONSE_INVALID") from None

        if not content.strip():
            # 已知的 JSON 模式偶发空响应，交给调用方决定是否重试。
            return _RETRY

        self._last_error = None
        usage = body.get("usage")
        if isinstance(usage, dict):
            self._calls += 1
            self._prompt_tokens += usage.get("prompt_tokens") or 0
            self._completion_tokens += usage.get("completion_tokens") or 0
        # 措辞改写要的是纯文本。这里若也走 JSON 解析，正常回复会被当成
        # 解析失败，措辞层每次都静默回退模板——测试用替身时看不出来。
        if text_mode:
            return content.strip()
        return _extract_json(content)

    def _payload(self, request: dict[str, Any]) -> dict[str, Any]:
        """组装一次请求。同一个客户端承载两种任务，靠 ``format`` 区分。

        ``format="text"`` 是措辞改写：只给 facts，要纯文本；
        其余是意图识别：给 catalog/message/pending，要 JSON。
        """
        instruction = request.get("instruction") or ""
        text_mode = request.get("format") == "text"
        if text_mode:
            system = instruction
            body = {"facts": request.get("facts")}
        else:
            # 提示词里必须有 json 字样与格式样例，否则 JSON 模式会一直吐空白。
            system = instruction if "json" in instruction.lower() else instruction + _FORMAT_HINT
            body = {
                "catalog": request.get("catalog") or [],
                "message": request.get("message") or "",
                "pending": request.get("pending"),
            }
            # 有历史才带上：首轮请求体与改造前完全一致。
            if request.get("history"):
                body["history"] = request["history"]
        user = json.dumps(body, ensure_ascii=False)
        payload: dict[str, Any] = {
            "model": self._config.model,
            # 意图识别要稳定，温度压低。注意：思考模式下该参数不生效，
            # 所以对 DeepSeek 要同时关掉思考模式，否则这一行等于没写。
            "temperature": 0,
            # 候选很小；显式限制既防截断也控成本（DeepSeek 默认 8K）。
            "max_tokens": self._config.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self._config.json_mode and not text_mode:
            payload["response_format"] = {"type": "json_object"}
        if self._config.thinking is not None:
            payload["thinking"] = {"type": self._config.thinking}
        return payload


def _parse_timeout(raw: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ProviderConfigError("BANKAGENT_MODEL_TIMEOUT 必须是数字") from None
    if not (0 < value <= 120):
        raise ProviderConfigError("BANKAGENT_MODEL_TIMEOUT 必须在 0 到 120 秒之间")
    return value


def _parse_max_tokens(raw: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ProviderConfigError("BANKAGENT_MODEL_MAX_TOKENS 必须是整数") from None
    if not (1 <= value <= 393216):
        raise ProviderConfigError("BANKAGENT_MODEL_MAX_TOKENS 必须在 1 到 393216 之间")
    return value


def build_model_from_env(env: Mapping[str, str] | None = None) -> OpenAICompatibleModel | None:
    """按环境变量构建模型；全空返回 None（保持 offline）。

    只配了 ``api_key`` 而缺其它项时**抛错而不是返回 None**：这种情况几乎
    都是漏了某个变量，静默回退 offline 会让人以为模型已经在用。

    ``base_url`` 与 ``model`` 有默认值（DeepSeek 官方地址与 ``deepseek-flash``），
    所以最少只要设 ``BANKAGENT_MODEL_API_KEY`` 一项就能用。
    """
    source = os.environ if env is None else env
    base = (source.get(ENV_BASE_URL) or "").strip()
    key = (source.get(ENV_API_KEY) or "").strip()
    name = (source.get(ENV_MODEL_NAME) or "").strip()

    if not (base or key or name):
        return None

    if not key:
        raise ProviderConfigError(
            f"模型配置不完整，缺少：{ENV_API_KEY}。三个变量都留空才会使用 offline 模式。"
        )

    base = base or DEFAULT_BASE_URL
    name = name or DEFAULT_MODEL_NAME

    timeout = _parse_timeout((source.get(ENV_TIMEOUT) or "").strip() or str(DEFAULT_TIMEOUT))
    max_tokens = _parse_max_tokens(
        (source.get(ENV_MAX_TOKENS) or "").strip() or str(DEFAULT_MAX_TOKENS)
    )

    thinking = (source.get(ENV_THINKING) or "").strip().lower() or None
    if thinking is None and "deepseek.com" in base:
        # DeepSeek 的 thinking 默认开启，而思考模式下 temperature 不生效。
        # 意图识别不需要推理链，默认关掉；要改回来设 BANKAGENT_MODEL_THINKING=enabled。
        thinking = "disabled"

    return OpenAICompatibleModel(
        ProviderConfig(
            base_url=base,
            api_key=key,
            model=name,
            timeout=timeout,
            max_tokens=max_tokens,
            thinking=thinking,
        )
    )
