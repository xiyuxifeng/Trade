# P2-009 行为标签化模块设计

## 目标

实现交易行为标签化模块：从 TradeLog 分类为 BehaviorLabel，为 TraderProfile 提供输入。

## 设计决策

| 决策项 | 选择 |
|--------|------|
| 方法 | B+ 模块化规则引擎（可演进 ML） |
| 规则配置 | A YAML 文件 |
| 输入数据 | B TradeLog + 日线（设计支持多周期） |
| 分类结果 | A 仅返回 in-memory |

---

## 模块结构

```
src/persona/behavior_labeler.py    # 主模块
config/rules/behavior_rules.yaml  # 规则配置
tests/unit/persona/test_behavior_labeler.py
```

---

## 核心接口

```python
class BehaviorClassifier(ABC):
    """行为分类器抽象接口。

    定义分类器契约，未来可替换为 ML 实现而无需修改调用方。
    """
    def classify(self, trade: TradeLog, context: dict) -> BehaviorPattern:
        """对单笔交易进行行为分类。"""


class RuleBasedClassifier(BehaviorClassifier):
    """基于 YAML 规则配置的分类器。

    规则从 YAML 文件加载，支持运行时重载。
    """
    def __init__(self, rules_path: str): ...


class BehaviorLabeler:
    """行为标签化入口类。

    封装分类器，提供友好的高层接口。
    """
    def label(self, trade: TradeLog, market_bars: list[MarketData]) -> BehaviorPattern:
        """对单笔交易进行标签化。"""
```

---

## 上下文 context 结构

```python
context = {
    "daily_bars": list[MarketData],  # 日线数据（支持多周期预留）
    "recent_trades": list[TradeLog], # 同交易日近期交易（可选）
}
```

---

## 规则 YAML 格式

```yaml
rules:
  - label: chase_rally
    conditions:
      - field: price_vs_ma
        op: gt
        value: 1.02  # 价格 > MA * 1.02
      - field: volume_ratio
        op: gt
        value: 1.5
    signals: ["price_breakout", "high_volume"]

  - label: bottom_fish
    conditions:
      - field: price_vs_ma
        op: lt
        value: 0.98
      - field: distance_from_high
        op: gt
        value: 0.1
    signals: ["oversold", "support_level"]
```

---

## 分类流程

```
TradeLog + context (日线)
       │
       ▼
  BehaviorLabeler.label()
       │
       ▼
  RuleBasedClassifier.classify()
       │
       ▼
  遍历 rules.yaml 规则
       │
       ▼
  匹配第一个命中的规则 → BehaviorPattern
  无匹配 → BehaviorLabel.UNKNOWN
```

---

## ML 升级路径

```python
# 未来只需替换这一行
classifier = RuleBasedClassifier("config/rules/behavior_rules.yaml")  # 现在
classifier = MLClassifier("models/behavior_classifier.pkl")           # 未来
```

---

## 代码注释要求

**所有类和公共方法必须有简洁的中文注释**，解释：
- 类：做什么的、用途
- 方法：输入、输出、行为

示例：
```python
class RuleEngine:
    """规则引擎，负责根据配置规则评估交易行为。"""
    pass

def evaluate(self, trade: TradeLog, context: dict) -> bool:
    """评估交易是否匹配当前规则。

    Args:
        trade: 交易记录
        context: 包含日线等上下文的字典

    Returns:
        True 如果匹配，否则 False
    """
```

---

## 产出文件

| 文件 | 说明 |
|------|------|
| `src/persona/behavior_labeler.py` | 主模块 |
| `config/rules/behavior_rules.yaml` | 规则配置 |
| `tests/unit/persona/test_behavior_labeler.py` | 单元测试 |

---

## 依赖关系

- 依赖 `src/persona/behavior.py` 的 BehaviorLabel、BehaviorPattern
- 依赖 `src/models/trade_log.py` 的 TradeLog
- 依赖 `src/models/market_data.py` 的 MarketData
- 不依赖真实数据，纯代码逻辑
