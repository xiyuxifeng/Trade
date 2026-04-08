# P2-009 行为标签化模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现交易行为标签化模块，从 TradeLog + 日线数据分类为 BehaviorLabel。

**Architecture:** 模块化规则引擎，BehaviorClassifier 接口抽象，具体规则从 YAML 配置加载，未来可替换为 ML 实现。

**Tech Stack:** Python, Pydantic, PyYAML, 复用 behavior.py 的 BehaviorLabel

---

## 文件结构

```
src/persona/behavior_labeler.py    # 主模块（创建）
config/rules/behavior_rules.yaml   # 规则配置（创建）
tests/unit/persona/test_behavior_labeler.py  # 单元测试（创建）
```

---

## Task 1: 创建 YAML 规则配置文件骨架

**Files:**
- Create: `trade-strategy-ai/config/rules/behavior_rules.yaml`

- [ ] **Step 1: 创建规则配置文件骨架**

```yaml
# 行为分类规则配置
# 规则按顺序评估，匹配第一个即返回

schema_version: "v1"

rules:
  # 追涨类
  - label: chase_rally
    description: 追涨（突破后追入）
    conditions:
      - field: price_vs_ma
        op: gt
        value: 1.02  # 价格 > MA20 * 1.02
      - field: volume_ratio
        op: gt
        value: 1.5   # 成交量放大
    signals: ["price_breakout", "high_volume"]

  # 抄底类
  - label: bottom_fish
    description: 抄底（均值回归左侧）
    conditions:
      - field: price_vs_ma
        op: lt
        value: 0.98  # 价格 < MA20 * 0.98
      - field: distance_from_high
        op: gt
        value: 0.1   # 距离高点 >10%
    signals: ["oversold", "support_level"]

  # 趋势跟踪
  - label: trend_follow
    description: 趋势跟踪
    conditions:
      - field: ma_slope
        op: gt
        value: 0.0   # MA 向上
      - field: price_vs_ma
        op: gt
        value: 1.0
    signals: ["trend_up", "above_ma"]

  # 止损
  - label: stop_loss_cut
    description: 止损
    conditions:
      - field: pnl_pct
        op: lt
        value: -0.05  # 亏损 >5%
    signals: ["stop_loss"]

  # 止盈
  - label: profit_taking
    description: 止盈
    conditions:
      - field: pnl_pct
        op: gt
        value: 0.10  # 盈利 >10%
    signals: ["profit_target"]
```

- [ ] **Step 2: 验证 YAML 格式正确**

Run: `cd trade-strategy-ai && python -c "import yaml; yaml.safe_load(open('config/rules/behavior_rules.yaml')); print('OK')"`
Expected: OK

---

## Task 2: 创建 context builder（计算派生字段）

**Files:**
- Create: `trade-strategy-ai/src/persona/behavior_labeler.py`（第一部分：ContextBuilder）

- [ ] **Step 1: 写 ContextBuilder 测试**

在 `tests/unit/persona/test_behavior_labeler.py` 中添加：

```python
"""Tests for BehaviorLabeler (P2-009)."""

from __future__ import annotations

import sys
sys.path.insert(0, "src")

from decimal import Decimal
from datetime import datetime

from src.models.trade_log import TradeLog
from src.models.market_data import MarketData
from src.persona.behavior_labeler import ContextBuilder


def test_compute_price_vs_ma():
    """价格 vs MA20 比率计算正确。"""
    bars = [
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 1),
                   open=Decimal("10"), high=Decimal("10.5"), low=Decimal("9.5"),
                   close=Decimal("10"), volume=Decimal("1000")),
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 3),
                   open=Decimal("10.2"), high=Decimal("10.8"), low=Decimal("10"),
                   close=Decimal("10.5"), volume=Decimal("1200")),
    ]
    trade = TradeLog(
        source="test", account_id="acc1", symbol="000001", market="SZ",
        side="buy", position_side="long", executed_at=datetime(2026, 4, 3, 14, 30),
        quantity=Decimal("100"), price=Decimal("10.5"), amount=Decimal("1050"),
        fee=Decimal("1"), executed_at=None,
    )
    # 手动设置 executed_at 因为 TradeLog 需要
    trade.executed_at = datetime(2026, 4, 3, 14, 30)

    builder = ContextBuilder()
    ctx = builder.build(trade, bars)

    # price_vs_ma = trade_price / avg_close(10, 10.5) = 10.5 / 10.25 ≈ 1.024
    assert "price_vs_ma" in ctx["features"]
    assert abs(ctx["features"]["price_vs_ma"] - 1.024) < 0.01


def test_context_requires_minimum_bars():
    """K线数据不足时返回默认值。"""
    trade = TradeLog(
        source="test", account_id="acc1", symbol="000001", market="SZ",
        side="buy", position_side="long", executed_at=datetime(2026, 4, 3, 14, 30),
        quantity=Decimal("100"), price=Decimal("10.5"), amount=Decimal("1050"),
        fee=Decimal("1"),
    )

    builder = ContextBuilder()
    ctx = builder.build(trade, [])  # 无 K线数据

    assert ctx["features"]["price_vs_ma"] == 1.0  # 默认值
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_behavior_labeler.py::test_compute_price_vs_ma -v --tb=short`
Expected: FAIL

- [ ] **Step 3: 实现 ContextBuilder**

```python
class ContextBuilder:
    """从 TradeLog 和 MarketData 构建分类所需的上下文特征。

    计算派生字段（从原始 OHLCV 推导），供规则引擎使用。
    设计支持多周期，但当前仅用日线数据计算。

    派生字段：
      - price_vs_ma: 交易价格 / MA20
      - volume_ratio: 成交量 / 20日均量
      - ma_slope: MA5 斜率（相对于 MA20）
      - distance_from_high: 距离 N 日高点百分比
      - distance_from_low: 距离 N 日低点百分比
      - hour: 交易小时
    """

    def build(self, trade: TradeLog, bars: list[MarketData]) -> dict:
        """构建分类上下文。

        Args:
            trade: 交易记录
            bars: 同一标的的日线数据（按 traded_at 升序）

        Returns:
            包含 features（派生字段字典）和 meta 的上下文
        """
        import math

        if not bars:
            features = self._default_features()
        else:
            features = self._compute_features(trade, bars)

        return {
            "trade": trade,
            "bars": bars,
            "features": features,
        }

    def _compute_features(self, trade: TradeLog, bars: list[MarketData]) -> dict:
        """计算派生特征。"""
        import math

        closes = [float(b.close) for b in bars[-20:]]  # 最近20日
        volumes = [float(b.volume) for b in bars[-20:]]

        ma20 = sum(closes) / len(closes) if closes else 0
        avg_volume = sum(volumes) / len(volumes) if volumes else 0

        trade_price = float(trade.price)
        volume = float(trade.quantity)

        features = {}

        # 价格 vs MA20
        features["price_vs_ma"] = trade_price / ma20 if ma20 > 0 else 1.0

        # 成交量比
        features["volume_ratio"] = volume / avg_volume if avg_volume > 0 else 1.0

        # MA5 斜率（简化：最近5日 vs 前5日）
        if len(closes) >= 10:
            ma5_recent = sum(closes[-5:]) / 5
            ma5_past = sum(closes[-10:-5]) / 5
            features["ma_slope"] = (ma5_recent - ma5_past) / ma5_past if ma5_past > 0 else 0.0
        else:
            features["ma_slope"] = 0.0

        # 距离 N 日高点
        highs = [float(b.high) for b in bars[-20:]]
        high_n = max(highs) if highs else trade_price
        features["distance_from_high"] = (high_n - trade_price) / high_n if high_n > 0 else 0.0

        # 距离 N 日低点
        lows = [float(b.low) for b in bars[-20:]]
        low_n = min(lows) if lows else trade_price
        features["distance_from_low"] = (trade_price - low_n) / low_n if low_n > 0 else 0.0

        # 交易小时
        features["hour"] = trade.executed_at.hour

        return features

    def _default_features(self) -> dict:
        """K线不足时返回默认值。"""
        return {
            "price_vs_ma": 1.0,
            "volume_ratio": 1.0,
            "ma_slope": 0.0,
            "distance_from_high": 0.0,
            "distance_from_low": 0.0,
            "hour": 0,
        }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_behavior_labeler.py::test_compute_price_vs_ma tests/unit/persona/test_behavior_labeler.py::test_context_requires_minimum_bars -v --tb=short`
Expected: 2 tests PASS

- [ ] **Step 5: 提交**

```bash
git add config/rules/behavior_rules.yaml src/persona/behavior_labeler.py tests/unit/persona/test_behavior_labeler.py
git commit -m "feat(P2-009): add ContextBuilder and behavior rules YAML"
```

---

## Task 3: 实现 RuleBasedClassifier

**Files:**
- Modify: `trade-strategy-ai/src/persona/behavior_labeler.py`
- Modify: `tests/unit/persona/test_behavior_labeler.py`

- [ ] **Step 1: 写 RuleEngine 和 RuleBasedClassifier 测试**

```python
from src.persona.behavior_labeler import RuleBasedClassifier, BehaviorLabeler
from src.persona.behavior import BehaviorLabel

def test_rule_engine_gt():
    """gt 比较器工作正常。"""
    trade = TradeLog(
        source="test", account_id="acc1", symbol="000001", market="SZ",
        side="buy", position_side="long", executed_at=datetime(2026, 4, 3, 14, 30),
        quantity=Decimal("100"), price=Decimal("10.5"), amount=Decimal("1050"),
        fee=Decimal("1"),
    )
    ctx = {"trade": trade, "bars": [], "features": {"price_vs_ma": 1.1}}

    # 规则：price_vs_ma > 1.02
    from src.persona.behavior_labeler import RuleCondition
    cond = RuleCondition(field="price_vs_ma", op="gt", value=1.02)
    assert cond.evaluate(ctx) is True

    cond2 = RuleCondition(field="price_vs_ma", op="gt", value=1.2)
    assert cond2.evaluate(ctx) is False


def test_rule_engine_lt():
    """lt 比较器工作正常。"""
    ctx = {"trade": None, "bars": [], "features": {"distance_from_high": 0.15}}

    cond = RuleCondition(field="distance_from_high", op="lt", value=0.1)
    assert cond.evaluate(ctx) is False

    cond2 = RuleCondition(field="distance_from_high", op="lt", value=0.2)
    assert cond2.evaluate(ctx) is True


def test_rule_all_conditions_must_match():
    """AND 逻辑：所有条件都匹配才算匹配。"""
    ctx = {"trade": None, "bars": [], "features": {"price_vs_ma": 1.1, "volume_ratio": 2.0}}

    rule = Rule(
        label=BehaviorLabel.CHASE_RALLY,
        conditions=[
            RuleCondition(field="price_vs_ma", op="gt", value=1.02),
            RuleCondition(field="volume_ratio", op="gt", value=1.5),
        ],
    )
    assert rule.matches(ctx) is True

    rule2 = Rule(
        label=BehaviorLabel.CHASE_RALLY,
        conditions=[
            RuleCondition(field="price_vs_ma", op="gt", value=1.02),
            RuleCondition(field="volume_ratio", op="gt", value=3.0),  # 不满足
        ],
    )
    assert rule2.matches(ctx) is False


def test_classifier_unknown_when_no_match():
    """无规则匹配时返回 UNKNOWN。"""
    classifier = RuleBasedClassifier("config/rules/behavior_rules.yaml")
    ctx = {"trade": None, "bars": [], "features": {"price_vs_ma": 1.0, "volume_ratio": 1.0}}

    result = classifier.classify(ctx)
    assert result.label == BehaviorLabel.UNKNOWN
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_behavior_labeler.py -v --tb=short`
Expected: FAIL

- [ ] **Step 3: 在 behavior_labeler.py 中添加 RuleCondition 和 Rule 类**

在 `ContextBuilder` 类之后添加：

```python
from dataclasses import dataclass
from typing import Any
import yaml
from src.persona.behavior import BehaviorLabel, BehaviorPattern


class RuleCondition:
    """单条规则条件。

    支持的比较操作符：gt, lt, ge, le, eq

    Attributes:
        field: 上下文中的字段名（如 price_vs_ma）
        op: 比较操作符
        value: 比较阈值
    """

    def __init__(self, field: str, op: str, value: Any) -> None:
        self.field = field
        self.op = op
        self.value = value

    def evaluate(self, context: dict) -> bool:
        """评估条件是否满足。

        Args:
            context: 包含 features 的上下文字典

        Returns:
            True 如果满足条件
        """
        features = context.get("features", {})
        actual = features.get(self.field)

        if actual is None:
            return False

        if self.op == "gt":
            return actual > self.value
        elif self.op == "lt":
            return actual < self.value
        elif self.op == "ge":
            return actual >= self.value
        elif self.op == "le":
            return actual <= self.value
        elif self.op == "eq":
            return actual == self.value
        return False


@dataclass
class Rule:
    """单条行为分类规则。

    包含多个条件，所有条件都满足时触发。

    Attributes:
        label: 匹配的行为标签
        description: 规则描述
        conditions: 条件列表（AND 关系）
        signals: 触发信号列表
    """

    label: BehaviorLabel
    description: str
    conditions: list[RuleCondition]
    signals: list[str]

    def matches(self, context: dict) -> bool:
        """所有条件都满足时返回 True（AND 逻辑）。"""
        return all(cond.evaluate(context) for cond in self.conditions)


class RuleBasedClassifier:
    """基于 YAML 规则配置的分类器。

    从 YAML 文件加载规则，遍历规则列表，
    返回第一个完全匹配的 BehaviorPattern。
    无匹配时返回 UNKNOWN。

    Attributes:
        rules: 规则列表（按优先级排序）
    """

    def __init__(self, rules_path: str) -> None:
        self.rules = self._load_rules(rules_path)

    def _load_rules(self, rules_path: str) -> list[Rule]:
        """从 YAML 文件加载规则配置。"""
        with open(rules_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        rules = []
        for rule_dict in config.get("rules", []):
            conditions = [
                RuleCondition(
                    field=c["field"],
                    op=c["op"],
                    value=c["value"],
                )
                for c in rule_dict.get("conditions", [])
            ]
            rules.append(Rule(
                label=BehaviorLabel(rule_dict["label"]),
                description=rule_dict.get("description", ""),
                conditions=conditions,
                signals=rule_dict.get("signals", []),
            ))
        return rules

    def classify(self, context: dict) -> BehaviorPattern:
        """对给定上下文进行行为分类。

        Args:
            context: ContextBuilder.build() 返回的上下文

        Returns:
            BehaviorPattern，匹配规则时带对应 label，无匹配时 label=UNKNOWN
        """
        for rule in self.rules:
            if rule.matches(context):
                return BehaviorPattern(
                    label=rule.label,
                    confidence=0.9,  # 规则置信度固定为 0.9
                    signals=rule.signals,
                    context=rule.description,
                )

        # 无匹配
        return BehaviorPattern(
            label=BehaviorLabel.UNKNOWN,
            confidence=0.0,
            signals=[],
            context=None,
        )

```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_behavior_labeler.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 5: 提交**

```bash
git add src/persona/behavior_labeler.py tests/unit/persona/test_behavior_labeler.py
git commit -m "feat(P2-009): add RuleBasedClassifier with YAML rule loading"
```

---

## Task 4: 实现 BehaviorLabeler 入口类

**Files:**
- Modify: `trade-strategy-ai/src/persona/behavior_labeler.py`
- Modify: `tests/unit/persona/test_behavior_labeler.py`

- [ ] **Step 1: 写 BehaviorLabeler 测试**

```python
def test_labeler_facade():
    """BehaviorLabeler 提供统一入口。"""
    # 创建少量 K线数据
    bars = [
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 1),
                   open=Decimal("10"), high=Decimal("10.5"), low=Decimal("9.5"),
                   close=Decimal("10"), volume=Decimal("1000")),
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 2),
                   open=Decimal("10.1"), high=Decimal("10.6"), low=Decimal("10"),
                   close=Decimal("10.4"), volume=Decimal("1100")),
        MarketData(symbol="000001", market="SZ", timeframe="1d",
                   traded_at=datetime(2026, 4, 3),
                   open=Decimal("10.3"), high=Decimal("10.8"), low=Decimal("10.2"),
                   close=Decimal("10.6"), volume=Decimal("1500")),
    ]

    trade = TradeLog(
        source="test", account_id="acc1", symbol="000001", market="SZ",
        side="buy", position_side="long",
        executed_at=datetime(2026, 4, 3, 14, 30),
        quantity=Decimal("100"), price=Decimal("10.6"), amount=Decimal("1060"),
        fee=Decimal("1"),
    )

    labeler = BehaviorLabeler(rules_path="config/rules/behavior_rules.yaml")
    pattern = labeler.label(trade, bars)

    assert isinstance(pattern.label, BehaviorLabel)
    assert isinstance(pattern.confidence, float)


def test_labeler_unknown():
    """无特征时返回 UNKNOWN。"""
    trade = TradeLog(
        source="test", account_id="acc1", symbol="000001", market="SZ",
        side="buy", position_side="long",
        executed_at=datetime(2026, 4, 3, 14, 30),
        quantity=Decimal("100"), price=Decimal("10"), amount=Decimal("1000"),
        fee=Decimal("1"),
    )

    labeler = BehaviorLabeler(rules_path="config/rules/behavior_rules.yaml")
    pattern = labeler.label(trade, [])  # 无 K线

    assert pattern.label == BehaviorLabel.UNKNOWN
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_behavior_labeler.py -v --tb=short`
Expected: FAIL

- [ ] **Step 3: 添加 BehaviorLabeler 类**

```python
class BehaviorLabeler:
    """行为标签化入口类。

    提供统一的高层接口，封装 ContextBuilder 和分类器。

    Example:
        labeler = BehaviorLabeler()
        pattern = labeler.label(trade, daily_bars)
    """

    def __init__(self, rules_path: str | None = None) -> None:
        """初始化 BehaviorLabeler。

        Args:
            rules_path: YAML 规则文件路径，默认为 config/rules/behavior_rules.yaml
        """
        if rules_path is None:
            rules_path = "config/rules/behavior_rules.yaml"
        self.context_builder = ContextBuilder()
        self.classifier = RuleBasedClassifier(rules_path)

    def label(
        self,
        trade: TradeLog,
        market_bars: list[MarketData],
    ) -> BehaviorPattern:
        """对单笔交易进行行为标签化。

        Args:
            trade: 交易记录
            market_bars: 同一标的的日线数据（支持多周期预留）

        Returns:
            BehaviorPattern，包含标签、置信度、信号
        """
        context = self.context_builder.build(trade, market_bars)
        return self.classifier.classify(context)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_behavior_labeler.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 5: 提交**

```bash
git add src/persona/behavior_labeler.py tests/unit/persona/test_behavior_labeler.py
git commit -m "feat(P2-009): add BehaviorLabeler facade class"
```

---

## Task 5: 最终验证

- [ ] **Step 1: 运行全量测试**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/test_behavior_labeler.py -v --tb=short`

- [ ] **Step 2: 运行回归测试**

Run: `cd trade-strategy-ai && python -m pytest tests/unit/persona/ -v --tb=short`

- [ ] **Step 3: 更新 TaskList**

P2-009 标记为完成

---

## 依赖关系

- Task 1 独立
- Task 2 依赖 Task 1
- Task 3 依赖 Task 2
- Task 4 依赖 Task 2 和 Task 3

## 验证检查清单

- [ ] YAML 规则文件格式正确
- [ ] ContextBuilder 计算 price_vs_ma / volume_ratio / ma_slope / distance_from_high
- [ ] RuleCondition 支持 gt/lt/ge/le/eq
- [ ] Rule 所有条件 AND 匹配
- [ ] RuleBasedClassifier 遍历规则优先返回第一个匹配
- [ ] BehaviorLabeler 封装 ContextBuilder + 分类器
- [ ] 无匹配时返回 UNKNOWN
- [ ] 所有测试通过，无真实数据依赖
- [ ] 所有类和公共方法有中文注释
