# P2-007 DSL 验证流程设计

## 目标

对 DSL 输入（ArticleStrategyRule / ConditionExpr）进行**语法校验 + 标准化**，确保 DSL 规则合法、可执行、无冗余。

## 验证级别

**语法校验 + 标准化**（不含语义校验）。

## 设计决策

| 决策项 | 选择 |
|--------|------|
| 验证级别 | B：语法校验 + 标准化 |
| 输入来源 | C：pipeline + 文件导入统一接口 |
| 错误格式 | A：复用 ValidationIssue |
| 标准化规则 | A：最小集合（去冗余嵌套、单子节点提升） |

---

## 模块结构

```
src/persona/dsl_validator.py   # 主模块
tests/unit/persona/test_dsl_validator.py
```

---

## 核心接口

### DSLValidator

```python
class DSLValidator:
    def validate_condition(self, expr: ConditionExpr) -> list[ValidationIssue]:
        """验证 ConditionExpr 语法合法性（递归）。

        检查项：
        - op 是否在允许列表 {and, or, not, cmp, true, false}
        - and/or: args 非空
        - not: args 恰好1个
        - cmp: field 和 cmp 非空，cmp 在允许列表
        """

    def normalize_condition(self, expr: ConditionExpr) -> ConditionExpr:
        """标准化 ConditionExpr（递归）。

        简化规则（按优先级）：
        1. AND(TRUE, x) → x
        2. OR(FALSE, x) → x
        3. NOT(NOT(x)) → x
        4. AND(x) → x  （单子节点提升）
        5. OR(x) → x   （单子节点提升）
        """

    def validate_rule(
        self,
        rule: ArticleStrategyRule | ArticlePrecondition,
    ) -> list[ValidationIssue]:
        """验证 ArticleStrategyRule / ArticlePrecondition。"""

    def validate_rules(
        self,
        rules: list[ArticleStrategyRule],
        source: str = "unknown",
    ) -> list[ValidationIssue]:
        """批量验证，返回所有问题。"""
```

### 验证问题代码

| code | severity | 说明 |
|------|----------|------|
| `dsl.syntax.invalid_op` | ERROR | op 不在允许列表 |
| `dsl.syntax.missing_field` | ERROR | cmp 缺少 field |
| `dsl.syntax.invalid_cmp` | ERROR | cmp 操作符不合法 |
| `dsl.syntax.missing_args` | ERROR | and/or args 为空 |
| `dsl.syntax.invalid_not_args` | ERROR | not args 数量非1 |

---

## 标准化算法

### normalize_condition(expr) 递归算法

```
function normalize(expr):
    # 1. 递归标准化子节点
    if expr.op in {and, or}:
        normalized_args = [normalize(child) for child in expr.args]
        expr = expr.model_copy(update={"args": normalized_args})
    elif expr.op == "not":
        normalized_child = normalize(expr.args[0])
        expr = expr.model_copy(update={"args": [normalized_child]})

    # 2. 简化规则（按优先级）
    if expr.op == "and":
        # 去除 TRUE
        args = [a for a in expr.args if not (a.op == "true")]
        if len(args) == 0: return TRUE
        if len(args) == 1: return args[0]
        return expr.model_copy(update={"args": args})

    if expr.op == "or":
        # 去除 FALSE
        args = [a for a in expr.args if not (a.op == "false")]
        if len(args) == 0: return FALSE
        if len(args) == 1: return args[0]
        return expr.model_copy(update={"args": args})

    if expr.op == "not":
        if expr.args[0].op == "not":
            return expr.args[0].args[0]  # NOT(NOT(x)) → x

    return expr
```

---

## 数据流

```
输入 (ArticleStrategyRule / ConditionExpr)
       │
       ▼
┌─────────────────────────┐
│  validate_rule/         │
│  validate_condition()   │
│                         │
│  1. 语法校验（递归）     │ ──→ ValidationIssue[]
│  2. 标准化（递归）       │ ──→ 标准化 ConditionExpr
└─────────────────────────┘
       │
       ▼
输出
  - ValidationIssue[]（有错误时）
  - 标准化 ConditionExpr（validate_rule 返回）
```

---

## 测试策略

1. **语法校验测试**：
   - 合法 ConditionExpr → 无 issue
   - 非法 op → ERROR
   - and/or 空 args → ERROR
   - not 多参数 → ERROR
   - cmp 缺 field → ERROR

2. **标准化测试**：
   - AND(TRUE, x) → x
   - OR(FALSE, x) → x
   - NOT(NOT(x)) → x
   - AND(x) → x
   - OR(x) → x
   - 嵌套场景：AND(TRUE, OR(FALSE, x)) → x

3. **批量验证测试**：
   - 多条规则，汇总所有 issue
   - 无 issue 时返回空列表

---

## 产出文件

| 文件 | 说明 |
|------|------|
| `src/persona/dsl_validator.py` | 主模块 |
| `tests/unit/persona/test_dsl_validator.py` | 单元测试 |

---

## 依赖关系

- 复用 `src/pipeline/validation.py` 的 `ValidationIssue` 和 `ValidationSeverity`
- 复用 `src/persona/dsl.py` 的 `ConditionExpr`、`ArticleStrategyRule`、`ArticlePrecondition`
- 不依赖真实数据，纯代码逻辑
