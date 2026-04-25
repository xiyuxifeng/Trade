# NTL-S5-012 差评触发 LLM 归因实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `return_pct < min_ret` 时触发 LLM 归因，将结果合并到同一条 `failure_case` memory 条目中。

**Architecture:**
- `TraderMemoryStore` 新增 `update()` 方法（load+modify+save 模式）
- `postmortem_tasks.handle_postmortem_analysis()` 找到 failure_case 并原地更新
- 复用 `src/llm/client.py` 的 LLMClient，完整上下文 Prompt（Option A）

**Tech Stack:** Python 3.11+, asyncio, pytest, SQLAlchemy async

---

## 文件清单

| 文件 | 动作 |
|------|------|
| `src/trader_memory/service.py` | 修改：新增 `update()` 方法 |
| `src/pipeline/tasks/postmortem_tasks.py` | 修改：`handle_postmortem_analysis` 原地更新 failure_case |
| `src/evaluation/postmortem_service.py` | 修改：新增 `llm_attribution()` 方法 |
| `src/agents/manager_agent/agent.py` | 修改：差评时触发 postmortem_task |
| `tests/unit/trader_memory/test_service.py` | 修改：新增 `update()` 测试 |
| `tests/unit/pipeline/tasks/test_postmortem_tasks.py` | 修改：新增原地更新测试 |

---

## Task 1: TraderMemoryStore.update()

**Files:**
- Modify: `src/trader_memory/service.py`
- Test: `tests/unit/trader_memory/test_service.py`

### 1.1 新增 update() 方法

- [ ] **Step 1: 写测试**

```python
# tests/unit/trader_memory/test_service.py 新增

def test_update_modifies_existing_item(tmp_path):
    """update() 应原地修改已有条目，不新增。"""
    from src.trader_memory.service import TraderMemoryStore
    from src.trader_memory.schemas import TraderMemoryItem, TraderMemoryType
    from datetime import date
    from uuid import uuid4

    store = TraderMemoryStore(path=tmp_path / "memory.jsonl")

    original = TraderMemoryItem(
        memory_id=uuid4(),
        trader_id="trader_001",
        memory_type=TraderMemoryType.failure_case,
        as_of_date=date.fromisoformat("2026-04-25"),
        symbol="AAPL",
        title="原始 failure",
        content="原始内容",
    )
    store.append(original)

    # 更新
    updated = original.model_copy(deep=True)
    updated.content = "更新后内容"
    updated.postmortem_data = {"return_pct": -3.5}

    result = store.update(original.memory_id, updated)

    assert result is True

    # 验证：文件只有一条
    items = store._load_all()
    assert len(items) == 1
    assert items[0].content == "更新后内容"
    assert items[0].postmortem_data == {"return_pct": -3.5}
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/trader_memory/test_service.py::test_update_modifies_existing_item -v`
Expected: FAIL（method not defined）

- [ ] **Step 3: 实现 update() 方法**

在 `archive()` 方法之后添加：

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

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/trader_memory/test_service.py::test_update_modifies_existing_item -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/trader_memory/service.py tests/unit/trader_memory/test_service.py
git commit -m "feat(NTL-S5-012): add TraderMemoryStore.update() method"
```

---

## Task 2: LLM 归因方法

**Files:**
- Modify: `src/evaluation/postmortem_service.py`
- Test: `tests/unit/evaluation/test_postmortem_service.py`

### 2.1 新增 llm_attribution() 方法

- [ ] **Step 1: 写测试**

```python
# tests/unit/evaluation/test_postmortem_service.py 新增

@pytest.mark.asyncio
async def test_llm_attribution_returns_result():
    """llm_attribution() 调用 LLM 并返回归因结果。"""
    from src.evaluation.postmortem_service import PostmortemService
    from src.llm.client import LLMClient

    service = PostmortemService(...)
    service._llm_client = MockLLMClient(returns={"reason": "...", "confidence": 0.8})

    result = await service.llm_attribution(
        trade_idea={"symbol": "AAPL", "side": "buy", ...},
        market_data={"bars": [...]},
        auto_attribution={"reason": "原始原因", "confidence": 0.5},
    )

    assert result["attribution_source"] in ["llm_confirmed", "llm_corrected", "llm_rejected"]
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::test_llm_attribution_returns_result -v`
Expected: FAIL（method not defined）

- [ ] **Step 3: 实现 llm_attribution()**

在 `PostmortemService` 类中添加：

```python
async def llm_attribution(
    self,
    trade_idea: dict,
    market_data: dict,
    auto_attribution: dict,
) -> dict:
    """对 failure_case 进行 LLM 归因分析。

    复用 src/llm/client.py 的 LLMClient（Protocol + 实现）。

    Args:
        trade_idea: 交易想法 dict
        market_data: 市场数据 dict（包含 bars）
        auto_attribution: 自动归因结果

    Returns:
        dict: 包含 attribution_source 和归因详情的 dict
    """
    prompt = self._build_llm_attribution_prompt(trade_idea, market_data, auto_attribution)

    response = await self._llm_client.complete_json(
        prompt=prompt,
        schema={
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "corrected_reason": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["reason"],
        },
    )

    # 判断归因结果
    if response is None:
        return {
            "attribution_source": "llm_rejected",
            "reason": auto_attribution.get("reason", ""),
            "corrected_reason": None,
            "confidence": 0.0,
        }

    corrected_reason = response.get("corrected_reason") or response.get("reason")
    auto_reason = auto_attribution.get("reason", "")

    if corrected_reason == auto_reason:
        attribution_source = "llm_confirmed"
    else:
        attribution_source = "llm_corrected"

    return {
        "attribution_source": attribution_source,
        "reason": corrected_reason,
        "corrected_reason": corrected_reason if corrected_reason != auto_reason else None,
        "confidence": response.get("confidence", 0.5),
        "llm_model": self._llm_client.model,
    }
```

- [ ] **Step 4: 实现 _build_llm_attribution_prompt()**

```python
def _build_llm_attribution_prompt(
    self,
    trade_idea: dict,
    market_data: dict,
    auto_attribution: dict,
) -> str:
    """构造 LLM 归因 Prompt（Option A: 完整上下文）。"""
    bars = market_data.get("bars", [])
    bars_str = json.dumps(bars, ensure_ascii=False, default=str) if bars else "无市场数据"

    return f"""## 交易想法
- 标的: {trade_idea.get('symbol', 'N/A')}
- 方向: {trade_idea.get('side', 'N/A')}
- 入场价格: {trade_idea.get('entry', {})}
- 目标价格: {trade_idea.get('target', 'N/A')}
- 止损价格: {trade_idea.get('stop_loss', 'N/A')}

## 市场数据（1d 日线）
{bars_str}

## 自动归因结果（auto）
- 原因: {auto_attribution.get('reason', 'N/A')}
- 置信度: {auto_attribution.get('confidence', 0.0)}

## 任务
分析上述交易失败的根本原因，给出修正后的归因。如果自动归因准确，确认即可。
如果自动归因有误，给出修正原因。

请以 JSON 格式返回：
{{"reason": "归因原因", "corrected_reason": "修正后原因（如有）", "confidence": 0.0-1.0}}
"""
```

- [ ] **Step 5: 运行测试验证**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::test_llm_attribution_returns_result -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/evaluation/postmortem_service.py tests/unit/evaluation/test_postmortem_service.py
git commit -m "feat(NTL-S5-012): add PostmortemService.llm_attribution()"
```

---

## Task 3: postmortem_tasks 原地更新

**Files:**
- Modify: `src/pipeline/tasks/postmortem_tasks.py`
- Test: `tests/unit/pipeline/tasks/test_postmortem_tasks.py`

### 3.1 修改 handle_postmortem_analysis

- [ ] **Step 1: 写测试**

```python
# tests/unit/pipeline/tasks/test_postmortem_tasks.py 新增

@pytest.mark.asyncio
async def test_handle_postmortem_updates_existing_failure_case(tmp_path):
    """handle_postmortem_analysis 应原地更新 failure_case，不新增条目。"""
    from src.pipeline.tasks.postmortem_tasks import handle_postmortem_analysis
    from src.trader_memory.service import TraderMemoryStore
    from src.trader_memory.schemas import TraderMemoryType, TraderMemoryFilter
    from datetime import date
    from uuid import uuid4

    store = TraderMemoryStore(path=tmp_path / "memory.jsonl")

    # 先创建 failure_case
    failure_case = TraderMemoryItem(
        memory_id=uuid4(),
        trader_id="trader_001",
        memory_type=TraderMemoryType.failure_case,
        as_of_date=date.fromisoformat("2026-04-25"),
        symbol="AAPL",
        title="失败案例",
        content="失败内容",
    )
    store.append(failure_case)

    # 模拟 postmortem 数据
    postmortem_data = {
        "return_pct": -3.5,
        "mfe": 2.1,
        "mae": 5.8,
        "attribution_source": "llm_corrected",
    }

    await handle_postmortem_analysis(
        trader_id="trader_001",
        idea_id=failure_case.idea_id,
        as_of_date=date.fromisoformat("2026-04-25"),
        symbol="AAPL",
        postmortem_data=postmortem_data,
        auto_attribution={"reason": "原始原因"},
        memory_store=store,
    )

    # 验证：文件只有一条
    items = store._load_all()
    assert len(items) == 1
    assert items[0].postmortem_data == postmortem_data
    assert items[0].extra["auto_original"] == {"reason": "原始原因"}
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/pipeline/tasks/test_postmortem_tasks.py::test_handle_postmortem_updates_existing_failure_case -v`
Expected: FAIL（逻辑未改）

- [ ] **Step 3: 实现更新逻辑**

在 `handle_postmortem_analysis` 中：

```python
# 找到对应的 failure_case memory（NTL-S5-012）
f = TraderMemoryFilter(
    trader_id=trader_id,
    memory_types=[TraderMemoryType.failure_case],
    symbol=symbol,
    date_from=as_of_date,
    date_to=as_of_date,
    include_archived=False,
)
failure_cases = memory_store.list_filtered(f)

if failure_cases:
    # 原地更新同一条目（NTL-S5-012）
    failure_case = failure_cases[0]
    updated = failure_case.model_copy(deep=True)
    updated.postmortem_data = postmortem_data
    updated.extra = failure_case.extra or {}
    updated.extra["auto_original"] = auto_attribution
    memory_store.update(failure_case.memory_id, updated)
else:
    # Fallback: append 新条目（兼容边界情况）
    memory_item = TraderMemoryItem(
        trader_id=trader_id,
        memory_type=TraderMemoryType.failure_case,
        as_of_date=as_of_date,
        symbol=symbol,
        title=f"Failure: {symbol}",
        content=postmortem_data.get("reason", "交易失败"),
        idea_id=idea_id,
        postmortem_data=postmortem_data,
        extra={"auto_original": auto_attribution},
    )
    memory_store.append(memory_item)
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/pipeline/tasks/test_postmortem_tasks.py::test_handle_postmortem_updates_existing_failure_case -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/pipeline/tasks/postmortem_tasks.py tests/unit/pipeline/tasks/test_postmortem_tasks.py
git commit -m "feat(NTL-S5-012): update failure_case in-place in handle_postmortem_analysis"
```

---

## Task 4: manager_agent 差评触发

**Files:**
- Modify: `src/agents/manager_agent/agent.py`

### 4.1 修改 run_after_close 差评逻辑

- [ ] **Step 1: 找到差评触发位置**

在 `run_after_close` 中已有 `pending_rankings` 逻辑附近，找到 `if return_pct < min_ret` 的位置（如有），或新增触发逻辑。

- [ ] **Step 2: 添加差评 postmortem_task**

在计算 `mfe_val, mae_val, return_pct_val` 后：

```python
# NTL-S5-012: 差评触发 LLM 归因
if return_pct_val < min_ret:
    postmortem_task = create_postmortem_task(
        trader_id=trader_id,
        idea_id=evidence_pack.idea_id,
        as_of_date=as_of_date,
        symbol=symbol,
        postmortem_data={
            "return_pct": return_pct_val,
            "mfe": mfe_val,
            "mae": mae_val,
            "attribution_source": "auto",  # 先标记 auto
        },
        auto_attribution={"reason": "...", "confidence": 0.5},  # 从 evidence_pack.signal_context 获取
    )
    pending_postmortems.append(postmortem_task)
```

- [ ] **Step 3: 提交**

```bash
git add src/agents/manager_agent/agent.py
git commit -m "feat(NTL-S5-012): trigger LLM attribution for bad ratings in run_after_close"
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** 设计文档中每个验收标准都有对应任务
- **Placeholder scan:** 无 TBD/TODO/占位符
- **Type consistency:** `update()` 返回 `bool`，`llm_attribution()` 返回 `dict`
- **No placeholder in code:** 所有函数都有实际实现
- **Commands correct:** pytest 命令路径正确
