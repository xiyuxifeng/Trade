"""Tests for DSL Validator (P2-007)."""

from __future__ import annotations

from src.persona.dsl import AND, CMP, FALSE, NOT, OR, TRUE, ConditionExpr
from src.persona.dsl_validator import DSLValidator


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