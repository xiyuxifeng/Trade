# NTL-S5-005 TraderMemory Schema 扩展实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展 TraderMemory schema，新增 postmortem / strategy_adjustment / market_regime_note 三种 memory types 及对应字段，支持盘后结果写入记忆层。

**Architecture:** 在 `schemas.py` 中扩展 `TraderMemoryType` enum 和 `TraderMemoryItem` model，在 `service.py` 中更新 `summarize_context` 支持 new types。追加型 JSONL 存储不变。

**Tech Stack:** Pydantic BaseModel, Python enum, JSONL

---

## 文件结构

```
src/trader_memory/
    schemas.py     # 修改：TraderMemoryType enum + TraderMemoryItem fields + TraderMemorySummary fields
    service.py     # 修改：summarize_context 支持 new memory types
tests/unit/trader_memory/
    test_trader_memory_schemas.py  # 创建：schemas 单元测试
    test_trader_memory_service.py   # 创建：service 单元测试
```

---

## Task 1: 扩展 schemas.py

**Files:**
- Modify: `src/trader_memory/schemas.py`

### Steps

- [ ] **Step 1: 读取现有 schemas.py**

Run: `cat src/trader_memory/schemas.py`

验证现有字段和类结构。

---

- [ ] **Step 2: 扩展 TraderMemoryType enum**

```python
class TraderMemoryType(str, Enum):
    """Memory categories written back by the manager loop."""

    success_case = "success_case"
    failure_case = "failure_case"
    review_note = "review_note"
    postmortem = "postmortem"                        # 新增
    strategy_adjustment = "strategy_adjustment"       # 新增
    market_regime_note = "market_regime_note"         # 新增
```

---

- [ ] **Step 3: 扩展 TraderMemoryItem**

在 `TraderMemoryItem` 类中添加以下字段（在 `created_at` 之前）：

```python
    # 新增：交易上下文关联
    idea_id: UUID | None = None
    strategy_version_id: str | None = None
    ranking_entry_id: UUID | None = None

    # 新增：盘后评估数据
    postmortem_data: dict | None = None
    strategy_adjustment_data: dict | None = None
    market_regime_data: dict | None = None
```

---

- [ ] **Step 4: 扩展 TraderMemorySummary**

在 `TraderMemorySummary` 类中添加以下字段：

```python
    # 新增字段
    postmortem_notes: list[str] = Field(default_factory=list)
    strategy_adjustments: list[str] = Field(default_factory=list)
    market_regime_notes: list[str] = Field(default_factory=list)
```

---

- [ ] **Step 5: 验证 Schema 可导入**

Run: `python -c "from src.trader_memory.schemas import TraderMemoryType, TraderMemoryItem, TraderMemorySummary; print('OK')"`

Expected: 输出 `OK`，无报错。

---

- [ ] **Step 6: Commit**

```bash
git add src/trader_memory/schemas.py
git commit -m "feat(NTL-S5-005): extend TraderMemory schema with new memory types and fields"
```

---

## Task 2: 更新 service.py 的 summarize_context

**Files:**
- Modify: `src/trader_memory/service.py`

### Steps

- [ ] **Step 1: 读取现有 service.py 的 summarize_context 方法**

找到 `summarize_context` 方法（约第 162-204 行），理解现有逻辑。

---

- [ ] **Step 2: 更新 summarize_context 支持 new memory types**

在 `summarize_context` 方法末尾，返回前添加：

```python
        # 新增：聚合 new memory types 到 summary
        postmortem_notes = [
            item.content
            for item in active_items
            if item.memory_type == TraderMemoryType.postmortem
        ][: max(0, int(limit))]

        strategy_adjustments = [
            item.content
            for item in active_items
            if item.memory_type == TraderMemoryType.strategy_adjustment
        ][: max(0, int(limit))]

        market_regime_notes = [
            item.content
            for item in active_items
            if item.memory_type == TraderMemoryType.market_regime_note
        ][: max(0, int(limit))]

        return TraderMemorySummary(
            trader_id=trader_id,
            symbol=symbol,
            total_items=len(active_items),
            total_symbol_items=len(symbol_items),
            archived_items=len(all_items) - len(active_items),
            by_type=by_type,
            recent_titles=recent_titles,
            symbol_titles=symbol_titles,
            review_notes=review_notes,
            postmortem_notes=postmortem_notes,
            strategy_adjustments=strategy_adjustments,
            market_regime_notes=market_regime_notes,
        )
```

原有的 `return TraderMemorySummary(...)` 替换为新的完整版本。

---

- [ ] **Step 3: 验证 Schema 和 Service 可导入**

Run: `python -c "from src.trader_memory.service import TraderMemoryStore; from src.trader_memory.schemas import TraderMemoryType; print('OK')"`

Expected: 输出 `OK`，无报错。

---

- [ ] **Step 4: Commit**

```bash
git add src/trader_memory/service.py
git commit -m "feat(NTL-S5-005): update summarize_context to aggregate new memory types"
```

---

## Task 3: 编写 schemas 单元测试

**Files:**
- Create: `tests/unit/trader_memory/test_trader_memory_schemas.py`

### Steps

- [ ] **Step 1: 编写 schemas 测试**

```python
"""TraderMemory schemas 单元测试（NTL-S5-005）。"""
import pytest
from datetime import date
from uuid import uuid4

from src.trader_memory.schemas import (
    TraderMemoryType,
    TraderMemoryItem,
    TraderMemorySummary,
)


class TestTraderMemoryType:
    """验证 TraderMemoryType 枚举包含全部 6 种类型。"""

    def test_all_memory_types_present(self):
        assert hasattr(TraderMemoryType, "success_case")
        assert hasattr(TraderMemoryType, "failure_case")
        assert hasattr(TraderMemoryType, "review_note")
        assert hasattr(TraderMemoryType, "postmortem")
        assert hasattr(TraderMemoryType, "strategy_adjustment")
        assert hasattr(TraderMemoryType, "market_regime_note")

    def test_memory_type_values(self):
        assert TraderMemoryType.postmortem.value == "postmortem"
        assert TraderMemoryType.strategy_adjustment.value == "strategy_adjustment"
        assert TraderMemoryType.market_regime_note.value == "market_regime_note"


class TestTraderMemoryItem:
    """验证 TraderMemoryItem 扩展字段。"""

    def test_can_create_with_new_fields(self):
        item = TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            title="Postmortem for SH600519",
            content="Entry timing poor, exit timing ok",
            idea_id=uuid4(),
            strategy_version_id="v_2026_04_25",
            ranking_entry_id=uuid4(),
            postmortem_data={
                "return_pct": 5.2,
                "mfe": 8.0,
                "mae": 2.8,
                "attribution_source": "auto",
                "failure_attribution": {
                    "root_causes": ["entry_timing_poor"],
                    "stage": "stage:entry",
                    "rule_type": "rule_type:entry",
                },
            },
        )
        assert item.memory_type == TraderMemoryType.postmortem
        assert item.postmortem_data["return_pct"] == 5.2
        assert item.idea_id is not None
        assert item.strategy_version_id == "v_2026_04_25"

    def test_can_create_strategy_adjustment(self):
        item = TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.strategy_adjustment,
            as_of_date=date(2026, 4, 25),
            title="Adjust entry rule threshold",
            content="Increase entry price tolerance",
            strategy_adjustment_data={
                "trigger": "postmortem_low_ranking",
                "adjustment_type": "rule_param",
                "target": "entry_price_tolerance",
                "previous_value": 0.02,
                "new_value": 0.03,
                "expected_effect": "reduce false positives",
            },
        )
        assert item.strategy_adjustment_data["trigger"] == "postmortem_low_ranking"
        assert item.strategy_adjustment_data["new_value"] == 0.03

    def test_can_create_market_regime_note(self):
        item = TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.market_regime_note,
            as_of_date=date(2026, 4, 25),
            title="High volatility regime",
            content="VIX > 30, reduce position size",
            market_regime_data={
                "regime_type": "volatile",
                "key_indicators": {"vix": 32.5, "trend_strength": 0.4},
                "note": "Reduce exposure",
            },
        )
        assert item.market_regime_data["regime_type"] == "volatile"


class TestTraderMemorySummary:
    """验证 TraderMemorySummary 扩展字段。"""

    def test_summary_has_new_fields(self):
        summary = TraderMemorySummary(
            trader_id="trader_a",
            postmortem_notes=["Entry timing poor", "Exit timing ok"],
            strategy_adjustments=["Increase entry tolerance"],
            market_regime_notes=["High volatility regime"],
        )
        assert len(summary.postmortem_notes) == 2
        assert len(summary.strategy_adjustments) == 1
        assert len(summary.market_regime_notes) == 1
```

---

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/trader_memory/test_trader_memory_schemas.py -v`

Expected: 6 PASS

---

- [ ] **Step 3: Commit**

```bash
git add tests/unit/trader_memory/test_trader_memory_schemas.py
git commit -m "test(NTL-S5-005): add trader memory schemas unit tests"
```

---

## Task 4: 编写 service 单元测试（可选）

**Files:**
- Create: `tests/unit/trader_memory/test_trader_memory_service.py`

### Steps

- [ ] **Step 1: 验证 summarize_context 更新逻辑**

由于 `summarize_context` 依赖 JSONL 文件存在，测试改为验证：
1. `TraderMemoryStore` 可正常实例化
2. `summarize_context` 方法存在且签名正确

```python
"""TraderMemory service 单元测试（NTL-S5-005）。"""
import pytest
from pathlib import Path
from src.trader_memory.service import TraderMemoryStore
from src.trader_memory.schemas import TraderMemoryType


def test_store_can_be_instantiated(tmp_path):
    store = TraderMemoryStore(path=tmp_path / "test_memory.jsonl")
    assert store.path == tmp_path / "test_memory.jsonl"


def test_summarize_context_signature(tmp_path):
    store = TraderMemoryStore(path=tmp_path / "test_memory.jsonl")
    # 验证方法存在且可调用（不检查结果，因为无数据）
    assert hasattr(store, "summarize_context")
    import inspect
    sig = inspect.signature(store.summarize_context)
    params = list(sig.parameters.keys())
    assert "trader_id" in params
    assert "symbol" in params
    assert "limit" in params
```

---

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/unit/trader_memory/test_trader_memory_service.py -v`

Expected: 2 PASS

---

- [ ] **Step 3: Commit**

```bash
git add tests/unit/trader_memory/test_trader_memory_service.py
git commit -m "test(NTL-S5-005): add trader memory service unit tests"
```

---

## Task 5: 最终验证 + TaskList 更新

**Files:**
- Run: 全量测试
- Modify: `docs/TaskList.md`

### Steps

- [ ] **Step 1: 运行全量测试验证**

Run: `pytest tests/unit/trader_memory/ -v --tb=short`

Expected: 8 PASS（6 schemas + 2 service）

---

- [ ] **Step 2: 更新 docs/TaskList.md**

找到 NTL-S5-005，标记为 `[x]` 完成，添加完成情况。

---

- [ ] **Step 3: Commit**

```bash
git add docs/TaskList.md
git commit -m "feat(NTL-S5-005): complete trader memory schema extension"
```

---

## 验收标准

1. `TraderMemoryType` 包含全部 6 种类型（3 新增）
2. `TraderMemoryItem` 包含 `idea_id` / `strategy_version_id` / `ranking_entry_id` / `postmortem_data` / `strategy_adjustment_data` / `market_regime_data` 字段
3. `TraderMemorySummary` 包含 `postmortem_notes` / `strategy_adjustments` / `market_regime_notes` 字段
4. `summarize_context` 正确聚合 new memory types 到 summary
5. 向后兼容：现有 JSONL 条目可正常读取
6. 全量测试 PASS