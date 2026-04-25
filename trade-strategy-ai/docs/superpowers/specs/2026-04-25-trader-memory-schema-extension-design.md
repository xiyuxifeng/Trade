# NTL-S5-005 TraderMemory Schema 扩展 设计文档

> 状态：已批准
> 创建：2026-04-25
> 目标：扩展 TraderMemory schema，支撑盘后复盘结论、策略调整建议和市场状态记忆的存储与检索

---

## 1. 背景与目标

NTL-S5-001 建立了 EvidencePack，NTL-S5-003 建立了 PostmortemService，NTL-S5-004 建立了 RankingService。NTL-S5-005 在此基础上扩展 `TraderMemory` schema，支持将盘后评估结果（postmortem）、策略调整（strategy_adjustment）、市场状态（market_regime_note）写入记忆层，供下次盘前使用和 Stage 7 自主优化。

### 核心能力

1. **新增 Memory Types**：3 种新类型支持结构化盘后数据存储
2. **扩展字段**：关联交易上下文（idea_id / strategy_version_id / ranking_entry_id）
3. **JSONB 内嵌**：结构化数据存储在 TraderMemoryItem 的专用字段
4. **追加型存储**：保留历史，支持 Stage 7 学习闭环
5. **双向追溯**：Memory 可追溯到 RankingEntry，Ranking 可追溯到 Memory

---

## 2. 数据结构

### 2.1 扩展后的 TraderMemoryType

```python
class TraderMemoryType(str, Enum):
    """Memory categories written back by the manager loop."""

    success_case = "success_case"
    failure_case = "failure_case"
    review_note = "review_note"
    postmortem = "postmortem"                        # 新增：盘后复盘结论
    strategy_adjustment = "strategy_adjustment"     # 新增：策略调整建议
    market_regime_note = "market_regime_note"       # 新增：市场状态备注
```

### 2.2 扩展后的 TraderMemoryItem

```python
class TraderMemoryItem(BaseModel):
    """One persisted trader memory entry."""

    # === 已有字段（不变）===
    memory_id: UUID = Field(default_factory=uuid4)
    trader_id: str
    memory_type: TraderMemoryType
    as_of_date: date

    symbol: str | None = None
    title: str
    content: str
    source: str = "manager"
    source_ref: str | None = None
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5

    archived: bool = False
    archived_at: datetime | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # === 新增字段：交易上下文关联 ===
    idea_id: UUID | None = None              # 关联的 TradeIdea ID
    strategy_version_id: str | None = None    # 关联的策略版本 ID
    ranking_entry_id: UUID | None = None     # 关联的 RankingEntry ID（强关联）

    # === 新增字段：盘后评估数据 ===
    # postmortem_data：直接复用 PostmortemResult 完整结构
    postmortem_data: dict | None = None      # {
                                                #   return_pct: float | None,
                                                #   mfe: float | None,
                                                #   mae: float | None,
                                                #   attribution_source: str,
                                                #   failure_attribution: {
                                                #     root_causes: list[str],
                                                #     stage: str | None,
                                                #     rule_type: str | None
                                                #   },
                                                #   postmortem_notes: str | None
                                                # }

    # strategy_adjustment_data：策略调整建议
    strategy_adjustment_data: dict | None = None  # {
                                                    #   trigger: str,           # "postmortem_low_ranking" / "llm_correction" / "manual"
                                                    #   adjustment_type: str,   # "rule_param" / "new_rule" / "filter" / "position_size"
                                                    #   target: str,           # rule_id 或 "position_size" / "max_positions"
                                                    #   previous_value: Any,
                                                    #   new_value: Any,
                                                    #   expected_effect: str,
                                                    #   source_idea_id: UUID | None
                                                    # }

    # market_regime_data：市场状态备注
    market_regime_data: dict | None = None  # {
                                                #   regime_type: str,        # "bull" / "bear" / "volatile" / "stable"
                                                #   key_indicators: dict,    # {volatility, trend_strength, ...}
                                                #   note: str
                                                # }
```

### 2.3 更新后的 TraderMemorySummary

```python
class TraderMemorySummary(BaseModel):
    """Compact summary returned to the TraderAgent for prompt injection."""

    trader_id: str
    symbol: str | None = None
    total_items: int = 0
    total_symbol_items: int = 0
    archived_items: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    recent_titles: list[str] = Field(default_factory=list)
    symbol_titles: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)

    # === 新增字段 ===
    postmortem_notes: list[str] = Field(default_factory=list)      # postmortem 类型的 content
    strategy_adjustments: list[str] = Field(default_factory=list)  # strategy_adjustment 类型的 content
    market_regime_notes: list[str] = Field(default_factory=list)   # market_regime_note 类型的 content
```

---

## 3. 与其他模块的关系

### 3.1 上游

- **PostmortemService**：生成 PostmortemResult，提供 postmortem_data 内容
- **RankingService**：update_entry 时触发 Memory 写回（NTL-S5-012）
- **ManagerAgent**：执行盘后写回报文（NTL-S5-012）

### 3.2 下游

- **NTL-S5-006（TraderMemory service 检索能力）**：扩展检索支持 new memory types
- **NTL-S5-012（差评触发记忆写回）**：基于 ranking 结果触发 Memory 写入
- **NTL-S7-002（策略调整建议）**：读取 strategy_adjustment memory
- **NTL-S7-003（候选版本生成）**：读取 postmortem / strategy_adjustment memory
- **NTL-S7-004（滚动评估窗口）**：按 memory_type + date 统计 Trader 改进曲线

### 3.3 数据流

```
RankingService.update_entry()  →  ManagerAgent.run_postmortem_and_write_memory()
       │
       ▼
TraderMemoryStore.append(TraderMemoryItem(
    memory_type=postmortem,
    ranking_entry_id=entry_id,
    postmortem_data=postmortem_result.to_dict(),
    ...
))
```

---

## 4. 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 新增 memory types 数量 | 3 种全部新增 | NTL-S7-002/003/004 各有独立用途 |
| 存储方式 | JSONB 内嵌到 TraderMemoryItem | 低频批量读取，不需要复杂查询，JSONL 单文件够用 |
| 版本化策略 | 追加型（保留历史） | Stage 7 需要历史轨迹做优化 |
| postmortem_data 结构 | 完整 PostmortemResult | NTL-S7-002/003/004 需要 stage/rule_type 等完整维度 |
| strategy_adjustment_data | 完整字段（trigger/type/target/prev/new/effect） | NTL-S7-002/003 需要新旧值对比和触发源追溯 |
| ranking 关联方式 | 强关联（ranking_entry_id） | 直接绑定避免两步查找，支持重复写回检测 |

---

## 5. 扩展机制

### 5.1 扩展原则

- **新增 memory type**：需在 `TraderMemoryType` enum 中添加，并通过代码评审
- **新增 data 字段**：在对应的 `_data` dict 中扩展，避免破坏现有结构
- **向后兼容**：新增字段为 optional，不影响现有数据的读取

### 5.2 禁止事项

- **禁止**在运行时动态创建新 memory type
- **禁止**修改已存储的 JSONL 条目（追加型设计）

---

## 6. 实现计划

### 6.1 文件结构

```
src/trader_memory/
    schemas.py         # 修改：扩展 TraderMemoryType + TraderMemoryItem + TraderMemorySummary
    service.py         # 修改：summarize_context 新增 new memory types 支持
    __init__.py        # 修改：如有需要
```

### 6.2 导出内容

无需新增导出，扩展现有类。

### 6.3 验收标准

1. `TraderMemoryType` 包含全部 6 种类型（3 新增）
2. `TraderMemoryItem` 包含 `idea_id` / `strategy_version_id` / `ranking_entry_id` 字段
3. `TraderMemoryItem` 包含 `postmortem_data` / `strategy_adjustment_data` / `market_regime_data` 字段
4. `TraderMemorySummary` 包含 `postmortem_notes` / `strategy_adjustments` / `market_regime_notes` 字段
5. `summarize_context` 正确聚合 new memory types
6. 向后兼容：现有 JSONL 条目可正常读取

---

## 7. Self-Review Checklist

- [x] 所有 placeholder（TBD/TODO）已清理
- [x] 6 种 memory type 全部定义，无重复
- [x] 新增字段全部为 optional，向后兼容
- [x] postmortem_data 直接复用 PostmortemResult 结构
- [x] strategy_adjustment_data 包含 trigger/type/target/previous_value/new_value/expected_effect
- [x] ranking_entry_id 强关联设计
- [x] 与 NTL-S5-012、NTL-S7-002/003/004 下游关系明确
- [x] 扩展机制清晰，可执行