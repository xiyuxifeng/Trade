# NTL-S5-006 前置：TraderMemory 写入时自动填充 tags 设计

> **目标：** 盘后评估完成后，程序自动将 HotTopic 信息填充到 `TraderMemoryItem` 的 `tags`、`topic_source`、`raw_topic_ids` 字段。

## 1. 背景

NTL-S5-006 已完成检索层扩展（`_apply_filter` 支持 `tags` + `strategy_version_id` 过滤），但记忆写入时没有填充 tags，导致检索无数据可用。

**数据流：**
```
盘前：HotTopicsBuilder.build() → HotTopicsPayload
    ↓
SignalContext.topic_source_ids（记录生成信号时关联的 HotTopic）
    ↓
盘后：TraderMemory 写入 → 需要从 topic_source_ids 提取 canonical tag
```

## 2. Canonical Tag 生成规则

**格式：** `{provider}:{kind}:{topic_name}`

**示例：**
| HotTopic | Canonical Tag |
|----------|--------------|
| kind=concept, topic_name=芯片, provider=kaipan | `kaipan:concept:芯片` |
| kind=industry, topic_name=半导体, provider=kaipan | `kaipan:industry:半导体` |
| kind=concept_fengkou, topic_name=锂电池, provider=kaipan | `kaipan:concept_fengkou:锂电池` |

**规则：**
- `provider` 取固定的 `"kaipan"`（当前只有 kaipan）
- `kind` 来自 HotTopic.kind（`concept` / `industry` / `concept_fengkou`）
- `topic_name` 来自 HotTopic.topic_name（稳定的人类可读名称）
- 用 `topic_name` 而非 `topic_id`，因为 `concept_fengkou` 的 topic_id 是位置标记（不稳定）

## 3. 字段填充

**TraderMemoryItem 三个相关字段：**

| 字段 | 填充值 |
|------|--------|
| `tags` | `list[str]`，包含所有 canonical tag（如 `["kaipan:concept:芯片", "kaipan:concept_fengkou:锂电池"]`） |
| `topic_source` | `"kaipan"`（固定） |
| `raw_topic_ids` | `{provider: raw_topic_id}`（如 `{"kaipan": "881121"}` 或 `{"kaipan": "fengkou_0"}`） |

## 4. 实现位置

**候选入口点：**

1. `ManagerAgent.run_after_close()` — 盘后闭环入口，最直接
2. `PostmortemService.generate()` — 盘后评估生成位置，但职责是生成 postmortem，不应承担记忆写入

**推荐：**
在 `ManagerAgent.run_after_close()` 中，构造 `TraderMemoryItem` 时填充这三个字段。

需要找到当前 TraderMemory 写入的具体位置，确认代码结构后再定。

## 5. 依赖关系

| 依赖 | 来源 |
|------|------|
| `topic_source_ids` | `SignalContext.topic_source_ids`（已有） |
| `TraderMemoryItem` schema | NTL-S5-006 已添加 topic_source / raw_topic_ids |
| HotTopic 数据 | `market_universe` 模块的 `HotTopic` dataclass |

## 6. 注意事项

- `topic_source_ids` 存的是**原始 topic_id 字符串列表**，不是 HotTopic 对象。需要反查 `market_universe_snapshot` 或重新构建 HotTopic 才能取到 `topic_name` 和 `kind`
- `market_universe_snapshot` 中存有完整的 HotTopic 列表，可以在写入时从中查找对应的 `topic_name` 和 `kind`
- 如果 `topic_source_ids` 和 `market_universe_snapshot` 都不完整，fallback 到只用 `topic_source_ids` 中的原始 ID 生成简单 tag（如 `"kaipan:fengkou_0"`）
