# Topic-Memory 完整集成设计

> **目标：** 让 Topic 信息从盘前到盘后完整流转，实现基于 topic 的记忆检索。
> **更新（2026-04-25）：** source_topic_ids 改用 "topic_name|kind" 编码格式，直接从 topic_constituents 生成 canonical tag，不再依赖 hot_topics 查表。

## 1. 现状与缺口

**已有：**
- `TraderMemoryStore` 支持按 `tags` + `strategy_version_id` 检索（NTL-S5-006 ✅）
- `market_universe` 模块可加载 `topic_constituents`（TopicConstituentsPayload）
- `SignalContext.market_universe_snapshot` 存储了 MarketUniverse

**缺口：**
- `idea.source_topic_ids` 存储格式不明确，导致 canonical tag 生成依赖不稳定的跨数据源查表
- `DailyReport` 没有 `market_universe_snapshot` 字段——盘后无法获取候选池快照
- `run_after_close()` 写入 `TraderMemory` 时没有填充 `tags` / `topic_source` / `raw_topic_ids`

## 2. 数据流设计

```
run_pre_market()
  └── 生成 TradeIdea 时
        ├── 从 market_universe.topic_constituents 关联 topic（格式："topic_name|kind"）
        └── DailyReport.market_universe_snapshot = market_universe（序列化）
              ↓
run_after_close()
  └── 加载 DailyReport（含 market_universe_snapshot）
        └── 解析 idea.source_topic_ids 编码字符串，直接生成 canonical tag
              └── 格式："kaipan:{kind}:{topic_name}"
              └── 填充 TraderMemoryItem(tags, topic_source, raw_topic_ids)
```

### 设计决策：不用 hot_topics 查表

**原因：** hot_topics.topic_id 和 topic_constituents.topic_id 来自不同数据源，ID 空间不同（实测重叠率 0%），查表会静默失败。

**新方案：** source_topic_ids 直接存储 "topic_name|kind" 编码字符串，canonical tag 生成时直接解析，不依赖跨数据源查表。

## 3. 实现步骤

### Step 1: DailyReport 新增 market_universe_snapshot 字段

**文件：** `src/schemas/contracts.py`

```python
class DailyReport(BaseModel):
    # ... 现有字段 ...
    market_universe_snapshot: dict[str, Any] | None = None  # MarketUniverse 序列化
```

### Step 2: generate_trade_ideas 关联 topic_constituents 到 source_topic_ids

**文件：** `src/agents/trader_agent/agent.py` — `generate_trade_ideas()`

从 `topic_constituents.constituents` 中匹配 symbol，提取 `topic_name` 和 `kind`，编码为 `"topic_name|kind"` 格式存储。

```python
# 在 generate_trade_ideas() 中，Idea 构建后
topic_entries = [
    f"{tc.topic_name}|{tc.kind}"
    for tc in market_universe.topic_constituents.constituents
    if tc.symbol == symbol and tc.topic_name and tc.kind
]
if topic_entries:
    ideas[-1].source_topic_ids = topic_entries
```

### Step 3: run_pre_market 保存 market_universe_snapshot 到 DailyReport

**文件：** `src/agents/manager_agent/agent.py` — `run_pre_market()`

```python
report = DailyReport(
    ...
    market_universe_snapshot=asdict(market_universe) if market_universe else None,
)
write_json(report_path, report.model_dump())
```

### Step 4: run_after_close 填充 canonical tags

**文件：** `src/agents/manager_agent/agent.py` — `run_after_close()`

直接解析 source_topic_ids 编码字符串生成 canonical tag：

```python
def _build_topic_tags(idea, market_universe_snapshot) -> tuple[list[str], str | None, dict[str, list[str]] | None]:
    # source_topic_ids 格式："topic_name|kind"（编码字符串）
    # 直接解析生成 canonical tags，不查 hot_topics
    canonical_tags = []
    raw_ids = {}

    for encoded in idea.source_topic_ids:
        if "|" not in encoded:
            continue
        topic_name, kind = encoded.rsplit("|", 1)
        if topic_name and kind:
            canonical_tags.append(f"kaipan:{kind}:{topic_name}")
            raw_ids.setdefault("kaipan", []).append(encoded)

    return canonical_tags, "kaipan" if canonical_tags else None, raw_ids or None
```

## 4. Canonical Tag 格式

**格式：** `{provider}:{kind}:{topic_name}`

**示例：**
- `kaipan:concept:芯片`
- `kaipan:industry:半导体`
- `kaipan:stock_sector_v2:农业`

**注意：** kind 来自 topic_constituents 的 kind（stock_sector_v2 / theme_detail / limit_up_reason 等），而非 hot_topics 的 kind（concept / industry / concept_fengkou）。

## 5. 字段语义

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_topic_ids` | `list[str]` | 编码字符串，格式 "topic_name\|kind"，不依赖 hot_topics |
| `raw_topic_ids` | `dict[str, list[str]]` | `{provider: [encoded_str, ...]}`，保留原始编码用于追溯 |

## 6. 依赖关系

| 步骤 | 文件 | 说明 |
|------|------|------|
| Step 1 | `src/schemas/contracts.py` | DailyReport 新增字段 |
| Step 2 | `src/agents/trader_agent/agent.py` | generate_trade_ideas 关联 topic_constituents |
| Step 3 | `src/agents/manager_agent/agent.py` | run_pre_market 保存快照 |
| Step 4 | `src/agents/manager_agent/agent.py` | run_after_close 解析编码生成 tags |

## 7. 测试策略

- `test_daily_report_has_market_universe_snapshot` — 验证字段存在
- `test_trade_idea_source_topic_ids_populated` — 验证 idea 生成时关联 topic（格式 "topic_name\|kind"）
- `test_memory_item_has_canonical_tags` — 验证 run_after_close 写入正确的 tags
- `test_build_topic_tags_uses_encoded_format` — 验证 _build_topic_tags 正确解析编码格式