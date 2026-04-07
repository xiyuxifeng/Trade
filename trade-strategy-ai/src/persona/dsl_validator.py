"""DSL Validator — 语法校验 + 标准化。"""

from __future__ import annotations

from src.pipeline.validation import ValidationIssue, ValidationSeverity
from src.persona.dsl import ConditionExpr
from src.persona.schemas import ArticleStrategyRule, ArticlePrecondition


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
        from src.persona.dsl import TRUE, FALSE

        # 1. 递归标准化子节点
        if expr.op in ("and", "or"):
            normalized_args = [self.normalize_condition(child) for child in (expr.args or [])]
            expr = expr.model_copy(update={"args": normalized_args})

            # 2. 简化规则
            if expr.op == "and":
                # 去除 TRUE
                args = [a for a in expr.args if a.op != "true"]
                if len(args) == 0:
                    return TRUE
                if len(args) == 1:
                    return args[0]
                return expr.model_copy(update={"args": args})

            if expr.op == "or":
                # 去除 FALSE
                args = [a for a in expr.args if a.op != "false"]
                if len(args) == 0:
                    return FALSE
                if len(args) == 1:
                    return args[0]
                return expr.model_copy(update={"args": args})

        elif expr.op == "not":
            normalized_child = self.normalize_condition(expr.args[0])
            expr = expr.model_copy(update={"args": [normalized_child]})

            # NOT(NOT(x)) → x
            if normalized_child.op == "not":
                return normalized_child.args[0]

        return expr

    def validate_rule(
        self,
        rule: ArticleStrategyRule | ArticlePrecondition,
    ) -> list[ValidationIssue]:
        """验证 ArticleStrategyRule / ArticlePrecondition。"""
        issues: list[ValidationIssue] = []
        condition = rule.condition
        if isinstance(condition, dict):
            condition = ConditionExpr.model_validate(condition)
        issues.extend(self.validate_condition(condition))
        return issues

    def validate_rules(
        self,
        rules: list[ArticleStrategyRule],
        source: str = "unknown",
    ) -> list[ValidationIssue]:
        """批量验证，返回所有问题。"""
        all_issues: list[ValidationIssue] = []
        for rule in rules:
            rule_issues = self.validate_rule(rule)
            for issue in rule_issues:
                issue.context = {**issue.context, "rule_id": getattr(rule, "claim_key", None), "source": source}
            all_issues.extend(rule_issues)
        return all_issues