# NTL-S5-012 差评触发 LLM 归因设计

> **日期：** 2026-04-25
> **任务：** NTL-S5-012 | 差评触发 LLM 归因并写回记忆
> **状态：** 已批准

---

## 目标

当 `run_after_close` 生成的 `return_pct` 低于 `min_ret` 阈值时，触发 LLM 归因分析，将归因结果合并到同一条 `failure_case` memory 条目中。

---

## 核心概念

| 概念 | 说明 |
|------|------|
| `failure_case` | MemoryType，表示交易失败记录 |
| `postmortem_data` | 复盘数据（mfe/mae/return_pct 等） |
| `auto_original` | 原始 auto attribution，保留在 extra 中 |
| `attribution_source` | `"auto"` \| `"llm_confirmed"` \| `"llm_corrected"` \| `"llm_rejected"` |
| `min_ret` | 差评阈值，与 NTL-S5-011 使用相同阈值（`config.evaluation.min_ret`） |

---

## 触发条件

- `return_pct < min_ret`（min_ret 来自 `config.evaluation.min_ret`，与 NTL-S5-011 相同阈值）
- 触发时机：`run_after_close` 中 `compute_mfe_mae_return` 计算完成后
- 触发后：创建 `postmortem_task` 异步执行 LLM 归因（不阻塞主流程）

---

## TraderMemoryStore 改动

### 新增 `update()` 方法

基于 `archive()` 已有的 load+modify+save 模式，新增通用 update 方法：

```python
def update(self, memory_id: UUID, updated_item: TraderMemoryItem) -> bool:
    """更新指定 memory 条目。返回 True if found and updated."""
    items = self._load_all()
    for i, item in enumerate(items):
        if item.memory_id == memory_id:
            items[i] = updated_item
            self._save_all(items)
            return True
    return False
```

---

## postmortem_tasks 改动

### `handle_postmortem_analysis` 逻辑调整

**Before（NTL-S5-008）：**
```python
store.append(memory)  # 创建新条目
```

**After（NTL-S5-012）：**
```python
# 找到对应的 failure_case memory
f = TraderMemoryFilter(
    trader_id=trader_id,
    memory_types=[TraderMemoryType.failure_case],
    symbol=symbol,
    date_from=as_of_date,
    date_to=as_of_date,
)
failure_cases = store.list_filtered(f)

if failure_cases:
    # 原地更新同一条目
    failure_case = failure_cases[0]
    updated = failure_case.model_copy(deep=True)
    updated.postmortem_data = postmortem_data
    updated.extra = failure_case.extra or {}
    updated.extra["auto_original"] = auto_attribution_result
    store.update(failure_case.memory_id, updated)
else:
    # Fallback: append 新条目（兼容未创建 failure_case 的边界情况）
    store.append(memory)
```

---

## LLM 归因

### LLM Client

复用 `src/llm/client.py`（Protocol 接口 + LLMClient 实现，已存在）

### Prompt 策略（Option A）

完整上下文一次性发送，不做多轮：

```
## 交易想法
{summarized trade_idea}

## 市场数据（1d 日线）
{bars JSON}

## 策略规则快照
{rules_snapshot}

## 自动归因结果
{auto_attribution_result}

## 任务
分析失败原因，给出修正归因。
```

### 归因结果映射

| LLM 结论 | attribution_source |
|----------|-------------------|
| 与 auto 一致 | `"llm_confirmed"` |
| 修正了 auto | `"llm_corrected"` |
| 拒绝归因 | `"llm_rejected"` |

归因结果写入 `postmortem_data`，原始 auto 结果保留在 `extra["auto_original"]`。

---

## 数据流

```
run_after_close(as_of_date=T日)
│
├── for idea in daily_report.ideas:
│   ├── return_pct = (current_price - entry_price) / entry_price
│   ├── 【NTL-S5-012 新增】if return_pct < min_ret:
│   │     ├── 创建 failure_case memory
│   │     └── 创建 postmortem_task（异步）
│   │
│   ├── 【NTL-S5-011】add_entry_from_metrics()
│   └── ...
│
├── postmortem_task 异步执行:
│   └── handle_postmortem_analysis():
│         ├── 找到 failure_case memory（date + symbol 定位）
│         ├── 构造完整 LLM prompt
│         ├── 调用 LLM → 归因结果
│         ├── store.update(failure_case.memory_id, updated)
│         │     └── 同一 entry: failure_case + postmortem_data
│         └── 完成
│
└── EvaluationResult
```

---

## 验收标准

1. `return_pct < min_ret` 时，failure_case memory 被原地更新（不是新增条目）
2. 更新后同一条目包含 `postmortem_data` 和 `extra["auto_original"]`
3. `attribution_source` 正确标记为 `"llm_confirmed"` / `"llm_corrected"` / `"llm_rejected"`
4. `run_after_close` 主流程不被 LLM 归因阻塞
5. 可以通过 `TraderMemoryStore.list_filtered()` 查询到包含完整归因的 memory
6. ranking 生成（NTL-S5-011）不受影响
