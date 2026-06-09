# NTL-S5-006: TraderMemory 检索扩展设计

> **目标：** 扩展 `TraderMemoryStore` 检索能力，支持按 `tags`（topic）、`strategy_version_id`、`symbol` 三个维度精准检索记忆。

## 1. 背景与问题

Stage 5 的最终目标是让盘后评估结果写回记忆，供下次盘前检索使用。NTL-S5-006 解决"检索层怎么按上下文精准取回"的问题。

**Topic 来源：**
- `HotTopic.topic_id` 来自 kaipan API，表示市场热点板块/概念
- `SignalContext.topic_source_ids` 记录生成信号时关联的热点 topic
- 写入记忆时，程序自动从 `SignalContext.topic_source_ids` 填充 `tags` 字段
- 不同 provider 的 topic ID 体系不同，通过 `topic_mapping` 表做 namespace 隔离和 canonical 映射

**检索场景：**
- "今天 AI 板块热，我需要召回历史上关于 AI 题材的成功/失败案例"
- "这个标的用了哪个策略版本当时的调整建议是什么"

## 2. 数据库 schema 变更

### 2.1 新增表 `topic_mapping`

```sql
CREATE TABLE topic_mapping (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,           -- provider 名称，如 "kaipan"
    raw_topic_id VARCHAR(100) NOT NULL,     -- provider 原始 ID
    canonical_name VARCHAR(200) NOT NULL,    -- 统一名称，存入 TraderMemory.tags
    metadata JSONB,                          -- 额外信息（如 score、increase_pct）
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider, raw_topic_id)
);

CREATE INDEX idx_topic_mapping_provider ON topic_mapping(provider);
CREATE INDEX idx_topic_mapping_canonical ON topic_mapping(canonical_name);
```

> **说明：** `topic_mapping` 表由 provider 层维护（不在 NTL-S5-006 实现范围内），本任务只负责建表。

## 3. Schema 扩展

> **注意：** `TraderMemoryItem` 使用 JSONL 存储（不是 PostgreSQL 表），因此 `topic_source` 和 `raw_topic_ids` 作为 Pydantic 字段新增，不涉及数据库迁移。

### 3.1 `TraderMemoryItem` 新增字段

```python
# src/trader_memory/schemas.py

class TraderMemoryItem(BaseModel):
    # ... 现有字段 ...

    # 新增：topic 关联
    topic_source: str | None = None              # provider 名称，如 "kaipan"
    raw_topic_ids: dict[str, str] | None = None  # {provider: raw_topic_id}
```

### 3.2 `TraderMemoryFilter` 新增字段

```python
# src/trader_memory/schemas.py

class TraderMemoryFilter(BaseModel):
    # ... 现有字段 ...

    # 新增：检索过滤
    tags: list[str] | None = None               # 按标签检索（匹配任一 tag 即可）
    strategy_version_id: str | None = None       # 按策略版本检索
```

## 4. 过滤逻辑变更

`TraderMemoryStore._apply_filter` 在现有逻辑基础上新增：

```python
def _apply_filter(self, items: list[TraderMemoryItem], f: TraderMemoryFilter) -> list[TraderMemoryItem]:
    result = [i for i in items if i.trader_id == f.trader_id]

    # ... 现有过滤逻辑（archived、memory_types、symbol、date_range、keyword） ...

    # 新增：tags 过滤（匹配任一 tag）
    if f.tags:
        result = [
            i for i in result
            if i.tags and any(tag in i.tags for tag in f.tags)
        ]

    # 新增：strategy_version_id 过滤
    if f.strategy_version_id:
        result = [
            i for i in result
            if i.strategy_version_id == f.strategy_version_id
        ]

    return result
```

## 5. 检索维度说明

| 维度 | 字段 | 检索方式 | 用途 |
|------|------|---------|------|
| 标的 | `symbol` | 精确匹配 | "关于 000001.SZ 的记忆" |
| 主题 | `tags` | 任意 tag 命中 | "关于 AI 题材的记忆" |
| 版本 | `strategy_version_id` | 精确匹配 | "用了 v_2026_04_25 版本的调整建议" |
| 日期 | `date_from/date_to` | 范围 | "最近一个月的记忆" |
| 类型 | `memory_types` | 枚举匹配 | "只要 postmortem 类型的" |

## 6. 前置依赖（不在本任务范围）

以下模块由独立任务实现，本任务只依赖其 schema 定义：

1. **topic_mapping 表填充规则** — provider 层写入时调用 canonical mapping 逻辑，将 raw_topic_id 映射为 canonical_name 并写入 `topic_mapping` 表
2. **Provider topic 查询接口** — 给定 provider + raw_topic_id，返回 canonical_name + metadata，用于 miss 时自动查询填充
3. **TraderMemory 写入时 tags 填充** — 盘后评估完成后，程序自动从 `SignalContext.topic_source_ids` 映射为 canonical name 填充到 `tags`

## 7. 测试策略

### 7.1 单元测试（test_trader_memory_service.py）

- `test_filter_by_tags` — 验证 tags 过滤（匹配任一 tag）
- `test_filter_by_strategy_version` — 验证 strategy_version_id 过滤
- `test_filter_by_tags_and_symbol` — 验证 tags + symbol 组合过滤
- `test_filter_by_version_and_date_range` — 验证 strategy_version_id + date_range 组合

### 7.2 Schema 测试（test_trader_memory_schemas.py）

- `test_trader_memory_item_with_topic_fields` — 验证 topic_source + raw_topic_ids 字段
- `test_trader_memory_filter_with_tags_and_version` — 验证 filter 新增字段

## 8. 交付物清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/trader_memory/schemas.py` | 修改 | 新增 topic_source、raw_topic_ids、tags、strategy_version_id 字段 |
| `src/trader_memory/service.py` | 修改 | `_apply_filter` 新增过滤逻辑 |
| `src/db/migrations/versions/2026_04_25_0001_add_topic_mapping_table.py` | 新增 | Alembic migration for topic_mapping 表 |
| `tests/unit/trader_memory/test_trader_memory_service.py` | 修改 | 新增 filter 测试 |
| `tests/unit/trader_memory/test_trader_memory_schemas.py` | 修改 | 新增 schema 测试 |
