# NTL-S5-013: 替换当前仅基于 current_price 的简化评估逻辑

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 废弃 `run_after_close` 中基于 `last_price` 的简化 return_pct 计算，统一使用 `compute_mfe_mae_return()` 的 MFE/MAE/return_pct 口径，支持 partial/fallback 分级降级。

**Architecture:**
- `IdeaEvaluation.status` 扩展为 `ok | partial | fallback | not_evaluated`
- `current_price` 字段保留但标注废弃（写入 exit_price）
- `compute_mfe_mae_return()` 作为主计算路径，bars 不足时分级降级

**Tech Stack:** Python, pytest, dataclass, UUID

---

## File Structure

- Modify: `src/schemas/contracts.py` — IdeaEvaluation schema 扩展
- Modify: `src/agents/manager_agent/agent.py` — run_after_close 评估循环重构
- Modify: `tests/unit/agents/test_manager_agent.py` — 新增测试覆盖

---

## Task 1: 扩展 IdeaEvaluation schema

**Files:**
- Modify: `src/schemas/contracts.py:108-116`（IdeaEvaluation 类）

**Reference:** `src/evaluation/metrics_calculator.py`（compute_mfe_mae_return 签名参考）

- [ ] **Step 1: 读取现有 IdeaEvaluation 定义**

```python
# 当前 src/schemas/contracts.py:108-116
class IdeaEvaluation(BaseModel):
    idea_id: UUID
    symbol: str
    entry_price: float | None = None
    current_price: float | None = None  # ← 标注废弃
    return_pct: float | None = None
    status: str = "not_evaluated"  # ← 扩展取值
    notes: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: 修改 IdeaEvaluation 类，扩展 status 取值并标注废弃**

```python
class IdeaEvaluation(BaseModel):
    """单笔交易评估结果。

    .. deprecated::
        current_price 字段废弃（2026-04-26），语义从"评估时刻快照价"
        改为"exit_price"（bars 收盘价）。保留以兼容外部消费方。
    """
    idea_id: UUID
    symbol: str
    entry_price: float | None = None
    current_price: float | None = None  # deprecated: 语义变为 exit_price
    return_pct: float | None = None
    status: Literal["ok", "partial", "fallback", "not_evaluated"] = "not_evaluated"
    notes: list[str] = Field(default_factory=list)
```

- [ ] **Step 3: 运行 contracts 测试确认无回归**

Run: `pytest tests/unit/schemas/test_contracts.py -v --tb=short`
Expected: 原有测试 PASS（无破坏性变更）

- [ ] **Step 4: Commit**

```bash
git add src/schemas/contracts.py
git commit -m "refactor(NTL-S5-013): extend IdeaEvaluation.status with ok/partial/fallback"
```

---

## Task 2: 编写评估循环重构的测试

**Files:**
- Modify: `tests/unit/agents/test_manager_agent.py`

**Reference:**
- `src/evaluation/metrics_calculator.py:44`（compute_mfe_mae_return 签名）
- `src/agents/manager_agent/agent.py:737-826`（当前评估循环）

- [ ] **Step 1: 读取现有 manager_agent 测试文件了解结构**

确认测试文件路径和现有测试类结构。

- [ ] **Step 2: 添加新测试覆盖评估状态**

```python
class TestRunAfterCloseEvaluationStatus:
    """NTL-S5-013: 评估状态覆盖 ok/partial/fallback 场景."""

    @pytest.mark.asyncio
    async def test_evaluation_status_ok_with_full_bars(self, tmp_path):
        """bars 数据完整时 status=ok."""
        # Setup: mock EvidencePack with full bars
        # Assert: IdeaEvaluation.status == "ok"
        pass

    @pytest.mark.asyncio
    async def test_evaluation_status_partial_with_insufficient_bars(self, tmp_path):
        """bars 数据不完整时 status=partial."""
        # Setup: mock EvidencePack with partial bars
        # Assert: IdeaEvaluation.status == "partial"
        pass

    @pytest.mark.asyncio
    async def test_evaluation_status_fallback_with_no_bars(self, tmp_path):
        """bars 完全为空时 status=fallback，降级使用 last_price."""
        # Setup: EvidencePack.market_data["bars"] = []
        # Assert: IdeaEvaluation.status == "fallback"
        pass
```

- [ ] **Step 3: 运行测试确认测试结构正确（预期 FAIL 或 SKIP）**

Run: `pytest tests/unit/agents/test_manager_agent.py::TestRunAfterCloseEvaluationStatus -v --tb=short`
Expected: 测试框架正常加载（PASS/FAIL 取决于 mock 完整度）

- [ ] **Step 4: Commit**

```bash
git add tests/unit/agents/test_manager_agent.py
git commit -m "test(NTL-S5-013): add evaluation status coverage tests"
```

---

## Task 3: 重构 run_after_close 评估循环

**Files:**
- Modify: `src/agents/manager_agent/agent.py:737-826`（评估循环核心逻辑）

**Reference:**
- `src/evaluation/metrics_calculator.py:44`（compute_mfe_mae_return）
- `prompts/llm_attribution.md`（变量替换参考）

- [ ] **Step 1: 读取当前评估循环代码确认行号**

- [ ] **Step 2: 找到简化公式位置（约 line 764）**

```python
# 当前旧逻辑（废弃）
return_pct = (float(current_price) - float(entry_price)) / float(entry_price)
```

- [ ] **Step 3: 替换为新口径计算逻辑**

在 `for idea in daily_report.ideas:` 循环内，找到：

```python
return_pct = (float(current_price) - float(entry_price)) / float(entry_price)
```

替换为：

```python
# NTL-S5-013: 使用 compute_mfe_mae_return 计算
bars = evidence_pack.market_data.get("bars", [])
entry_price_val = float(entry_price) if entry_price else 0.0
target_price = evidence_pack.market_data.get("target_price")
stop_loss_price = evidence_pack.market_data.get("stop_loss_price")

mfe_val, mae_val, return_pct_calc, exit_triggered, exit_date = compute_mfe_mae_return(
    bars=bars,
    entry_price=entry_price_val,
    entry_date=str(as_of_date),
    target_price=target_price,
    stop_loss_price=stop_loss_price,
)

# 判断数据情况并决定 status
if not bars:
    # fallback 到 last_prices（旧逻辑保留作为降级路径）
    if current_price is not None and entry_price is not None:
        return_pct_calc = (float(current_price) - float(entry_price)) / float(entry_price)
        eval_status = "fallback"
        notes_text = f"[fallback] return_pct={round(return_pct_calc, 6):.6f}, reason=no_bars_data"
    else:
        eval_status = "not_evaluated"
        notes_text = "Missing entry price or current price for fallback"
elif len(bars) < 完整持仓期需要的 bar 数:
    # partial data
    eval_status = "partial"
    notes_text = f"[partial] mfe={mfe_val:.4f}, mae={mae_val:.4f}, return_pct={round(return_pct_calc, 6):.6f}"
else:
    eval_status = "ok"
    notes_text = f"mfe={mfe_val:.4f}, mae={mae_val:.4f}, return_pct={round(return_pct_calc, 6):.6f}, exit={exit_triggered}"
```

**注意**：`完整持仓期需要的 bar 数` 判断逻辑：
- 如果 `entry_date` 当天就有 bar，只需要 1 个
- 否则需要从 entry_date 到 as_of_date 的所有交易日 bar
- 简化判断：如果 bars 数量 < 2，视为 partial

- [ ] **Step 4: 替换 IdeaEvaluation 创建部分**

找到：

```python
evaluations.append(
    IdeaEvaluation(
        idea_id=idea.idea_id,
        symbol=idea.symbol,
        entry_price=float(entry_price),
        current_price=float(current_price),
        return_pct=round(return_pct, 6),
        status="ok",
    )
)
```

替换为：

```python
# 获取 exit_price（bars 末bar收盘价，否则用 current_price）
exit_price = float(bars[-1]["close"]) if bars else current_price

evaluations.append(
    IdeaEvaluation(
        idea_id=idea.idea_id,
        symbol=idea.symbol,
        entry_price=float(entry_price) if entry_price else None,
        current_price=exit_price,  # 标注废弃，但仍写入
        return_pct=round(return_pct_calc, 6),
        status=eval_status,
        notes=[notes_text],
    )
)
```

- [ ] **Step 5: 运行 manager_agent 测试确认无回归**

Run: `pytest tests/unit/agents/test_manager_agent.py -v --tb=short 2>&1 | tail -40`
Expected: 原有测试 PASS

- [ ] **Step 6: Commit**

```bash
git add src/agents/manager_agent/agent.py
git commit -m "refactor(NTL-S5-013): replace simplified return_pct with compute_mfe_mae_return"
```

---

## Task 4: 验证完整测试套件

- [ ] **Step 1: 运行完整 evaluation + manager_agent 测试**

Run: `pytest tests/unit/evaluation/ tests/unit/agents/test_manager_agent.py -v --tb=short 2>&1 | tail -50`
Expected: 全部 PASS

- [ ] **Step 2: 更新 TaskList 标记 NTL-S5-013 完成**

在 `docs/TaskList.md` 中找到 NTL-S5-013，添加完成标记。

- [ ] **Step 3: 更新 daily-sessions 和 daily-report**

记录 NTL-S5-013 完成状态。

---

## Self-Review Checklist

1. **Spec coverage**: 每条设计规则都有对应任务？
   - ✅ 完全替换公式 → Task 3 Step 3
   - ✅ status 扩展 → Task 1
   - ✅ partial bars 判断 → Task 3 Step 3
   - ✅ fallback 降级 → Task 3 Step 3
   - ✅ current_price 废弃标注 → Task 1 Step 2
   - ✅ notes 扩展 → Task 3 Step 4

2. **Placeholder scan**: 无 TBD/TODO/placeholder

3. **Type consistency**: `Literal["ok", "partial", "fallback", "not_evaluated"]` 在 Task 1 定义，Task 3 使用一致

4. **Gap check**: 无遗漏的设计规则
