# Topic-Memory 完整集成设计

> **目标：** 让 HotTopic 信息从盘前到盘后完整流转，实现基于 topic 的记忆检索。

## 1. 现状与缺口

**已有：**
- `TraderMemoryStore` 支持按 `tags` + `strategy_version_id` 检索（NTL-S5-006 ✅）
- `market_universe` 模块可加载 HotTopics（`MarketUniverse.hot_topics`）
- `SignalContext.market_universe_snapshot` 存储了 MarketUniverse（但未被用于关联 idea）

**缺口：**
- `idea.source_topic_ids` 永远是 `[]`——HotTopic 从未关联到 TradeIdea
- `DailyReport` 没有 `market_universe_snapshot` 字段——盘后无法获取 HotTopic 详情
- `run_after_close()` 写入 `TraderMemory` 时没有填充 `tags` / `topic_source` / `raw_topic_ids`

## 2. 数据流设计

```
run_pre_market()
  └── 生成 TradeIdea 时
        ├── 从 market_universe.hot_topics 关联 topic → idea.source_topic_ids
        └── DailyReport.market_universe_snapshot = market_universe（序列化）
              ↓
run_after_close()
  └── 加载 DailyReport（含 market_universe_snapshot）
        └── 对每个 idea，从 market_universe_snapshot 反查 HotTopic 详情
              └── 生成 canonical tag: "kaipan:concept:芯片"
              └── 填充 TraderMemoryItem(tags, topic_source, raw_topic_ids)
```

## 3. 实现步骤

### Step 1: DailyReport 新增 market_universe_snapshot 字段

**文件：** `src/schemas/contracts.py`

```python
class DailyReport(BaseModel):
    # ... 现有字段 ...
    # 新增
    market_universe_snapshot: dict[str, Any] | None = None  # MarketUniverse 序列化
```

**注意：** `DailyReport` 是盘前生成的，存储的是**当日候选池快照**（非实时）。

### Step 2: run_pre_market() 关联 HotTopic 到 idea.source_topic_ids

**文件：** `src/agents/trader_agent/agent.py` — `generate_trade_ideas()`

当 `strategy_version` 非 None 时，每个 idea 生成时：
- 检查该标的是否在 `market_universe.strong_symbols` 或 `hot_topics` 中
- 如果在，从 `hot_topics` 取对应 `topic_id` 列表，写入 `idea.source_topic_ids`

**伪代码：**
```python
# 在 generate_trade_ideas() 中，Idea 构建时
if market_universe and symbol in relevant_topics:
    idea.source_topic_ids = [topic.topic_id for topic in hot_topics if symbol_matches]
```

### Step 3: run_pre_market() 保存 market_universe_snapshot 到 DailyReport

**文件：** `src/agents/manager_agent/agent.py` — `run_pre_market()`

```python
report = DailyReport(
    ...
    market_universe_snapshot=asdict(market_universe) if market_universe else None,
)
write_json(report_path, report.model_dump())
```

### Step 4: run_after_close() 填充 canonical tags

**文件：** `src/agents/manager_agent/agent.py` — `run_after_close()`

当构造 `TraderMemoryItem` 时：
```python
# 从 DailyReport.market_universe_snapshot 反查 canonical tags
canonical_tags = []
raw_topic_ids_map = {}

if daily_report.market_universe_snapshot and idea.source_topic_ids:
    mu = MarketUniverse(**daily_report.market_universe_snapshot)
    hot_topics_map = {ht.topic_id: ht for ht in (mu.hot_topics or [])}
    for tid in idea.source_topic_ids:
        ht = hot_topics_map.get(tid)
        if ht:
            canonical_tags.append(f"kaipan:{ht.kind}:{ht.topic_name}")
            raw_topic_ids_map["kaipan"] = ht.topic_id

TraderMemoryItem(
    ...
    tags=["evaluation", memory_type.value] + canonical_tags,
    topic_source="kaipan",
    raw_topic_ids=raw_topic_ids_map if raw_topic_ids_map else None,
)
```

## 4. Canonical Tag 格式

**格式：** `{provider}:{kind}:{topic_name}`

**示例：**
- `kaipan:concept:芯片`
- `kaipan:industry:半导体`
- `kaipan:concept_fengkou:锂电池`

## 5. 依赖关系

| 步骤 | 文件 | 说明 |
|------|------|------|
| Step 1 | `src/schemas/contracts.py` | DailyReport 新增字段 |
| Step 2 | `src/agents/trader_agent/agent.py` | generate_trade_ideas 关联 topic |
| Step 3 | `src/agents/manager_agent/agent.py` | run_pre_market 保存快照 |
| Step 4 | `src/agents/manager_agent/agent.py` | run_after_close 填充 tags |

## 6. 测试策略

- `test_daily_report_has_market_universe_snapshot` — 验证字段存在
- `test_trade_idea_source_topic_ids_populated` — 验证 idea 生成时关联 topic
- `test_memory_item_has_canonical_tags` — 验证 run_after_close 写入正确的 tags
