# 复盘任务持久化一致性修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `ManagerAgent.run_after_close()` 中复盘任务先落盘后补字段导致的持久化任务与真实写回状态不一致问题。

**Architecture:** 调整执行顺序：先完成 memory 写回获取 `memory_id`，再构建任务对象，最后落盘。`_build_review_task` 增加 `memory_id` 可选参数。

**Tech Stack:** Python

---

## 文件变更概览

| 文件 | 操作 |
|------|------|
| `src/agents/manager_agent/agent.py` | 修改 `_build_review_task` 签名，修改 `run_after_close` 调用顺序 |

---

## Task 1: 修改 `_build_review_task` 签名，增加 `memory_id` 参数

**Files:**
- Modify: `src/agents/manager_agent/agent.py:215-255`

- [ ] **Step 1: 修改 `_build_review_task` 函数签名和实现**

将 `src/agents/manager_agent/agent.py:215-255` 的 `_build_review_task` 修改为：

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
    """Convert an underperforming idea into a structured review task.

    P2-109A 闭环: EvaluationResult → ReviewTask created → Trader writes back review note
    """
    trigger_reason = ReviewTriggerReason.loss if return_pct < 0 else ReviewTriggerReason.below_expected
    writeback_status = ReviewWritebackStatus.written if memory_id else ReviewWritebackStatus.pending

    review_details = ReviewTaskDetails(
        review_type="trader_review",
        trigger_reason=trigger_reason,
        source_idea_id=idea.idea_id,
        symbol=idea.symbol,
        trader_id=idea.trader_id,
        evaluation_snapshot=ReviewEvaluationSnapshot(
            idea_id=idea.idea_id,
            symbol=idea.symbol,
            entry_price=round(entry_price, 6),
            current_price=round(current_price, 6),
            return_pct=round(return_pct, 6),
            threshold=round(threshold, 6),
            as_of_date=as_of_date,
        ),
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

**关键变更：**
- 增加 `memory_id: str | None = None` 参数
- `writeback_status` 根据 `memory_id` 是否存在来决定是 `written` 还是 `pending`
- `review_details` 中直接设置 `writeback_status` 和 `memory_id`

---

## Task 2: 调整 `run_after_close` 中的调用顺序

**Files:**
- Modify: `src/agents/manager_agent/agent.py:493-516`

- [ ] **Step 1: 修改复盘任务的创建和落盘顺序**

将 `src/agents/manager_agent/agent.py:493-516` 的复盘任务处理逻辑修改为：

```python
if (self.config.evaluation.loss_trigger and return_pct < 0) or (return_pct < min_ret):
    # 1. 先计算 trigger_reason（供后续使用）
    trigger_reason = ReviewTriggerReason.loss if return_pct < 0 else ReviewTriggerReason.below_expected

    # 2. 创建 memory，获取 memory_id
    memory = self._append_review_memory(
        as_of_date=as_of_date,
        idea=idea,
        entry_price=float(entry_price),
        current_price=float(current_price),
        return_pct=return_pct,
        threshold=min_ret,
        trigger_reason=trigger_reason,
    )
    memory_id = str(memory.memory_id)

    # 3. 构建任务（带 memory_id，此时 writeback_status=written）
    review_task = self._build_review_task(
        idea=idea,
        as_of_date=as_of_date,
        entry_price=float(entry_price),
        current_price=float(current_price),
        return_pct=return_pct,
        threshold=min_ret,
        memory_id=memory_id,
    )

    # 4. 落盘（此时 task 已包含完整信息）
    self._append_task(review_task)
```

**关键变更：**
- `trigger_reason` 提前计算（不再从 `review_task.details` 反向获取）
- `_append_review_memory` 先于 `_append_task` 调用
- `_build_review_task` 携带 `memory_id` 参数
- 删除 lines 514-516 的事后更新逻辑

---

## Task 3: 验证

- [ ] **Step 1: 运行 Python 语法检查**

Run: `cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && python -m py_compile src/agents/manager_agent/agent.py`
Expected: 无输出（编译成功）

- [ ] **Step 2: 检查导入是否正常**

Run: `cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && python -c "from src.agents.manager_agent.agent import ManagerAgent; print('import ok')"`
Expected: `import ok`

- [ ] **Step 3: 确认没有遗留的 "Update writeback status" 注释**

Run: `grep -n "Update writeback status" src/agents/manager_agent/agent.py`
Expected: 无输出（已删除）

---

## 完成后

- 设计文档：`docs/superpowers/specs/2026-04-09-fix-review-task-consistency-design.md`
- 计划文档：`docs/superpowers/plans/2026-04-09-fix-review-task-consistency-plan.md`
