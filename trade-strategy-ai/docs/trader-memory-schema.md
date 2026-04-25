# TraderMemory 数据结构文档

> **最后更新：** 2026-04-25

---

## TraderMemoryItem

交易员记忆的最小单元，存储在 `trader_memory.jsonl`（JSONL 格式，append-only）。

### 核心字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `memory_id` | UUID | 唯一标识，自动生成 |
| `trader_id` | str | 交易员 ID |
| `memory_type` | `TraderMemoryType` | 记忆类型（见下方枚举） |
| `as_of_date` | date | 交易日期（YYYY-MM-DD） |
| `symbol` | str \| None | 交易标的 |
| `title` | str | 记忆标题 |
| `content` | str | 记忆正文内容 |
| `source` | str | 来源，默认 `"manager"` |
| `source_ref` | str \| None | 来源引用（如 URL、文件路径） |
| `tags` | list[str] | 标签列表 |
| `importance` | float | 重要性，0.0~1.0，默认 0.5 |

### 软删除

| 字段 | 类型 | 说明 |
|------|------|------|
| `archived` | bool | 是否归档，默认 False |
| `archived_at` | datetime \| None | 归档时间 |

### 交易上下文关联

| 字段 | 类型 | 说明 |
|------|------|------|
| `idea_id` | UUID \| None | 关联的交易想法 ID |
| `strategy_version_id` | str \| None | 关联的策略版本 ID |
| `ranking_entry_id` | UUID \| None | 关联的 ranking 条目 ID |

### Topic 关联（NTL-S5-006）

| 字段 | 类型 | 说明 |
|------|------|------|
| `topic_source` | str \| None | topic 来源 provider 名称，如 `"kaipan"` |
| `raw_topic_ids` | dict[str, list[str]] \| None | `{provider: [raw_topic_id, ...]}` |

### 盘后评估数据

| 字段 | 类型 | 说明 |
|------|------|------|
| `postmortem_data` | dict \| None | 盘后复盘结论数据（见下方结构） |
| `strategy_adjustment_data` | dict \| None | 策略调整建议数据 |
| `market_regime_data` | dict \| None | 市场状态备注数据 |

### 其他

| 字段 | 类型 | 说明 |
|------|------|------|
| `created_at` | datetime | 创建时间，自动生成 |

---

## TraderMemoryType 枚举

| 枚举值 | 说明 |
|--------|------|
| `success_case` | 成功交易记录 |
| `failure_case` | 失败交易记录 |
| `review_note` | 复盘笔记 |
| `postmortem` | 盘后复盘结论（NTRL-S5-008 新增） |
| `strategy_adjustment` | 策略调整建议（NTRL-S5-008 新增） |
| `market_regime_note` | 市场状态备注（NTRL-S5-008 新增） |

---

## postmortem_data 结构

当 `memory_type` 为 `failure_case` 且完成 LLM 归因后，`postmortem_data` 字段包含：

```json
{
  "idea_id": "UUID",
  "symbol": "SH600519",
  "return_pct": -3.5,
  "mfe": 2.1,
  "mae": 5.8,
  "attribution_source": "llm_corrected",
  "attribution_result": {
    "reason": "失败原因分析...",
    "corrected_reason": "修正后的归因...",
    "confidence": 0.85
  },
  "llm_model": "qwen-plus",
  "processed_at": "2026-04-25T16:30:00Z"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `idea_id` | UUID | 关联的交易想法 ID |
| `symbol` | str | 交易标的 |
| `return_pct` | float | 收益率（%） |
| `mfe` | float | Maximum Favorable Excursion，最大有利偏移 |
| `mae` | float | Maximum Adverse Excursion，最大不利偏移 |
| `attribution_source` | str | 归因来源：`"auto"` \| `"llm_confirmed"` \| `"llm_corrected"` \| `"llm_rejected"` |
| `attribution_result` | dict | LLM 归因结果详情 |
| `llm_model` | str | 使用的 LLM 模型名称 |
| `processed_at` | str | 处理时间（ISO 8601） |

---

## extra 字段

`extra` 字段为自由格式 dict，用于存储附加信息。当前已知用途：

| 路径 | 类型 | 说明 |
|------|------|------|
| `extra["auto_original"]` | dict | LLM 归因前，保留原始 auto attribution 结果（NTRL-S5-012） |

---

## 查询过滤（TraderMemoryFilter）

| 字段 | 类型 | 说明 |
|------|------|------|
| `trader_id` | str | 必须指定 |
| `memory_types` | list[TraderMemoryType] \| None | 按类型过滤 |
| `symbol` | str \| None | 按标的过滤 |
| `date_from` | date \| None | 起始日期 |
| `date_to` | date \| None | 结束日期 |
| `keyword` | str \| None | 搜索 title + content |
| `include_archived` | bool | 是否包含已归档，默认 False |
| `tags` | list[str] \| None | 按标签过滤（匹配任一即可） |
| `strategy_version_id` | str \| None | 按策略版本过滤 |
| `limit` | int | 返回条数限制，默认 50 |
| `offset` | int | 翻页偏移，默认 0 |

---

## 文件格式

存储路径：`{output_dir}/trader_memory.jsonl`

格式：JSONL（每行一个 JSON 对象）

```jsonl
{"memory_id": "...", "memory_type": "failure_case", "trader_id": "trader_001", ...}
{"memory_id": "...", "memory_type": "postmortem", "trader_id": "trader_001", ...}
```

---

## 持久化规则

- **Append-only**：仅通过 `append()` 添加新记录，不直接修改已有记录
- **软删除**：使用 `archive()` 标记删除，不物理删除
- **更新模式**：需要更新时，先 `list_filtered()` 找到记录，修改后调用 `update()` 重写全量文件
