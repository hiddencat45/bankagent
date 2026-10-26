"""有据润色：让模型只决定「怎么说」，不决定「发生了什么」。

各场景的 ``render`` 已经依据后端结果写出一段**事实正确**的文案。这一层把它
交给模型改写得更自然，然后校验模型没有编造数字。

为什么是「改写」而不是「生成」：如果让模型看着数据直接写回复，它就有机会
把失败说成成功——在银行语境里这比不回复更危险。改写时原文已经是对的，模型
能改变的只有措辞，幻觉空间被压到最小。校验不过一律回退原文。

没配置模型（offline）时这一层完全直通，行为与改造前一致。
"""

from __future__ import annotations

import re
from typing import Any

# 面向用户的文案里不该出现实体标识；交给模型之前先剥离。
_ID_KEYS = frozenset({
    "card_id", "subscription_id", "transaction_id", "account_id",
    "contact_id", "user_id", "authorization_ref", "challenge_id",
})

_INSTRUCTION = """你是银行客服的措辞改写助手。输入里有一段已经核实过的回复原文
（reference_text），把它改写成自然、简洁、口语化的中文。

规则：
1. 不得改变任何数字、金额、日期、状态或实体名称；
2. 不得新增原文没有的事实、原因、承诺或建议；
3. 不得删除原文中的金额和状态；
4. 不要礼貌套话（"您好""感谢咨询"），直接说事；
5. 不要解释你做了什么，不要加引号或 Markdown；
6. 只输出改写后的中文正文。

reference_text 是唯一事实来源，facts 只用来理解上下文。"""

# 改写结果的合理长度区间（相对原文）。太短说明丢了信息，太长说明在发挥。
_MIN_RATIO = 0.35
_MAX_RATIO = 3.0
# 太短的文案改写收益低、风险高，直接不送模型。
_MIN_LENGTH = 12

_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _strip_ids(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_ids(v) for k, v in value.items() if k not in _ID_KEYS}
    if isinstance(value, list):
        return [_strip_ids(v) for v in value]
    return value


def _numbers(text: str) -> set[float]:
    """按数值比较而不是按字面：``25.00`` 与 ``25``、``1000.00`` 与 ``1000`` 视为同一个数。"""
    found: set[float] = set()
    for literal in _NUMBER.findall(text):
        try:
            found.add(float(literal))
        except ValueError:  # 超长数字串，当作不可比较
            continue
    return found


def _facts(result: dict[str, Any], reference: str) -> dict[str, Any]:
    """只把脱敏后的事实交给模型：原文、操作名、状态、错误码、业务数据。"""
    return {
        "reference_text": reference,
        "operation": result.get("operation"),
        "status": result.get("status"),
        "error_code": result.get("error_code"),
        "data": _strip_ids(result.get("data")),
    }


class ResponsePhraser:
    """把已核实的结果改写成自然语言；任何不确定都回退原模板。"""

    def __init__(self, model: Any = None):
        self.model = model
        self._rewritten = 0
        self._fallback = 0

    def phrase(self, result: dict[str, Any], reference: str | None) -> str:
        if not reference:
            return ""
        if self.model is None or len(reference) < _MIN_LENGTH:
            return reference

        try:
            text = self.model.predict({
                "instruction": _INSTRUCTION,
                "facts": _facts(result, reference),
                "format": "text",
            })
        except Exception:
            self._fallback += 1
            return reference

        if not isinstance(text, str):
            self._fallback += 1
            return reference

        text = text.strip()
        if not self._acceptable(text, reference):
            self._fallback += 1
            return reference

        self._rewritten += 1
        return text

    @staticmethod
    def _acceptable(text: str, reference: str) -> bool:
        """三条硬约束：非空、数字不得是原文之外的、长度在合理区间。

        数字用子集校验：改写可以说得更口语，但不许出现原文没有的金额。
        反过来，原文的每个数字都不强制保留——润色时省略次要数字是正常的，
        金额与状态由第 4 条提示词约束。
        """
        if not text:
            return False
        if not _numbers(text) <= _numbers(reference):
            return False
        return len(reference) * _MIN_RATIO <= len(text) <= len(reference) * _MAX_RATIO

    def stats(self) -> dict[str, int]:
        """给测试与排查用：改写成功与被回退的次数。"""
        return {"rewritten": self._rewritten, "fallback": self._fallback}
