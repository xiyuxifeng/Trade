"""
Strategy DSL — 人可读、机器可解析的规则表达格式。

Schema 版本: v1 (2026-04-07)

设计目标:
1. YAML/JSON 双重兼容（Pydantic model 可序列化为任一格式）
2. 可版本化（schema_version 字段）
3. 可校验（ConditionExpr 有结构化校验）
4. 可组合（规则可聚合成 StyleCluster）

目录结构:
  strategy_rules[]   → ArticleStrategyRule 列表（每条规则 = 一个操作意图）
  preconditions[]     → ArticlePrecondition 列表（市场前置条件）
  extracted_concepts  → 概念标签列表（人可读）

---

## ArticleStrategyRule

一条从文章中提取的规范化规则。

字段:
  schema_version  : str  = "v1"   # 版本号，用于前向兼容
  claim_key       : ClaimKey      # 规则归属分类（见 claim_keys.py）
  rule_type       : str           # entry | exit | filter | sizing | risk
  instrument_focus: InstrumentFocus  # stock | etf | cb | mixed
  condition       : ConditionExpr # 市场状态前提（见下方）
  action          : ActionSpec    # 触发动作（见下方）
  params          : dict          # 扩展参数（规则特定）
  confidence      : float | None  # 置信度 0.0~1.0

证据字段:
  source_url   : str | None
  quoted_text  : str | None       # 来源原文（可选）
  published_at : datetime | None

---

## ArticlePrecondition

市场前置条件（大盘/板块状态要求）。

字段:
  schema_version  : str = "v1"
  claim_key       : ClaimKey = filter_market_regime
  instrument_focus: InstrumentFocus
  condition       : ConditionExpr
  confidence      : float | None

证据字段:
  source_url   : str | None
  quoted_text  : str | None
  published_at : datetime | None

---

## ConditionExpr

条件表达式树，支持 AND/OR/NOT 逻辑运算符。

结构:
  { "op": "and", "args": [ConditionExpr, ...] }
  { "op": "or",  "args": [ConditionExpr, ...] }
  { "op": "not", "args": [ConditionExpr] }
  { "op": "cmp", "field": "<field_path>", "cmp": "eq|ne|gt|ge|lt|le|in|not_in",
                     "value": <any> }
  { "op": "true" }   # 恒真
  { "op": "false" }  # 恒假

field_path 示例:
  "regime"          → MarketState.regime
  "volatility"      → MarketState.volatility
  "symbol_count"    → 自定义计数
  "price.near_high" → 价格接近N日高点

---

## ActionSpec

动作规格，描述规则触发后的操作。

字段:
  type   : str           # enter | exit | filter | sizing | risk | adjust
  side   : str | None    # buy | sell（enter/exit 用）
  order  : str | None    # limit | market | trigger
  price  : Any | None    # 价格表达式，如 { "var": "close" } 或 { "var": "entry_price", "pct": -0.05 }
  params : dict          # 扩展参数

---

## YAML 示例

```yaml
# 策略规则示例：突破20日高点买入
schema_version: "v1"
claim_key: entry.trigger
rule_type: entry
instrument_focus: stock
condition:
  op: and
  args:
    - op: cmp; field: regime; cmp: eq; value: trend_up
    - op: cmp; field: volatility; cmp: in; value: [low, mid]
action:
  type: enter
  side: buy
  order: limit
  price: { var: close }
  params:
    breakout_window: 20
    confirmation: close_above
confidence: 0.85
source_url: https://example.com/article
```

## JSON 示例

```json
{
  "schema_version": "v1",
  "claim_key": "entry.trigger",
  "rule_type": "entry",
  "instrument_focus": "stock",
  "condition": {
    "op": "and",
    "args": [
      {"op": "cmp", "field": "regime", "cmp": "eq", "value": "trend_up"},
      {"op": "cmp", "field": "volatility", "cmp": "in", "value": ["low", "mid"]}
    ]
  },
  "action": {
    "type": "enter",
    "side": "buy",
    "order": "limit",
    "price": {"var": "close"}
  },
  "confidence": 0.85
}
```
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

from src.persona.claim_keys import ClaimKey


# ---------------------------------------------------------------------------
# Condition expression tree
# ---------------------------------------------------------------------------

class ConditionExpr(BaseModel):
    """Structured market condition expression tree.

    Supports: and, or, not, cmp (comparison), true, false
    """

    op: str  # "and" | "or" | "not" | "cmp" | "true" | "false"
    args: list["ConditionExpr"] | None = None  # for and/or/not
    field: str | None = None  # for cmp
    cmp: str | None = None  # eq | ne | gt | ge | lt | le | in | not_in
    value: Any | None = None  # for cmp

    @model_validator(mode="after")
    def _validate_op(self) -> "ConditionExpr":
        allowed = {"and", "or", "not", "cmp", "true", "false"}
        if self.op not in allowed:
            raise ValueError(f"ConditionExpr op must be one of {allowed}, got: {self.op!r}")

        if self.op in ("and", "or"):
            if not self.args:
                raise ValueError(f"ConditionExpr op={self.op!r} requires non-empty args")
        elif self.op == "not":
            if not self.args or len(self.args) != 1:
                raise ValueError(f"ConditionExpr op='not' requires exactly one arg")
        elif self.op == "cmp":
            if not self.field or not self.cmp:
                raise ValueError("ConditionExpr op='cmp' requires field and cmp")
            allowed_cmp = {"eq", "ne", "gt", "ge", "lt", "le", "in", "not_in"}
            if self.cmp not in allowed_cmp:
                raise ValueError(f"cmp must be one of {allowed_cmp}, got: {self.cmp!r}")

        # true/false have no further requirements
        return self


# ---------------------------------------------------------------------------
# Action specification
# ---------------------------------------------------------------------------

class ActionSpec(BaseModel):
    """Action triggered when a rule's condition is satisfied."""

    type: str  # enter | exit | filter | sizing | risk | adjust
    side: str | None = None  # buy | sell
    order: str | None = None  # limit | market | trigger
    price: dict[str, Any] | None = None  # e.g. {"var": "close"} or {"var": "entry_price", "pct": -0.05}
    params: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Convenience constructors (for code generation / testing)
# ---------------------------------------------------------------------------

AND = lambda *args: ConditionExpr(op="and", args=list(args))
OR = lambda *args: ConditionExpr(op="or", args=list(args))
NOT = lambda arg: ConditionExpr(op="not", args=[arg])
TRUE = ConditionExpr(op="true")
FALSE = ConditionExpr(op="false")
CMP = lambda field, cmp_op, value: ConditionExpr(op="cmp", field=field, cmp=cmp_op, value=value)
