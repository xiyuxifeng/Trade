"""
DSL Executor — P4-017。

执行编译后的 DSL 规则，提供更高级的执行控制能力。

与 dsl_compiler.py 的区别：
- Compiler: ConditionExpr → CompiledRule（编译时）
- Executor: 执行 CompiledRule，支持生命周期、优先级、回调、批处理等

功能：
1. 规则生命周期管理（启用/禁用）
2. 规则优先级排序
3. 执行回调钩子（on_match, on_no_match, on_error）
4. 短路执行（early termination）
5. 规则组和冲突处理
6. 执行指标收集
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from src.persona.dsl import ActionSpec
from src.persona.dsl_compiler import CompiledRule, ExecutionResult, StateAccessor


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RuleState(Enum):
    """规则状态。"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    SUSPENDED = "suspended"  # 临时禁用（如风控拦截后）


class ExecutionMode(Enum):
    """执行模式。"""
    ALL = "all"       # 执行所有规则
    FIRST = "first"   # 短路：遇到第一个匹配就停止
    BEST = "best"     # 返回评分最高的规则


# ---------------------------------------------------------------------------
# Execution Events
# ---------------------------------------------------------------------------

@dataclass
class RuleEvent:
    """规则执行事件。"""
    rule: CompiledRule
    matched: bool
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict | None = None


@dataclass
class ExecutionSummary:
    """执行摘要。"""
    total: int
    matched: int
    failed: int
    duration_ms: float
    events: list[RuleEvent]


# ---------------------------------------------------------------------------
# Rule Registry
# ---------------------------------------------------------------------------

class RuleRegistry:
    """规则注册表，管理规则的启用/禁用状态和优先级。

    用法：
        registry = RuleRegistry()
        registry.register(rule, priority=1, enabled=True)
        registry.enable("rule_id")
        registry.disable("rule_id")
    """

    def __init__(self) -> None:
        self._rules: dict[str, CompiledRule] = {}
        self._priorities: dict[str, int] = {}
        self._states: dict[str, RuleState] = {}

    def register(
        self,
        rule: CompiledRule,
        priority: int = 0,
        enabled: bool = True,
    ) -> None:
        """注册规则。

        Args:
            rule: 编译后的规则
            priority: 优先级（数值越大越先执行）
            enabled: 是否启用
        """
        self._rules[rule.rule_id] = rule
        self._priorities[rule.rule_id] = priority
        self._states[rule.rule_id] = RuleState.ENABLED if enabled else RuleState.DISABLED

    def unregister(self, rule_id: str) -> None:
        """注销规则。"""
        self._rules.pop(rule_id, None)
        self._priorities.pop(rule_id, None)
        self._states.pop(rule_id, None)

    def get(self, rule_id: str) -> CompiledRule | None:
        """获取规则。"""
        return self._rules.get(rule_id)

    def get_all(self) -> list[CompiledRule]:
        """获取所有规则（按优先级排序）。"""
        sorted_ids = sorted(
            self._rules.keys(),
            key=lambda rid: self._priorities.get(rid, 0),
            reverse=True,
        )
        return [self._rules[rid] for rid in sorted_ids]

    def get_enabled(self) -> list[CompiledRule]:
        """获取所有启用的规则（按优先级排序）。"""
        enabled_ids = [
            rid for rid, state in self._states.items()
            if state == RuleState.ENABLED
        ]
        sorted_ids = sorted(
            enabled_ids,
            key=lambda rid: self._priorities.get(rid, 0),
            reverse=True,
        )
        return [self._rules[rid] for rid in sorted_ids]

    def enable(self, rule_id: str) -> None:
        """启用规则。"""
        if rule_id in self._states:
            self._states[rule_id] = RuleState.ENABLED

    def disable(self, rule_id: str) -> None:
        """禁用规则。"""
        if rule_id in self._states:
            self._states[rule_id] = RuleState.DISABLED

    def suspend(self, rule_id: str) -> None:
        """临时挂起规则。"""
        if rule_id in self._states:
            self._states[rule_id] = RuleState.SUSPENDED

    def is_enabled(self, rule_id: str) -> bool:
        """检查规则是否启用。"""
        return self._states.get(rule_id) == RuleState.ENABLED

    def get_state(self, rule_id: str) -> RuleState | None:
        """获取规则状态。"""
        return self._states.get(rule_id)


# ---------------------------------------------------------------------------
# Execution Hooks
# ---------------------------------------------------------------------------

@dataclass
class ExecutionHooks:
    """执行回调钩子。"""
    on_match: Callable[[CompiledRule, StateAccessor], None] | None = None
    on_no_match: Callable[[CompiledRule, StateAccessor], None] | None = None
    on_error: Callable[[CompiledRule, StateAccessor, Exception], None] | None = None
    on_execution_start: Callable[[list[CompiledRule], dict, dict], None] | None = None
    on_execution_end: Callable[[ExecutionSummary], None] | None = None


# ---------------------------------------------------------------------------
# DSL Executor
# ---------------------------------------------------------------------------

class DSLExecutor:
    """DSL 执行引擎。

    提供高级的规则执行能力，包括生命周期管理、优先级、回调钩子等。

    用法：
        executor = DSLExecutor(registry)
        executor.register_hook(on_match=lambda r, _: print(f"Matched: {r.name}"))

        # 执行所有规则
        summary = executor.execute(state={"regime": "bullish"}, bar={"close": 100.0})

        # 短路执行
        result = executor.execute_first(state={"regime": "bullish"}, bar={})

        # 获取匹配的规则
        matched = executor.filter_matching(state={}, bar={})
    """

    def __init__(
        self,
        registry: RuleRegistry | None = None,
        hooks: ExecutionHooks | None = None,
    ):
        self._registry = registry or RuleRegistry()
        self._hooks = hooks or ExecutionHooks()

    @property
    def registry(self) -> RuleRegistry:
        """获取规则注册表。"""
        return self._registry

    def execute(
        self,
        state: dict | None = None,
        bar: dict | None = None,
        rule_ids: list[str] | None = None,
    ) -> ExecutionSummary:
        """执行所有启用的规则。

        Args:
            state: 市场状态
            bar: K线数据
            rule_ids: 可选，指定要执行的规则ID列表

        Returns:
            执行摘要
        """
        start_time = datetime.now()
        rules = self._registry.get_enabled()

        if rule_ids:
            rules = [r for r in rules if r.rule_id in rule_ids]

        events: list[RuleEvent] = []
        matched_count = 0
        failed_count = 0

        if self._hooks.on_execution_start:
            self._hooks.on_execution_start(rules, state or {}, bar or {})

        for rule in rules:
            rule_event = self._execute_rule(rule, state, bar)
            events.append(rule_event)
            if rule_event.matched:
                matched_count += 1
            else:
                failed_count += 1

        duration = (datetime.now() - start_time).total_seconds() * 1000

        summary = ExecutionSummary(
            total=len(rules),
            matched=matched_count,
            failed=failed_count,
            duration_ms=duration,
            events=events,
        )

        if self._hooks.on_execution_end:
            self._hooks.on_execution_end(summary)

        return summary

    def execute_first(
        self,
        state: dict | None = None,
        bar: dict | None = None,
        rule_ids: list[str] | None = None,
    ) -> RuleEvent | None:
        """短路执行：遇到第一个匹配就停止。

        Args:
            state: 市场状态
            bar: K线数据
            rule_ids: 可选，指定要执行的规则ID列表

        Returns:
            第一个匹配的规则事件，如果没有匹配返回 None
        """
        rules = self._registry.get_enabled()

        if rule_ids:
            rules = [r for r in rules if r.rule_id in rule_ids]

        for rule in rules:
            rule_event = self._execute_rule(rule, state, bar)
            if rule_event.matched:
                return rule_event

        return None

    def filter_matching(
        self,
        state: dict | None = None,
        bar: dict | None = None,
        rule_type: str | None = None,
        rule_ids: list[str] | None = None,
    ) -> list[CompiledRule]:
        """获取所有匹配的规则。

        Args:
            state: 市场状态
            bar: K线数据
            rule_type: 可选，按规则类型过滤
            rule_ids: 可选，指定要检查的规则ID列表

        Returns:
            匹配的规则列表
        """
        rules = self._registry.get_enabled()

        if rule_ids:
            rules = [r for r in rules if r.rule_id in rule_ids]

        matched = []
        for rule in rules:
            if rule_type and rule.rule_type != rule_type:
                continue
            try:
                if rule.matches(state=state, bar=bar):
                    matched.append(rule)
            except Exception:
                continue

        return matched

    def execute_rule(
        self,
        rule_id: str,
        state: dict | None = None,
        bar: dict | None = None,
    ) -> RuleEvent:
        """执行指定规则。

        Args:
            rule_id: 规则ID
            state: 市场状态
            bar: K线数据

        Returns:
            规则事件
        """
        rule = self._registry.get(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")
        return self._execute_rule(rule, state, bar)

    def _execute_rule(
        self,
        rule: CompiledRule,
        state: dict | None,
        bar: dict | None,
    ) -> RuleEvent:
        """执行单个规则。"""
        accessor = StateAccessor(state=state or {}, bar=bar or {})

        try:
            matched = rule.condition_fn(accessor)
        except Exception as e:
            if self._hooks.on_error:
                self._hooks.on_error(rule, accessor, e)
            matched = False

        event = RuleEvent(rule=rule, matched=matched, context={"state": state, "bar": bar})

        if matched:
            if self._hooks.on_match:
                self._hooks.on_match(rule, accessor)
        else:
            if self._hooks.on_no_match:
                self._hooks.on_no_match(rule, accessor)

        return event

    def get_metrics(self) -> dict[str, Any]:
        """获取执行指标。"""
        return {
            "total_rules": len(self._registry._rules),
            "enabled_rules": len([
                s for s in self._registry._states.values()
                if s == RuleState.ENABLED
            ]),
            "disabled_rules": len([
                s for s in self._registry._states.values()
                if s == RuleState.DISABLED
            ]),
        }


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def create_executor(
    rules: list[CompiledRule],
    hooks: ExecutionHooks | None = None,
) -> tuple[DSLExecutor, RuleRegistry]:
    """快捷创建执行器并注册规则。

    Args:
        rules: 编译后的规则列表
        hooks: 执行回调钩子

    Returns:
        (执行器, 注册表) 元组
    """
    registry = RuleRegistry()
    executor = DSLExecutor(registry=registry, hooks=hooks)

    for rule in rules:
        registry.register(rule)

    return executor, registry
