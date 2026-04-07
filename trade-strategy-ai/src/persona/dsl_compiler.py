"""
DSL Compiler — 策略 DSL 规则 → 可执行 Python 代码。

给定 ArticleStrategyRule / ArticlePrecondition，
编译为可调用函数：compiled_rule(state, bars) -> bool

Schema 版本: v1 (2026-04-07)
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Any, Callable

from src.persona.dsl import AND, ActionSpec, CMP, ConditionExpr, NOT, OR, TRUE, ConditionExpr
from src.persona.patterns import ArticlePattern, BasePattern, CanonicalPattern, PatternType
from src.persona.schemas import ArticlePrecondition, ArticleStrategyRule


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

_CMP_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "ge": operator.ge,
    "lt": operator.lt,
    "le": operator.le,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}


# ---------------------------------------------------------------------------
# State accessor
# ---------------------------------------------------------------------------

class StateAccessor:
    """从 MarketState 或 bar 数据中按 field path 取值。"""

    def __init__(self, state: dict | None = None, bar: dict | None = None) -> None:
        self._state = state or {}
        self._bar = bar or {}

    def get(self, field: str) -> Any:
        """按 field path 获取值。

        field 示例：
          - "regime"           → state['regime']
          - "volatility"       → state['volatility']
          - "close"            → bar['close']
          - "volume"           → bar['volume']
          - "ma20"             → bar 附带指标（如已预计算）
          - "rsi"              → 同上
        """
        # 先在 bar 中找
        if field in self._bar:
            return self._bar[field]
        # 再在 state 中找
        if field in self._state:
            return self._state[field]
        return None


# ---------------------------------------------------------------------------
# Condition compiler — ConditionExpr → callable
# ---------------------------------------------------------------------------


def compile_condition(expr: ConditionExpr) -> Callable[[StateAccessor], bool]:
    """将 ConditionExpr 编译为可执行函数。"""

    op = expr.op

    # ---- Leaf: cmp ----
    if op == "cmp":
        field = expr.field or ""
        cmp_fn = _CMP_OPS.get(expr.cmp or "")
        value = expr.value

        def _cmp(accessor: StateAccessor) -> bool:
            actual = accessor.get(field)
            if actual is None:
                return False
            try:
                return cmp_fn(actual, value)
            except (TypeError, ValueError):
                return False

        return _cmp

    # ---- Logical ----
    if op == "and":
        children = [compile_condition(arg) for arg in (expr.args or [])]
        return lambda acc: all(c(acc) for c in children)

    if op == "or":
        children = [compile_condition(arg) for arg in (expr.args or [])]
        return lambda acc: any(c(acc) for c in children)

    if op == "not":
        [child] = expr.args or []
        child_fn = compile_condition(child)
        return lambda acc: not child_fn(acc)

    # ---- Constants ----
    if op == "true":
        return lambda _acc: True

    if op == "false":
        return lambda _acc: False

    raise ValueError(f"Unknown ConditionExpr op: {op!r}")


# ---------------------------------------------------------------------------
# Compiled Rule
# ---------------------------------------------------------------------------


@dataclass
class CompiledRule:
    """编译后的规则，可反复调用。"""

    rule_id: str
    name: str
    rule_type: str  # entry / exit / filter / sizing / risk
    instrument_focus: str
    condition_fn: Callable[[StateAccessor], bool]
    action: ActionSpec
    params: dict[str, Any]
    confidence: float | None

    def matches(self, state: dict | None = None, bar: dict | None = None) -> bool:
        """评估规则是否在给定市场状态和K线bar下触发。"""
        accessor = StateAccessor(state=state, bar=bar)
        return self.condition_fn(accessor)

    def __repr__(self) -> str:
        return f"CompiledRule({self.rule_id}, {self.rule_type}, {self.name})"


# ---------------------------------------------------------------------------
# DSL Compiler — 入口
# ---------------------------------------------------------------------------


def compile_rule(
    rule: ArticleStrategyRule | ArticlePrecondition | ConditionExpr,
    *,
    rule_id: str | None = None,
    name: str | None = None,
) -> CompiledRule:
    """将 ArticleStrategyRule / ArticlePrecondition 编译为 CompiledRule。

    Args:
        rule: 要编译的规则对象
        rule_id: 可选，手动指定规则ID
        name: 可选，手动指定规则名称
    """

    if isinstance(rule, ArticleStrategyRule):
        return _compile_strategy_rule(rule, rule_id=rule_id, name=name)
    elif isinstance(rule, ArticlePrecondition):
        return _compile_precondition(rule, rule_id=rule_id, name=name)
    elif isinstance(rule, ConditionExpr):
        return _compile_condition_only(rule, rule_id=rule_id, name=name)
    else:
        raise TypeError(f"Cannot compile rule of type {type(rule).__name__}")


def _compile_strategy_rule(
    rule: ArticleStrategyRule,
    rule_id: str | None,
    name: str | None,
) -> CompiledRule:
    condition_fn = compile_condition(rule.condition)
    return CompiledRule(
        rule_id=rule_id or rule.claim_key.value,
        name=name or rule.claim_key.value,
        rule_type=rule.rule_type,
        instrument_focus=rule.instrument_focus.value,
        condition_fn=condition_fn,
        action=rule.action,
        params=rule.params,
        confidence=rule.confidence,
    )


def _compile_precondition(
    precond: ArticlePrecondition,
    rule_id: str | None,
    name: str | None,
) -> CompiledRule:
    condition_fn = compile_condition(precond.condition)
    return CompiledRule(
        rule_id=rule_id or f"precond_{precond.claim_key.value}",
        name=name or f"前置条件: {precond.claim_key.value}",
        rule_type="filter",
        instrument_focus=precond.instrument_focus.value,
        condition_fn=condition_fn,
        action=ActionSpec(type="filter"),
        params={},
        confidence=precond.confidence,
    )


def _compile_condition_only(
    expr: ConditionExpr,
    rule_id: str | None,
    name: str | None,
) -> CompiledRule:
    condition_fn = compile_condition(expr)
    return CompiledRule(
        rule_id=rule_id or "anonymous",
        name=name or "条件规则",
        rule_type="filter",
        instrument_focus="mixed",
        condition_fn=condition_fn,
        action=ActionSpec(type="filter"),
        params={},
        confidence=None,
    )


# ---------------------------------------------------------------------------
# DSL Executor — 批量执行
# ---------------------------------------------------------------------------


@dataclass
class ExecutionResult:
    """规则执行结果。"""
    rule: CompiledRule
    matched: bool
    state: dict | None
    bar: dict | None


def execute_rules(
    rules: list[CompiledRule],
    state: dict | None = None,
    bar: dict | None = None,
) -> list[ExecutionResult]:
    """在给定 state + bar 下执行一批规则。"""
    results = []
    for rule in rules:
        matched = rule.matches(state=state, bar=bar)
        results.append(ExecutionResult(rule=rule, matched=matched, state=state, bar=bar))
    return results


def filter_matching(
    rules: list[CompiledRule],
    state: dict | None = None,
    bar: dict | None = None,
    rule_type: str | None = None,
) -> list[CompiledRule]:
    """返回所有匹配的规则，可选按 type 过滤。"""
    results = execute_rules(rules, state=state, bar=bar)
    return [
        r.rule
        for r in results
        if r.matched and (rule_type is None or r.rule.rule_type == rule_type)
    ]
