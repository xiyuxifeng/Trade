"""DSL Validator — 语法校验 + 标准化。"""

from __future__ import annotations

from src.pipeline.validation import ValidationIssue, ValidationSeverity
from src.persona.dsl import ConditionExpr


class DSLValidator:
    def validate_condition(self, expr: ConditionExpr) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        self._validate_expr(expr, issues)
        return issues

    def _validate_expr(self, expr: ConditionExpr, issues: list[ValidationIssue]) -> None:
        op = expr.op
        allowed_ops = {"and", "or", "not", "cmp", "true", "false"}

        if op not in allowed_ops:
            issues.append(ValidationIssue(
                code="dsl.syntax.invalid_op",
                severity=ValidationSeverity.ERROR,
                message=f"Unknown ConditionExpr op: {op!r}",
                context={"op": op},
            ))
            return

        if op in ("and", "or"):
            if not expr.args:
                issues.append(ValidationIssue(
                    code="dsl.syntax.missing_args",
                    severity=ValidationSeverity.ERROR,
                    message=f"ConditionExpr op={op!r} requires non-empty args",
                    context={"op": op},
                ))
            for child in (expr.args or []):
                self._validate_expr(child, issues)

        elif op == "not":
            if not expr.args or len(expr.args) != 1:
                issues.append(ValidationIssue(
                    code="dsl.syntax.invalid_not_args",
                    severity=ValidationSeverity.ERROR,
                    message="ConditionExpr op='not' requires exactly one arg",
                    context={"args_count": len(expr.args) if expr.args else 0},
                ))
            for child in (expr.args or []):
                self._validate_expr(child, issues)

        elif op == "cmp":
            if not expr.field:
                issues.append(ValidationIssue(
                    code="dsl.syntax.missing_field",
                    severity=ValidationSeverity.ERROR,
                    message="ConditionExpr op='cmp' requires field",
                    context={"field": expr.field, "cmp": expr.cmp},
                ))
            if expr.cmp and expr.cmp not in {"eq", "ne", "gt", "ge", "lt", "le", "in", "not_in"}:
                issues.append(ValidationIssue(
                    code="dsl.syntax.invalid_cmp",
                    severity=ValidationSeverity.ERROR,
                    message=f"cmp must be one of {{eq,ne,gt,ge,lt,le,in,not_in}}, got: {expr.cmp!r}",
                    context={"cmp": expr.cmp},
                ))

    def normalize_condition(self, expr: ConditionExpr) -> ConditionExpr:
        ...