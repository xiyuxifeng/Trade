"""
Tests for DSL Compiler (P2-006).
"""

from __future__ import annotations

from src.persona.dsl import AND, CMP, NOT, OR, TRUE, FALSE
from src.persona.dsl_compiler import (
    CompiledRule,
    ExecutionResult,
    StateAccessor,
    compile_condition,
    compile_rule,
    execute_rules,
    filter_matching,
)


class TestStateAccessor:
    """Unit tests for StateAccessor."""

    def test_get_from_bar(self) -> None:
        acc = StateAccessor(state={}, bar={"close": 100.0})
        assert acc.get("close") == 100.0

    def test_get_from_state(self) -> None:
        acc = StateAccessor(state={"regime": "bullish"}, bar={})
        assert acc.get("regime") == "bullish"

    def test_bar_takes_precedence(self) -> None:
        acc = StateAccessor(state={"regime": "bearish"}, bar={"regime": "bullish"})
        assert acc.get("regime") == "bullish"

    def test_get_missing_returns_none(self) -> None:
        acc = StateAccessor(state={}, bar={})
        assert acc.get("anything") is None


class TestCompileCondition:
    """Unit tests for condition expression compilation."""

    def test_cmp_eq_true(self) -> None:
        expr = CMP("regime", "eq", "bullish")
        fn = compile_condition(expr)
        acc = StateAccessor(state={"regime": "bullish"}, bar={})
        assert fn(acc) is True

    def test_cmp_eq_false(self) -> None:
        expr = CMP("regime", "eq", "bullish")
        fn = compile_condition(expr)
        acc = StateAccessor(state={"regime": "bearish"}, bar={})
        assert fn(acc) is False

    def test_cmp_gt_true(self) -> None:
        expr = CMP("close", "gt", 100.0)
        fn = compile_condition(expr)
        acc = StateAccessor(state={}, bar={"close": 105.0})
        assert fn(acc) is True

    def test_cmp_gt_false(self) -> None:
        expr = CMP("close", "gt", 105.0)
        fn = compile_condition(expr)
        acc = StateAccessor(state={}, bar={"close": 100.0})
        assert fn(acc) is False

    def test_cmp_in_true(self) -> None:
        expr = CMP("regime", "in", ["bullish", "neutral"])
        fn = compile_condition(expr)
        acc = StateAccessor(state={"regime": "bullish"}, bar={})
        assert fn(acc) is True

    def test_cmp_not_in(self) -> None:
        expr = CMP("regime", "not_in", ["bullish"])
        fn = compile_condition(expr)
        acc = StateAccessor(state={"regime": "bearish"}, bar={})
        assert fn(acc) is True

    def test_cmp_missing_field_returns_false(self) -> None:
        expr = CMP("nonexistent", "eq", "x")
        fn = compile_condition(expr)
        acc = StateAccessor(state={}, bar={})
        assert fn(acc) is False

    def test_and_true(self) -> None:
        expr = AND(
            CMP("regime", "eq", "bullish"),
            CMP("close", "gt", 100.0),
        )
        fn = compile_condition(expr)
        acc = StateAccessor(state={"regime": "bullish"}, bar={"close": 105.0})
        assert fn(acc) is True

    def test_and_false_when_one_fails(self) -> None:
        expr = AND(
            CMP("regime", "eq", "bullish"),
            CMP("close", "gt", 200.0),
        )
        fn = compile_condition(expr)
        acc = StateAccessor(state={"regime": "bullish"}, bar={"close": 105.0})
        assert fn(acc) is False

    def test_or_true(self) -> None:
        expr = OR(
            CMP("regime", "eq", "bearish"),
            CMP("close", "gt", 100.0),
        )
        fn = compile_condition(expr)
        acc = StateAccessor(state={"regime": "bullish"}, bar={"close": 105.0})
        assert fn(acc) is True

    def test_or_false(self) -> None:
        expr = OR(
            CMP("regime", "eq", "bearish"),
            CMP("close", "gt", 200.0),
        )
        fn = compile_condition(expr)
        acc = StateAccessor(state={"regime": "bullish"}, bar={"close": 105.0})
        assert fn(acc) is False

    def test_not(self) -> None:
        expr = NOT(CMP("regime", "eq", "bullish"))
        fn = compile_condition(expr)
        acc = StateAccessor(state={"regime": "bearish"}, bar={})
        assert fn(acc) is True

    def test_true(self) -> None:
        expr = TRUE  # not callable, it's already a ConditionExpr
        fn = compile_condition(expr)
        acc = StateAccessor(state={}, bar={})
        assert fn(acc) is True

    def test_false(self) -> None:
        expr = FALSE  # not callable, it's already a ConditionExpr
        fn = compile_condition(expr)
        acc = StateAccessor(state={}, bar={})
        assert fn(acc) is False

    def test_nested(self) -> None:
        expr = AND(
            CMP("regime", "eq", "bullish"),
            OR(
                CMP("close", "gt", 200.0),
                CMP("close", "lt", 50.0),
            ),
        )
        fn = compile_condition(expr)
        acc1 = StateAccessor(state={"regime": "bullish"}, bar={"close": 30.0})
        acc2 = StateAccessor(state={"regime": "bullish"}, bar={"close": 100.0})
        assert fn(acc1) is True
        assert fn(acc2) is False


class TestCompileRule:
    """Unit tests for compile_rule with ConditionExpr."""

    def test_compile_condition_only(self) -> None:
        expr = CMP("regime", "eq", "bullish")
        rule = compile_rule(expr, rule_id="test-rule", name="Test Rule")
        assert isinstance(rule, CompiledRule)
        assert rule.rule_id == "test-rule"
        assert rule.name == "Test Rule"
        assert rule.rule_type == "filter"
        assert rule.instrument_focus == "mixed"

    def test_compiled_rule_matches(self) -> None:
        expr = CMP("close", "gt", 100.0)
        rule = compile_rule(expr)
        assert rule.matches(state={}, bar={"close": 105.0}) is True
        assert rule.matches(state={}, bar={"close": 90.0}) is False

    def test_compiled_rule_repr(self) -> None:
        expr = CMP("regime", "eq", "bullish")
        rule = compile_rule(expr, rule_id="r1", name="My Rule")
        r = repr(rule)
        assert "r1" in r
        assert "filter" in r
        assert "My Rule" in r


class TestExecuteRules:
    """Unit tests for execute_rules and filter_matching."""

    def test_execute_rules(self) -> None:
        r1 = compile_rule(CMP("regime", "eq", "bullish"))
        r2 = compile_rule(CMP("close", "gt", 100.0))
        results = execute_rules(
            [r1, r2],
            state={"regime": "bullish"},
            bar={"close": 105.0},
        )
        assert len(results) == 2
        assert results[0].matched is True
        assert results[1].matched is True

    def test_filter_matching(self) -> None:
        r1 = compile_rule(CMP("regime", "eq", "bullish"))
        r2 = compile_rule(CMP("close", "gt", 200.0))
        matched = filter_matching(
            [r1, r2],
            state={"regime": "bullish"},
            bar={"close": 105.0},
        )
        assert len(matched) == 1
        assert matched[0].rule_id == r1.rule_id

    def test_filter_matching_by_type(self) -> None:
        expr = CMP("regime", "eq", "bullish")
        r1 = compile_rule(expr, rule_id="entry1")
        matched = filter_matching([r1], state={}, bar={}, rule_type="entry")
        assert len(matched) == 0  # rule_type is "filter" by default

    def test_execute_rules_empty(self) -> None:
        results = execute_rules([], state={}, bar={})
        assert results == []
