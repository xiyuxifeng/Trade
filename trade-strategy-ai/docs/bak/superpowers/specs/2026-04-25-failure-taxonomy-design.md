# NTL-S5-002 失败归因分类 设计文档

> 状态：草稿，待评审
> 创建：2026-04-25
> 目标：建立盘后失败归因的标准化分类体系

---

## 1. 背景与目标

### 1.1 背景

NTL-S5-001 建立了 `EvidencePack` 结构，将盘前交易建议与完整上下文聚合。NTL-S5-002 在此基础上建立**失败归因分类**，为盘后评估提供结构化的失败原因标注能力。

### 1.2 目标

- 为每笔失败的交易生成标准化的 failure category 标签
- 支持多维度分类（根因 + 交易阶段 + 规则类型）
- 作为盘后 ranking、报告生成、Stage 7 学习闭环的权威数据源
- 支持记忆写回（通过显式步骤）

### 1.3 架构决策

**直接分析为主（A）**：
- `EvaluationResult.failure_categories` 是 canonical 权威来源
- Stage 7 学习闭环直接读取 `failure_categories`
- 记忆写回通过 NTL-S5-012 显式步骤实现

```
失败归因分类（权威来源）
        │
        ├──→ EvaluationResult.failure_categories ──→ Stage 7 学习闭环
        │
        └──→ NTL-S5-012 显式写回 ──→ TraderMemory.failure_case
```

---

## 2. 分类维度体系

采用**多维度标签组合（D）**：一笔失败可同时标注根因标签、交易阶段标签和规则类型标签。

### 2.1 维度结构

| 维度 | 是否必选 | 数量限制 | 存储位置 |
|------|----------|----------|----------|
| 根因（root_cause） | **必选** | 至少 1 个 | `failure_categories` |
| 交易阶段（stage） | 可选 | 最多 1 个 | `failure_categories` |
| 规则类型（rule_type） | 可选 | 最多 1 个 | `failure_categories` |

### 2.2 根因标签（RootCause）

| 标签 | 含义 | 来源依据 |
|------|------|----------|
| `rule_precondition_failed` | 规则前置条件未满足（如过滤条件本应拦住但没拦） | rules_snapshot |
| `signal_quality_low` | 信号质量低（如信号冲突、confidence 过低、规则互相矛盾） | SignalContext |
| `entry_timing_poor` | 入场时机差（如追高入场、收盘前匆忙入场） | market_data + entry_price |
| `exit_timing_poor` | 出场时机差（如止损被扫后反弹、过早止盈） | market_data + exit_price |
| `position_size_mismatch` | 仓位不匹配（如超过风险容忍、头寸过轻错过机会） | position_size + rules |
| `market_mismatch` | 市场环境不匹配（如策略不适应当前波动率或趋势强度渐变） | market_data |
| `external_event` | 外部事件冲击（如突发政策、板块黑天鹅） | market_data + external context |
| `symbol_selection_suboptimal` | 标的选择次优（如选的标的不是板块里最强或流动性最好的） | market_universe_snapshot |
| `data_quality_issue` | 数据质量问题（如收盘价异常、指标计算错误） | market_data |

### 2.3 交易阶段标签（Stage）

| 标签 | 含义 |
|------|------|
| `stage:entry` | 失败发生在入场阶段 |
| `stage:exit` | 失败发生在出场阶段 |
| `stage:holding` | 失败发生在持仓阶段（持仓期间判断失误） |

### 2.4 规则类型标签（RuleType）

| 标签 | 含义 |
|------|------|
| `rule_type:entry` | 涉及入场规则 |
| `rule_type:exit` | 涉及出场/止损规则 |
| `rule_type:filter` | 涉及过滤规则 |
| `rule_type:sizing` | 涉及仓位规则 |

---

## 3. 数据结构

### 3.1 Schema 定义

新增 `src/evaluation/failure_taxonomy.py`：

```python
class FailureRootCause(StrEnum):
    """失败根因标签（必选，至少 1 个）。"""
    RULE_PRECONDITION_FAILED = "rule_precondition_failed"
    SIGNAL_QUALITY_LOW = "signal_quality_low"
    ENTRY_TIMING_POOR = "entry_timing_poor"
    EXIT_TIMING_POOR = "exit_timing_poor"
    POSITION_SIZE_MISMATCH = "position_size_mismatch"
    MARKET_MISMATCH = "market_mismatch"
    EXTERNAL_EVENT = "external_event"
    SYMBOL_SELECTION_SUBOPTIMAL = "symbol_selection_suboptimal"
    DATA_QUALITY_ISSUE = "data_quality_issue"


class FailureStage(StrEnum):
    """失败发生的交易阶段（可选，最多 1 个）。"""
    ENTRY = "stage:entry"
    EXIT = "stage:exit"
    HOLDING = "stage:holding"


class FailureRuleType(StrEnum):
    """涉及的规则类型（可选，最多 1 个）。"""
    ENTRY = "rule_type:entry"
    EXIT = "rule_type:exit"
    FILTER = "rule_type:filter"
    SIZING = "rule_type:sizing"
```

### 3.2 存储方式

`EvaluationResult.failure_categories: list[str]` 直接存储标签字符串：

```python
["entry_timing_poor", "stage:entry", "rule_type:entry"]
```

### 3.3 维度解析辅助函数

```python
def parse_failure_categories(tags: list[str]) -> FailureAttribution:
    """将标签列表解析为结构化归因对象。"""
    root_causes = [t for t in tags if t in FailureRootCause]
    stages = [t for t in tags if t in FailureStage]
    rule_types = [t for t in tags if t in FailureRuleType]
    return FailureAttribution(
        root_causes=root_causes,
        stage=stages[0] if stages else None,
        rule_type=rule_types[0] if rule_types else None,
    )


@dataclass
class FailureAttribution:
    """结构化失败归因。"""
    root_causes: list[str]
    stage: str | None
    rule_type: str | None
```

---

## 4. 归因判断逻辑

### 4.1 判断优先级

1. **数据质量问题** → `data_quality_issue`（优先判断，避免后续计算基于错误数据）
2. **外部事件冲击** → `external_event`（可通过市场数据异常或已知事件列表判断）
3. **信号质量问题** → `signal_quality_low`（基于 SignalContext.confidence 或 triggered_rules 冲突）
4. **规则前置条件** → `rule_precondition_failed`（基于 rules_snapshot 中未满足的条件）
5. **入场时机** → `entry_timing_poor`（entry_price vs 盘中价格走势）
6. **出场时机** → `exit_timing_poor`（stop_loss 被扫 vs 后续反弹幅度）
7. **仓位管理** → `position_size_mismatch`（position_size vs 风险限额）
8. **市场环境** → `market_mismatch`（基于波动率、趋势强度等指标与环境判断）
9. **标的选择** → `symbol_selection_suboptimal`（基于同板块其他标的对比）
10. **阶段标注** → `stage:entry/exit/holding`（基于交易生命周期阶段）
11. **规则类型标注** → `rule_type:entry/exit/filter/sizing`（基于 rules_snapshot 中的规则类型）

### 4.2 exit_timing_poor 与 external_event 的区分

| 场景 | 根因标签 | 阶段标签 | 说明 |
|------|----------|----------|------|
| 止损被扫，后反弹 | `exit_timing_poor` | `stage:exit` | 止损设置不合理或出场时机差 |
| 止损被突发政策/事件扫掉 | `external_event` | `stage:exit` | 外部冲击导致，非策略问题 |
| 过早止盈 | `exit_timing_poor` | `stage:exit` | 持仓中判断失误 |
| 止损被扫但仓位没动（模拟环境） | `signal_quality_low` | - | 信号本身有问题 |

### 4.3 判断依据来源（续）

| 归因 | 主要依据 |
|------|----------|
| `rule_precondition_failed` | `EvidencePack.strategy_version_snapshot`（rules_snapshot） |
| `signal_quality_low` | `EvidencePack.signal_context`（confidence, triggered_rules） |
| `entry_timing_poor` | `EvidencePack.market_data`（入场价格 vs 盘中价格走势） |
| `exit_timing_poor` | `EvidencePack.market_data` + `EvidencePack.trade_idea`（止损 vs 后续反弹） |
| `position_size_mismatch` | `EvidencePack.trade_idea.position_size` + `EvidencePack.strategy_version_snapshot` |
| `market_mismatch` | `EvidencePack.market_data`（波动率、趋势指标） |
| `external_event` | `EvidencePack.market_data`（价格异常跳变）+ 外部事件列表 |
| `symbol_selection_suboptimal` | `EvidencePack.signal_context.market_universe_snapshot` |
| `data_quality_issue` | `EvidencePack.market_data`（价格/成交量异常检测） |

---

## 5. 扩展机制

### 5.1 扩展原则

- **根因标签**：通过代码评审扩展，需更新 `FailureRootCause` enum + 本文档 + 对应判断逻辑
- **交易阶段标签**：通过代码评审扩展，需更新 `FailureStage` enum + 本文档
- **规则类型标签**：通过代码评审扩展，需更新 `FailureRuleType` enum + 本文档

### 5.2 扩展流程

1. 在 `src/evaluation/failure_taxonomy.py` 中新增 enum 条目
2. 在本设计文档中对应维度下新增标签定义行
3. 在判断逻辑中新增对应分支
4. 编写或更新对应测试
5. 通过代码评审合并

### 5.3 禁止事项

- **禁止**在运行时动态创建新标签
- **禁止**在 `failure_categories` 中使用非 enum 定义内的标签字符串
- **禁止**在 enum 中添加 `vendor:*` 或其他自定义命名空间前缀

---

## 6. 与其他模块的关系

### 6.1 上游

- `EvidencePack`：归因判断的核心输入来源
- `EvaluationResult`：归因结果写入 `failure_categories` 字段

### 6.2 下游

- **Stage 7 学习闭环**：直接读取 `EvaluationResult.failure_categories` 作为规则提炼的数据源
- **NTL-S5-003（盘后复盘）**：消费 failure_categories 生成结构化复盘报告
- **NTL-S5-004（ranking service）**：按 failure_categories 聚合统计
- **NTL-S5-012（记忆写回）**：基于 failure_categories 显式写入 `TraderMemory.failure_case`

---

## 7. 实现计划

### 7.1 文件结构

```
src/evaluation/
    __init__.py
    evidence_pack.py      # NTL-S5-001（已有）
    failure_taxonomy.py   # NTL-S5-002（新增）
```

### 7.2 导出内容

```python
# src/evaluation/__init__.py
from .failure_taxonomy import (
    FailureRootCause,
    FailureStage,
    FailureRuleType,
    FailureAttribution,
    parse_failure_categories,
)

__all__ = [
    "FailureRootCause",
    "FailureStage",
    "FailureRuleType",
    "FailureAttribution",
    "parse_failure_categories",
]
```

### 7.3 验收标准

1. 三个 StrEnum 类型完整定义，所有标签无重复
2. `parse_failure_categories()` 正确解析混合标签列表
3. 文档完整记录所有标签含义和判断依据
4. 扩展机制（章节 5）清晰，可执行
5. 与 EvidencePack 的数据流关系明确

---

## 8. Self-Review Checklist

- [ ] 所有标签都有明确含义，无歧义
- [ ] 根因标签至少 1 个，互不重叠
- [ ] stage 和 rule_type 可选但数量限制明确
- [ ] `exit_timing_poor` 与 `external_event` 的区分逻辑清晰（章节 4.2）
- [ ] 扩展机制完整，可执行
- [ ] 上游/下游数据流关系清晰
- [ ] 无 "TBD"、"TODO" 占位符
