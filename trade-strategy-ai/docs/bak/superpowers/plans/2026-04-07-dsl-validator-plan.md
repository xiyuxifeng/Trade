# P2-007 DSL 验证流程实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对 DSL 输入（ArticleStrategyRule / ConditionExpr）进行语法校验 + 标准化，确保规则合法、可执行、无冗余。

**Architecture:** 复用现有 ValidationIssue 体系，新增 DSLValidator 类处理语法校验和标准化逻辑，不依赖真实数据。

**Tech Stack:** Python, Pydantic, 复用 src/pipeline/validation.py 的 ValidationIssue

---

## 文件结构

```
src/persona/dsl_validator.py   # 创建：DSLValidator 类
tests/unit/persona/test_dsl_validator.py  # 创建：单元测试
```

---

## Task 1: 创建 dsl_validator.py 骨架

**Files:**
- Create: `trade-strategy-ai/src/persona/dsl_validator.py`
- Reference: `trade-strategy-ai/src/pipeline/validation.py` (ValidationIssue 复用)
- Reference: `trade-strategy-ai/src/persona/dsl.py` (ConditionExpr 定义)

- [ ] **Step 1: 创建 dsl_validator.py 骨架（import + 类定义）**

```python
"""DSL Validator — 语法校验 + 标准化。"""

from __future__ import annotations

from src.pipeline.validation import ValidationIssue, ValidationSeverity
from src.persona.dsl import ConditionExpr


class DSLValidator:
    def validate_condition(self, expr: ConditionExpr) -> list[ValidationIssue]:
        ...

    def normalize_condition(self, expr: ConditionExpr) -> ConditionExpr:
        ...
```

- [ ] **Step 2: 运行验证骨架可导入**

Run: `cd trade-strategy-ai && python -c "from src.persona.dsl_validator import DSLValidator; print('OK')"`
Expected: OK

---

## Task 2: 实现 validate_condition 语法校验

**Files:**
- Modify: `trade-strategy-ai/src/persona/dsl_validator.py`

- [ ] **Step 1: 写 validate_condition 测试（现有测试文件追加）**

在 `tests/unit/persona/test_dsl_validator.py` 中添加：

```python
from src.persona.dsl import AND, CMP, FALSE, NOT, OR, TRUE
from src.persona.dsl_validator import DSLValidator

def test_valid_cmp():
    v = DSLValidator()
    expr = CMP("regime", "eq", "bullish")
    issues = v.validate_condition(expr)
    assert issues == []

def test_invalid_op():
    v = DSLValidator()
    from src.persona.dsl import ConditionExpr
    expr = ConditionExpr(op="foobar")
    issues = v.validate_condition(expr)
    assert any(i.code == "dsl.syntax.invalid_op" for i in issues)

def test_and_missing_args():
    v = DSLValidator()
    expr = ConditionExpr(op="and", args=[])
    issues = v.validate_condition(expr)
    assert any(i.code == "dsl.syntax.missing_args" for i in issues)

def test_not_multiple_args():
    v = DSLValidator()
    expr = ConditionExpr(op="not", args=[CMP("a", "eq", 1), CMP("b", "eq", 2)])
    issues = v.validate_condition(expr)
    assert any(i.code == "dsl.syntax.invalid_not_args" for i in issues)

def test_cmp_missing_field():
    v = DSLValidator()
    expr = ConditionExpr(op="cmp", field=None, cmp="eq", value=1)
    issues = v.validate_condition(expr)
    assert any(i.code == "dsl.syntax.missing_field" for i in issues)

def test_cmp_invalid_cmp_op():
    v = DSLValidator()
    expr = ConditionExpr(op="cmp", field="x", cmp="invalid", value=1)
    issues = v.validate_condition(expr)
    assert any(i.code == "dsl.syntax.invalid_cmp" for i in issues)

def test_nested_invalid():
    v = DSLValidator()
    expr = AND(CMP("a", "eq", 1), ConditionExpr(op="foobar"))
    issues = v.validate_condition(expr)
    assert any(i.code == "dsl.syntax.invalid_op" for i in issues)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_dsl_validator.py -v --tb=short`
Expected: FAIL (DSLValidator not implemented yet)

- [ ] **Step 3: 实现 validate_condition**

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_dsl_validator.py -v --tb=short`
Expected: 7 tests PASS

- [ ] **Step 5: 提交**

```bash
git add trade-strategy-ai/src/persona/dsl_validator.py trade-strategy-ai/tests/unit/persona/test_dsl_validator.py
git commit -m "feat(P2-007): add DSLValidator.validate_condition syntax checking"
```

---

## Task 3: 实现 normalize_condition 标准化

**Files:**
- Modify: `trade-strategy-ai/src/persona/dsl_validator.py`
- Modify: `tests/unit/persona/test_dsl_validator.py`

- [ ] **Step 1: 写 normalize_condition 测试**

```python
def test_normalize_and_true():
    v = DSLValidator()
    expr = AND(TRUE, CMP("x", "eq", 1))
    norm = v.normalize_condition(expr)
    assert norm.op == "cmp"
    assert norm.field == "x"

def test_normalize_and_multiple():
    v = DSLValidator()
    expr = AND(TRUE, CMP("a", "eq", 1), CMP("b", "eq", 2))
    norm = v.normalize_condition(expr)
    assert norm.op == "and"
    assert len(norm.args) == 2

def test_normalize_or_false():
    v = DSLValidator()
    expr = OR(FALSE, CMP("x", "eq", 1))
    norm = v.normalize_condition(expr)
    assert norm.op == "cmp"
    assert norm.field == "x"

def test_normalize_not_not():
    v = DSLValidator()
    expr = NOT(NOT(CMP("x", "eq", 1)))
    norm = v.normalize_condition(expr)
    assert norm.op == "cmp"
    assert norm.field == "x"

def test_normalize_single_child_and():
    v = DSLValidator()
    expr = AND(CMP("x", "eq", 1))
    norm = v.normalize_condition(expr)
    assert norm.op == "cmp"

def test_normalize_single_child_or():
    v = DSLValidator()
    expr = OR(CMP("x", "eq", 1))
    norm = v.normalize_condition(expr)
    assert norm.op == "cmp"

def test_normalize_nested():
    v = DSLValidator()
    expr = AND(TRUE, OR(FALSE, CMP("x", "eq", 1)))
    norm = v.normalize_condition(expr)
    assert norm.op == "cmp"
    assert norm.field == "x"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_dsl_validator.py -v --tb=short`
Expected: FAIL (normalize not implemented)

- [ ] **Step 3: 实现 normalize_condition**

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_dsl_validator.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 5: 提交**

```bash
git add trade-strategy-ai/src/persona/dsl_validator.py trade-strategy-ai/tests/unit/persona/test_dsl_validator.py
git commit -m "feat(P2-007): add normalize_condition standardization"
```

---

## Task 4: 实现 validate_rule 批量验证

**Files:**
- Modify: `trade-strategy-ai/src/persona/dsl_validator.py`
- Modify: `tests/unit/persona/test_dsl_validator.py`

- [ ] **Step 1: 写 validate_rule / validate_rules 测试**

```python
from src.persona.schemas import ArticleStrategyRule, ArticlePrecondition
from src.persona.claim_keys import ClaimKey
from src.persona.patterns import InstrumentFocus

def test_validate_rule_valid():
    v = DSLValidator()
    rule = ArticleStrategyRule(
        claim_key=ClaimKey.ENTRY_TRIGGER,
        rule_type="entry",
        instrument_focus=InstrumentFocus.STOCK,
        condition=CMP("regime", "eq", "bullish"),
        action=ActionSpec(type="enter"),
        params={},
        confidence=0.8,
    )
    issues = v.validate_rule(rule)
    assert issues == []

def test_validate_rule_invalid_condition():
    v = DSLValidator()
    rule = ArticleStrategyRule(
        claim_key=ClaimKey.ENTRY_TRIGGER,
        rule_type="entry",
        instrument_focus=InstrumentFocus.STOCK,
        condition=ConditionExpr(op="foobar"),
        action=ActionSpec(type="enter"),
        params={},
        confidence=0.8,
    )
    issues = v.validate_rule(rule)
    assert any(i.code == "dsl.syntax.invalid_op" for i in issues)

def test_validate_rules_multiple():
    v = DSLValidator()
    rules = [
        ArticleStrategyRule(
            claim_key=ClaimKey.ENTRY_TRIGGER,
            rule_type="entry",
            instrument_focus=InstrumentFocus.STOCK,
            condition=CMP("regime", "eq", "bullish"),
            action=ActionSpec(type="enter"),
            params={},
            confidence=0.8,
        ),
        ArticleStrategyRule(
            claim_key=ClaimKey.EXIT_TRIGGER,
            rule_type="exit",
            instrument_focus=InstrumentFocus.STOCK,
            condition=ConditionExpr(op="foobar"),
            action=ActionSpec(type="exit"),
            params={},
            confidence=0.8,
        ),
    ]
    issues = v.validate_rules(rules, source="test")
    assert len(issues) == 1
    assert issues[0].code == "dsl.syntax.invalid_op"

def test_validate_rules_empty():
    v = DSLValidator()
    issues = v.validate_rules([], source="test")
    assert issues == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_dsl_validator.py -v --tb=short`
Expected: FAIL (validate_rule not implemented)

- [ ] **Step 3: 实现 validate_rule 和 validate_rules**

```python
def validate_rule(
    self,
    rule: ArticleStrategyRule | ArticlePrecondition,
) -> list[ValidationIssue]:
    """验证 ArticleStrategyRule / ArticlePrecondition。"""
    issues: list[ValidationIssue] = []
    issues.extend(self.validate_condition(rule.condition))
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_dsl_validator.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 5: 提交**

```bash
git add trade-strategy-ai/src/persona/dsl_validator.py trade-strategy-ai/tests/unit/persona/test_dsl_validator.py
git commit -m "feat(P2-007): add validate_rule and validate_rules batch validation"
```

---

## Task 5: 最终验证

- [ ] **Step 1: 运行全量测试**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_dsl_validator.py -v --tb=short`

- [ ] **Step 2: 运行回归测试确保无破坏**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_dsl_compiler.py -v --tb=short`

- [ ] **Step 3: 更新 TaskList**

P2-007 标记为完成

---

## 依赖关系

- Task 2 依赖 Task 1
- Task 3 独立于 Task 2（但都在同一文件）
- Task 4 依赖 Task 2 和 Task 3

## 验证检查清单

- [ ] validate_condition 覆盖所有 5 种错误代码
- [ ] normalize_condition 覆盖 5 种简化规则
- [ ] validate_rules 汇总所有 issue
- [ ] 测试使用 mock 数据，无真实数据依赖
