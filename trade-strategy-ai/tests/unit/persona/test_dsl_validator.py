"""Tests for DSL Validator (P2-007)."""

from __future__ import annotations

from src.persona.dsl import AND, CMP, FALSE, NOT, OR, TRUE, ConditionExpr, ActionSpec
from src.persona.dsl_validator import DSLValidator
from src.persona.schemas import ArticleStrategyRule, ArticlePrecondition, InstrumentFocus
from src.persona.claim_keys import ClaimKey


class TestValidateCondition:
    def test_valid_cmp(self):
        v = DSLValidator()
        expr = CMP("regime", "eq", "bullish")
        issues = v.validate_condition(expr)
        assert issues == []

    def test_invalid_op(self):
        v = DSLValidator()
        expr = ConditionExpr(op="foobar")
        issues = v.validate_condition(expr)
        assert any(i.code == "dsl.syntax.invalid_op" for i in issues)

    def test_and_missing_args(self):
        v = DSLValidator()
        expr = ConditionExpr(op="and", args=[])
        issues = v.validate_condition(expr)
        assert any(i.code == "dsl.syntax.missing_args" for i in issues)

    def test_not_multiple_args(self):
        v = DSLValidator()
        expr = ConditionExpr(op="not", args=[CMP("a", "eq", 1), CMP("b", "eq", 2)])
        issues = v.validate_condition(expr)
        assert any(i.code == "dsl.syntax.invalid_not_args" for i in issues)

    def test_cmp_missing_field(self):
        v = DSLValidator()
        expr = ConditionExpr(op="cmp", field=None, cmp="eq", value=1)
        issues = v.validate_condition(expr)
        assert any(i.code == "dsl.syntax.missing_field" for i in issues)

    def test_cmp_invalid_cmp_op(self):
        v = DSLValidator()
        expr = ConditionExpr(op="cmp", field="x", cmp="invalid", value=1)
        issues = v.validate_condition(expr)
        assert any(i.code == "dsl.syntax.invalid_cmp" for i in issues)

    def test_nested_invalid(self):
        v = DSLValidator()
        expr = AND(CMP("a", "eq", 1), ConditionExpr(op="foobar"))
        issues = v.validate_condition(expr)
        assert any(i.code == "dsl.syntax.invalid_op" for i in issues)


class TestNormalizeCondition:
    def test_normalize_and_true(self):
        v = DSLValidator()
        expr = AND(TRUE, CMP("x", "eq", 1))
        norm = v.normalize_condition(expr)
        assert norm.op == "cmp"
        assert norm.field == "x"

    def test_normalize_and_multiple(self):
        v = DSLValidator()
        expr = AND(TRUE, CMP("a", "eq", 1), CMP("b", "eq", 2))
        norm = v.normalize_condition(expr)
        assert norm.op == "and"
        assert len(norm.args) == 2

    def test_normalize_or_false(self):
        v = DSLValidator()
        expr = OR(FALSE, CMP("x", "eq", 1))
        norm = v.normalize_condition(expr)
        assert norm.op == "cmp"
        assert norm.field == "x"

    def test_normalize_not_not(self):
        v = DSLValidator()
        expr = NOT(NOT(CMP("x", "eq", 1)))
        norm = v.normalize_condition(expr)
        assert norm.op == "cmp"
        assert norm.field == "x"

    def test_normalize_single_child_and(self):
        v = DSLValidator()
        expr = AND(CMP("x", "eq", 1))
        norm = v.normalize_condition(expr)
        assert norm.op == "cmp"

    def test_normalize_single_child_or(self):
        v = DSLValidator()
        expr = OR(CMP("x", "eq", 1))
        norm = v.normalize_condition(expr)
        assert norm.op == "cmp"

    def test_normalize_nested(self):
        v = DSLValidator()
        expr = AND(TRUE, OR(FALSE, CMP("x", "eq", 1)))
        norm = v.normalize_condition(expr)
        assert norm.op == "cmp"
        assert norm.field == "x"


class TestValidateRule:
    def test_validate_rule_valid(self):
        v = DSLValidator()
        rule = ArticleStrategyRule(
            claim_key=ClaimKey.entry_trigger,
            rule_type="entry",
            instrument_focus=InstrumentFocus.stock,
            condition={"op": "cmp", "field": "regime", "cmp": "eq", "value": "bullish"},
            action={"type": "enter"},
            params={},
            confidence=0.8,
        )
        issues = v.validate_rule(rule)
        assert issues == []

    def test_validate_rule_invalid_condition(self):
        v = DSLValidator()
        rule = ArticleStrategyRule(
            claim_key=ClaimKey.entry_trigger,
            rule_type="entry",
            instrument_focus=InstrumentFocus.stock,
            condition={"op": "foobar"},
            action={"type": "enter"},
            params={},
            confidence=0.8,
        )
        issues = v.validate_rule(rule)
        assert any(i.code == "dsl.syntax.invalid_op" for i in issues)

    def test_validate_rules_multiple(self):
        v = DSLValidator()
        rules = [
            ArticleStrategyRule(
                claim_key=ClaimKey.entry_trigger,
                rule_type="entry",
                instrument_focus=InstrumentFocus.stock,
                condition={"op": "cmp", "field": "regime", "cmp": "eq", "value": "bullish"},
                action={"type": "enter"},
                params={},
                confidence=0.8,
            ),
            ArticleStrategyRule(
                claim_key=ClaimKey.exit_take_profit,
                rule_type="exit",
                instrument_focus=InstrumentFocus.stock,
                condition={"op": "foobar"},
                action={"type": "exit"},
                params={},
                confidence=0.8,
            ),
        ]
        issues = v.validate_rules(rules, source="test")
        assert len(issues) == 1
        assert issues[0].code == "dsl.syntax.invalid_op"

    def test_validate_rules_empty(self):
        v = DSLValidator()
        issues = v.validate_rules([], source="test")
        assert issues == []