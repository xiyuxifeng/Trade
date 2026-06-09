# Fix: 复盘任务持久化一致性

> 日期：2026-04-09
> 问题来源：`docs/issues.md` 高优先级问题 2

## 目标

修复 `ManagerAgent.run_after_close()` 中复盘任务先落盘、后补字段导致的持久化任务与真实写回状态不一致问题。

## 问题根因

当前代码执行顺序：

```python
# 1. 创建 review_task（writeback_status=pending）
review_task = self._build_review_task(...)

# 2. 立即写入磁盘（此时 writeback_status=pending）
self._append_task(review_task)

# 3. 创建 memory 并获取 memory_id
memory = self._append_review_memory(...)

# 4. 仅更新内存对象的 details（磁盘记录未同步！）
review_task.details["writeback_status"] = ReviewWritebackStatus.written.value
review_task.details["memory_id"] = str(memory.memory_id)
```

**结果：** `agent_tasks.jsonl` 中写入的任务记录缺少 `writeback_status` 和 `memory_id`，无法闭环追踪。

## 方案 A：调整执行顺序

**核心思路：** 先完成 memory 写回，再构建完整任务对象，最后落盘。

### 修改点

**1. 修改 `_build_review_task` 签名**

增加可选参数 `memory_id` 和 `writeback_status`：

```python
def _build_review_task(
    self,
    *,
    idea: "TradeIdea",
    as_of_date: date,
    entry_price: float,
    current_price: float,
    return_pct: float,
    threshold: float,
    memory_id: str | None = None,
) -> AgentTask:
    """Convert an underperforming idea into a structured review task."""
    trigger_reason = ReviewTriggerReason.loss if return_pct < 0 else ReviewTriggerReason.below_expected
    writeback_status = ReviewWritebackStatus.written if memory_id else ReviewWritebackStatus.pending

    review_details = ReviewTaskDetails(
        review_type="trader_review",
        trigger_reason=trigger_reason,
        source_idea_id=idea.idea_id,
        symbol=idea.symbol,
        trader_id=idea.trader_id,
        evaluation_snapshot=ReviewEvaluationSnapshot(...),
        writeback_status=writeback_status,
        memory_id=memory_id,
    )

    return AgentTask(
        type="trader_review",
        title=f"Trader review required: {idea.symbol}",
        trader_id=idea.trader_id,
        idea_id=idea.idea_id,
        details=review_details.model_dump(),
    )
```

**2. 修改 `run_after_close` 中的调用顺序**

```python
# 1. 先创建 memory（获取 memory_id）
trigger_reason = ReviewTriggerReason(...)  # 需要先计算 trigger_reason
memory = self._append_review_memory(
    as_of_date=as_of_date,
    idea=idea,
    entry_price=float(entry_price),
    current_price=float(current_price),
    return_pct=return_pct,
    threshold=min_ret,
    trigger_reason=trigger_reason,  # 需要传入 trigger_reason
)
memory_id = str(memory.memory_id)

# 2. 再构建任务（带 memory_id）
review_task = self._build_review_task(
    idea=idea,
    as_of_date=as_of_date,
    entry_price=float(entry_price),
    current_price=float(current_price),
    return_pct=return_pct,
    threshold=min_ret,
    memory_id=memory_id,
)

# 3. 最后落盘（此时 writeback_status=written，memory_id 已填充）
self._append_task(review_task)
```

**3. `_append_review_memory` 签名调整**

由于 `trigger_reason` 需要先计算才能传给两个方法，可以将 `trigger_reason` 的计算逻辑提取为独立函数，或者直接在 `run_after_close` 中计算后再传入。

`trigger_reason` 的计算：
```python
trigger_reason = ReviewTriggerReason.loss if return_pct < 0 else ReviewTriggerReason.below_expected
```

### 数据流对比

| 步骤 | 当前（错误） | 修复后（正确） |
|------|-------------|---------------|
| 1 | `_build_review_task()` → pending | `_append_review_memory()` → 获取 memory_id |
| 2 | `_append_task()` → 落盘（状态丢失） | `_build_review_task(memory_id)` → 完整对象 |
| 3 | `_append_review_memory()` → 内存更新 | `_append_task()` → 落盘（完整状态） |
| 4 | 更新 details（内存，无磁盘记录） | - |

## 涉及文件

- `src/agents/manager_agent/agent.py`
  - `_build_review_task()`：增加 `memory_id` 参数
  - `_append_review_memory()`：保持不变
  - `run_after_close()`：调整调用顺序

## 验证点

1. 落盘后 `agent_tasks.jsonl` 中的任务记录包含 `memory_id` 和 `writeback_status=written`
2. 单元测试验证顺序正确性
