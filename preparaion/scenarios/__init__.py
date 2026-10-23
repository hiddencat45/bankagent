"""场景注册器：发现场景模块、校验声明、提供受控分发。

本模块是 A 的公共层，按《阶段0-接口草案》§2 与《场景扩展与分工》§4 实现：

- 自动发现 ``scenarios/`` 下的场景模块，但**启用前**必须通过声明校验；
- 不同场景不得抢占同一 ``operation`` 名；同场景多意图可映射同一操作，
  但安全声明（``effect`` / ``risk``）必须一致；
- 白名单来自通过校验且已启用的声明，公共层还要验证 operation 属于当前场景，
  **不能凭候选参数指定任意函数**；
- 关键词只是离线规则模式的识别策略，收集全部命中候选，**不按文件名顺序取第一个**；
- 未实现后端不得作为可用能力暴露，``NotImplementedError`` 不能被转成成功。

异常边界：``resolve`` 钩子内部可能抛出受控拒绝（例如 B 的 ``find_contacts``
在归属失败时抛 ``PermissionError``）。本模块在**公共边界统一捕获**并转成
当前操作的 ``REJECTED`` / ``ACCOUNT_NOT_ACCESSIBLE``，不让每个场景重复
try/except，也绝不把「无权访问」伪装成「没有联系人」。
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Callable, Iterable

from bank_types import (
    BackendResult,
    Effect,
    IntentSpec,
    RiskLevel,
    TrustedContext,
)

__all__ = [
    "ScenarioSpec",
    "ScenarioError",
    "ScenarioDeclarationError",
    "ScenarioRegistry",
    "build_registry",
    "REGISTRY",
]

# 允许的风险等级与效果取值。声明里出现其它值属于配置错误，必须阻止启用。
_VALID_EFFECTS: frozenset[str] = frozenset({"READ", "WRITE"})
_VALID_RISKS: frozenset[str] = frozenset({"GREEN", "YELLOW", "RED", "DENY"})

# 场景模块必须提供的属性。
_REQUIRED_ATTRS: tuple[str, ...] = ("SCENARIO", "INTENTS", "execute", "render")

# 场景模块可选提供的钩子。
_OPTIONAL_HOOKS: tuple[str, ...] = (
    "resolve",
    "validate",
    "risk",
    "confirmation",
    "CLARIFY_LABELS",
)

# 风险等级的高低顺序，用于「只能升高」的比较。
_RISK_ORDER: dict[str, int] = {"GREEN": 0, "YELLOW": 1, "RED": 2, "DENY": 3}


class ScenarioError(Exception):
    """场景运行期错误基类。"""


class ScenarioDeclarationError(ScenarioError):
    """场景声明非法：配置错误，必须阻止启用，不能静默跳过。"""


class ScenarioSpec:
    """一个已通过校验的场景声明。

    只保存声明与钩子引用，不保存任何业务状态；业务事实始终来自后端。
    """

    __slots__ = (
        "name",
        "module",
        "intents",
        "execute",
        "render",
        "resolve",
        "validate",
        "risk",
        "confirmation",
        "clarify_labels",
    )

    def __init__(self, name: str, module: Any) -> None:
        self.name = name
        self.module = module
        self.intents: dict[str, IntentSpec] = module.INTENTS
        self.execute: Callable[..., Any] = module.execute
        self.render: Callable[..., str] = module.render
        self.resolve: Callable[..., dict] | None = getattr(module, "resolve", None)
        self.validate: Callable[..., bool] | None = getattr(module, "validate", None)
        self.risk: Callable[..., str] | None = getattr(module, "risk", None)
        # 确认卡展示字段由场景自己决定：server 只负责序列化，不需要按 operation
        # 写死分支。返回 None 表示该场景没有额外展示字段。
        self.confirmation: Callable[..., dict] | None = getattr(module, "confirmation", None)
        self.clarify_labels: dict[str, str] = getattr(module, "CLARIFY_LABELS", {}) or {}

    # -- 声明查询 ---------------------------------------------------------

    def operations(self) -> set[str]:
        """本场景声明的全部 operation 名。"""
        return {spec["operation"] for spec in self.intents.values()}

    def intent_for_operation(self, operation: str) -> str | None:
        """反查某个 operation 对应的意图名（同一 operation 可能对应多个意图）。"""
        for name, spec in self.intents.items():
            if spec["operation"] == operation:
                return name
        return None

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return f"<ScenarioSpec {self.name!r} intents={sorted(self.intents)}>"


class ScenarioRegistry:
    """已启用场景的注册表。

    构造时完成全部校验；任何一个场景声明非法都会抛
    ``ScenarioDeclarationError``，**不会**带着坏声明继续运行。
    """

    def __init__(self, specs: Iterable[ScenarioSpec]) -> None:
        self._by_name: dict[str, ScenarioSpec] = {}
        self._operation_owner: dict[str, str] = {}
        self._intent_index: dict[tuple[str, str], IntentSpec] = {}

        for spec in specs:
            self._register(spec)

        if not self._by_name:
            raise ScenarioDeclarationError("没有可用的场景声明")

        # 白名单只来自通过校验且已启用的声明。
        self.allowed_operations: frozenset[str] = frozenset(self._operation_owner)

    # -- 注册与校验 -------------------------------------------------------

    def _register(self, spec: ScenarioSpec) -> None:
        name = spec.name
        if not isinstance(name, str) or not name.strip():
            raise ScenarioDeclarationError("SCENARIO 必须是非空字符串")
        if name in self._by_name:
            raise ScenarioDeclarationError(f"场景名重复：{name!r}")

        if not isinstance(spec.intents, dict) or not spec.intents:
            raise ScenarioDeclarationError(f"场景 {name!r} 的 INTENTS 必须是非空 dict")

        for intent_name, intent_spec in spec.intents.items():
            self._validate_intent(name, intent_name, intent_spec)

            operation = intent_spec["operation"]
            owner = self._operation_owner.get(operation)
            if owner is not None and owner != name:
                # 不同场景抢占同一操作名是明确禁止的。
                raise ScenarioDeclarationError(
                    f"操作 {operation!r} 已被场景 {owner!r} 占用，"
                    f"场景 {name!r} 不得重复声明"
                )
            self._operation_owner[operation] = name
            self._intent_index[(name, intent_name)] = intent_spec

        # 同一场景内，同一 operation 的多意图必须安全声明一致。
        by_operation: dict[str, list[IntentSpec]] = {}
        for intent_spec in spec.intents.values():
            by_operation.setdefault(intent_spec["operation"], []).append(intent_spec)
        for operation, group in by_operation.items():
            effects = {item["effect"] for item in group}
            risks = {item["risk"] for item in group}
            if len(effects) > 1:
                raise ScenarioDeclarationError(
                    f"场景 {name!r} 的 {operation!r} 多个意图声明了不同 effect：{sorted(effects)}"
                )
            if len(risks) > 1:
                raise ScenarioDeclarationError(
                    f"场景 {name!r} 的 {operation!r} 多个意图声明了不同 risk：{sorted(risks)}"
                )

        self._by_name[name] = spec

    def _validate_intent(self, scenario: str, intent_name: str, spec: Any) -> None:
        where = f"场景 {scenario!r} 的意图 {intent_name!r}"
        if not isinstance(spec, dict):
            raise ScenarioDeclarationError(f"{where} 必须是 dict")

        for key in ("keywords", "slots", "required", "operation", "effect", "risk"):
            if key not in spec:
                raise ScenarioDeclarationError(f"{where} 缺少必需键 {key!r}")

        if not isinstance(spec["operation"], str) or not spec["operation"].strip():
            raise ScenarioDeclarationError(f"{where} 的 operation 必须是非空字符串")

        effect = spec["effect"]
        if effect not in _VALID_EFFECTS:
            raise ScenarioDeclarationError(
                f"{where} 的 effect 非法：{effect!r}，允许 {sorted(_VALID_EFFECTS)}"
            )

        risk = spec["risk"]
        if risk not in _VALID_RISKS:
            raise ScenarioDeclarationError(
                f"{where} 的 risk 非法：{risk!r}，允许 {sorted(_VALID_RISKS)}"
            )

        # READ 才能是 GREEN；WRITE 至少 YELLOW。这是公共层的硬规则，
        # 不能靠场景自觉声明。
        if effect == "READ" and risk != "GREEN":
            raise ScenarioDeclarationError(
                f"{where} 是 READ 却声明 risk={risk!r}；只读操作只能是 GREEN"
            )
        if effect == "WRITE" and risk == "GREEN":
            raise ScenarioDeclarationError(
                f"{where} 是 WRITE 却声明 risk='GREEN'；写操作至少 YELLOW"
            )

        if not isinstance(spec["keywords"], list):
            raise ScenarioDeclarationError(f"{where} 的 keywords 必须是 list")
        if not isinstance(spec["slots"], dict):
            raise ScenarioDeclarationError(f"{where} 的 slots 必须是 dict")
        if not isinstance(spec["required"], list):
            raise ScenarioDeclarationError(f"{where} 的 required 必须是 list")
        for slot in spec["required"]:
            if slot not in spec["slots"]:
                raise ScenarioDeclarationError(
                    f"{where} 的 required 含未声明槽位 {slot!r}"
                )

    # -- 查询 -------------------------------------------------------------

    def get(self, scenario: str) -> ScenarioSpec:
        spec = self._by_name.get(scenario)
        if spec is None:
            raise ScenarioError(f"未知场景：{scenario!r}")
        return spec

    def scenario_names(self) -> list[str]:
        return sorted(self._by_name)

    def specs(self) -> list[ScenarioSpec]:
        return [self._by_name[name] for name in sorted(self._by_name)]

    def spec_for_operation(self, operation: str) -> "ScenarioSpec | None":
        """按 operation 反查场景。

        确认卡投影需要它：挑战记录里只有 ``operation`` 与已绑定 ``params``，
        没有场景名。找不到返回 ``None`` 而不是抛异常——投影失败不该把一次
        已经通过风控的确认变成系统故障。
        """
        for name in sorted(self._by_name):
            spec = self._by_name[name]
            if operation in spec.operations():
                return spec
        return None

    # -- 意图识别（离线规则模式）------------------------------------------

    def match_intents(self, message: str) -> list[tuple[str, str, int]]:
        """收集**全部**关键词命中的候选，不按文件名顺序取第一个。

        返回 ``[(scenario, intent, hit_count)]``，按命中词数降序；
        调用方遇到不同 operation 同时命中时应澄清，而不是猜一个。
        """
        if not isinstance(message, str) or not message.strip():
            return []

        hits: list[tuple[str, str, int]] = []
        for spec in self.specs():
            for intent_name, intent_spec in spec.intents.items():
                count = sum(
                    1 for word in intent_spec["keywords"]
                    if isinstance(word, str) and word and word in message
                )
                if count:
                    hits.append((spec.name, intent_name, count))

        hits.sort(key=lambda item: (-item[2], item[0], item[1]))
        return hits

    # -- 受控分发 ---------------------------------------------------------

    def resolve_params(
        self,
        scenario: str,
        candidate_params: dict[str, Any],
        context: TrustedContext,
    ) -> dict[str, Any]:
        """调用场景的 ``resolve`` 钩子，并在公共边界统一处理受控拒绝。

        这是 B 在 PR #9/#10 交接里要求的边界：``find_contacts`` 归属失败会抛
        ``PermissionError``，本方法把它转成当前操作的 REJECTED /
        ACCOUNT_NOT_ACCESSIBLE，**不让每个场景重复捕获**，也绝不把无权访问
        伪装成「没有联系人」。
        """
        spec = self.get(scenario)
        if spec.resolve is None:
            return dict(candidate_params or {})

        try:
            resolved = spec.resolve(dict(candidate_params or {}), context)
        except PermissionError as exc:
            raise ScenarioError("ACCOUNT_NOT_ACCESSIBLE") from exc
        except ValueError as exc:
            raise ScenarioError("INVALID_PARAMS") from exc

        if not isinstance(resolved, dict):
            raise ScenarioError("INVALID_PARAMS")
        return resolved

    def check_operation(self, scenario: str, operation: str) -> None:
        """确认 operation 属于该场景，且在白名单内。

        模型或候选参数都不能指定任意函数名，因此这里是防线的关键一环。
        """
        spec = self.get(scenario)
        if operation not in spec.operations():
            raise ScenarioError(
                f"操作 {operation!r} 不属于场景 {scenario!r}；"
                f"该场景声明的是 {sorted(spec.operations())}"
            )
        if operation not in self.allowed_operations:
            raise ScenarioError(f"操作 {operation!r} 不在白名单内")

    def risk_floor(self, scenario: str, operation: str) -> RiskLevel:
        """取该操作声明的静态最低风险。"""
        spec = self.get(scenario)
        for intent_spec in spec.intents.values():
            if intent_spec["operation"] == operation:
                return intent_spec["risk"]  # type: ignore[return-value]
        raise ScenarioError(f"操作 {operation!r} 未在场景 {scenario!r} 中声明")

    def effect_of(self, scenario: str, operation: str) -> Effect:
        spec = self.get(scenario)
        for intent_spec in spec.intents.values():
            if intent_spec["operation"] == operation:
                return intent_spec["effect"]  # type: ignore[return-value]
        raise ScenarioError(f"操作 {operation!r} 未在场景 {scenario!r} 中声明")

    def evaluate_risk(
        self,
        scenario: str,
        operation: str,
        params: dict[str, Any],
        context: TrustedContext,
    ) -> RiskLevel:
        """合并静态声明与场景钩子，结果**只能升高不能降低**。

        场景钩子返回非法或缺失值属于配置错误，必须阻止执行（抛
        ``ScenarioDeclarationError``），不能当作 GREEN 放行。
        """
        spec = self.get(scenario)
        floor = self.risk_floor(scenario, operation)

        if spec.risk is None:
            return floor

        raised = spec.risk(operation, params, context)
        if raised not in _VALID_RISKS:
            raise ScenarioDeclarationError(
                f"场景 {scenario!r} 的 risk 钩子返回非法值 {raised!r}"
            )
        if _RISK_ORDER[raised] < _RISK_ORDER[floor]:
            raise ScenarioDeclarationError(
                f"场景 {scenario!r} 的 risk 钩子试图把 {floor} 降到 {raised}；"
                "风险只能升高"
            )
        return raised  # type: ignore[return-value]

    def execute(
        self,
        scenario: str,
        operation: str,
        params: dict[str, Any],
        context: TrustedContext,
    ) -> BackendResult:
        """受控执行：先校验 operation 归属，再调用场景 ``execute``。

        场景的 ``execute`` 只负责分发到后端并返回统一结果，不修改账户状态。
        受控拒绝统一转成 REJECTED；未实现的后端必须明确失败，
        **不能**把 ``NotImplementedError`` 转成成功。
        """
        self.check_operation(scenario, operation)
        spec = self.get(scenario)

        try:
            result = spec.execute(operation, params, context)
        except PermissionError as exc:
            return _rejected(operation, "ACCOUNT_NOT_ACCESSIBLE", exc)
        except NotImplementedError as exc:
            return _rejected(operation, "NOT_IMPLEMENTED", exc)

        return self._normalize_result(operation, result)

    def _normalize_result(self, operation: str, result: Any) -> BackendResult:
        """校验后端/场景返回值形状，避免坏结果流入上层。"""
        if not isinstance(result, dict):
            raise ScenarioError(f"操作 {operation!r} 的 execute 必须返回 dict")

        status = result.get("status")
        if status not in {"COMPLETED", "REJECTED", "FAILED", "PENDING"}:
            raise ScenarioError(f"操作 {operation!r} 返回了非法 status：{status!r}")

        error_code = result.get("error_code")
        data = result.get("data")
        if status == "COMPLETED":
            if error_code is not None:
                raise ScenarioError(
                    f"操作 {operation!r} 状态 COMPLETED 但 error_code 非空"
                )
        elif status in {"REJECTED", "FAILED"} and not error_code:
            # 失败必须可解释，否则上层无法区分「业务拒绝」与「意外故障」。
            raise ScenarioError(f"操作 {operation!r} 状态 {status} 但缺少 error_code")

        return {
            "operation": result.get("operation", operation),
            "status": status,
            "data": data,
            "error_code": error_code,
        }

    def render(self, scenario: str, result: BackendResult) -> str:
        """调用场景 ``render``，失败或处理中不得显示成功。"""
        spec = self.get(scenario)
        text = spec.render(result)
        if not isinstance(text, str):
            raise ScenarioError(f"场景 {scenario!r} 的 render 必须返回 str")
        return text


def _rejected(operation: str, error_code: str, exc: BaseException) -> BackendResult:
    """把受控异常转成结构化拒绝；异常本身只作为因果链保留，不外泄给用户。"""
    del exc  # 只用于 __cause__，不进结果
    return {
        "operation": operation,
        "status": "REJECTED",
        "data": None,
        "error_code": error_code,
    }


def _iter_scenario_modules() -> Iterable[Any]:
    """枚举当前包下的场景模块，跳过私有模块与注册器自身。"""
    package = importlib.import_module(__name__)
    for info in pkgutil.iter_modules(package.__path__):
        if info.name.startswith("_"):
            continue
        yield importlib.import_module(f"{__name__}.{info.name}")


def build_registry(modules: Iterable[Any] | None = None) -> ScenarioRegistry:
    """发现并校验场景，构造注册表。

    ``modules`` 为空时自动发现 ``scenarios/`` 下所有非私有模块。
    任何一个场景缺必需属性都会抛 ``ScenarioDeclarationError``——
    未实现的场景不能静默变成一个「不可用但看不见」的空壳。
    """
    specs: list[ScenarioSpec] = []
    for module in modules if modules is not None else _iter_scenario_modules():
        missing = [attr for attr in _REQUIRED_ATTRS if not hasattr(module, attr)]
        if missing:
            name = getattr(module, "__name__", repr(module))
            raise ScenarioDeclarationError(
                f"场景模块 {name} 缺少必需属性：{missing}"
            )
        specs.append(ScenarioSpec(module.SCENARIO, module))

    return ScenarioRegistry(specs)


# 模块级默认注册表：导入时即完成校验，坏声明会在启动阶段暴露而不是运行到一半才炸。
REGISTRY: ScenarioRegistry = build_registry()
