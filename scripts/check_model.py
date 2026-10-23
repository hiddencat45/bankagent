"""真实模型冒烟检查：填好 key 后跑一次，确认能拿到合法候选。

默认按 DeepSeek 调好，最少只要一个 key：

    $env:BANKAGENT_MODEL_API_KEY = "<你的 key>"
    python scripts/check_model.py

想换地址或模型再加：

    $env:BANKAGENT_MODEL_BASE_URL = "https://api.deepseek.com"
    $env:BANKAGENT_MODEL_NAME     = "deepseek-v4-pro"

它刻意只做**观测**，不判定对错：模型能不能正确理解同义表达、会不会在无关
问题上乱答，需要人看一眼输出再决定。脚本给的是证据，不是结论。

三个检查项对应三种能力：

1. 明确指令 → 能否识别出正确场景与槽位
2. 换个说法 → 同义表达能否理解（这是关键词规则做不到的）
3. 无关问题 → 会不会凭空编一个业务意图（拒识能力）

任何一项不理想都不代表接入失败，但**第三项编造意图**属于安全问题：
那会让无关闲聊变成一笔写操作的前半段。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "preparaion"))

from agent_understanding import CandidateInterpreter, UnderstandingError  # noqa: E402
from model_providers import (  # noqa: E402
    ENV_API_KEY,
    ENV_BASE_URL,
    ENV_MODEL_NAME,
    ProviderConfigError,
    build_model_from_env,
)
from scenarios import REGISTRY  # noqa: E402

CASES = [
    ("明确指令", "给张伟转 300 元"),
    ("同义表达", "帮我把这个月的房租两千五打给张伟"),
    ("无关问题", "今天天气怎么样"),
]


def main() -> int:
    try:
        model = build_model_from_env()
    except ProviderConfigError as exc:
        print(f"[配置错误] {exc}")
        return 1

    if model is None:
        print("未配置模型，当前会用 offline 关键词规则。要验收真实模型，至少设置：")
        print(f"  {ENV_API_KEY}=<你的 key>")
        print()
        print("可选（已按 DeepSeek 配好默认值）：")
        print(f"  {ENV_BASE_URL}=https://api.deepseek.com")
        print(f"  {ENV_MODEL_NAME}=deepseek-flash")
        return 1

    config = model._config
    print(f"供应商地址：{config.base_url}")
    print(f"模型名称：{config.model}")
    # 凭据只报长度，不回显。
    print(f"凭据：已设置（{len(config.api_key)} 字符）")
    print(f"输出上限：{config.max_tokens} tokens")
    # DeepSeek 的 thinking 默认开启，而思考模式下 temperature 不生效。
    print(f"思考模式：{config.thinking or '不发送该字段'}")
    print()

    interpreter = CandidateInterpreter(model, REGISTRY)

    failures = 0
    for label, message in CASES:
        started = time.monotonic()
        try:
            prediction = interpreter.predict(message, None)
        except UnderstandingError as exc:
            elapsed = (time.monotonic() - started) * 1000
            print(f"[{label}] {message}")
            print(f"  失败：{exc.code}  （{elapsed:.0f} ms）")
            # 边界对用户只报 MODEL_UNAVAILABLE；真正原因（状态码/网络）在这里。
            if model.last_error:
                print(f"  技术原因：{model.last_error}")
            failures += 1
            print()
            continue

        elapsed = (time.monotonic() - started) * 1000
        print(f"[{label}] {message}")
        print(f"  耗时：{elapsed:.0f} ms")
        if prediction["scenario"] is None:
            print("  候选：空（未识别出业务意图）")
        else:
            print(f"  候选：{prediction['scenario']} / {prediction['intent']}"
                  f" / {prediction['candidate_params']}")
        print()

    print(f"健康状态：{'ok' if interpreter.health() else 'unavailable'}")
    if failures:
        print(f"有 {failures} 项在协议层就失败了，先看错误码再判断是配置问题还是模型问题。")
        print("  MODEL_RESPONSE_TRUNCATED → 调大 BANKAGENT_MODEL_MAX_TOKENS")
        print("  MODEL_HTTP_401           → key 无效或过期")
        print("  MODEL_TIMEOUT            → 网络问题，或调大 BANKAGENT_MODEL_TIMEOUT")
    else:
        print("协议层全部通过。语义是否达标请对照上面的候选人工判断：")
        print("  · 第 2 项应能识别出 TRANSFER，并尽量抽出金额与收款人")
        print("  · 第 3 项应当是空候选；若给出了业务意图，属于安全隐患，应换模型或加提示词约束")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
