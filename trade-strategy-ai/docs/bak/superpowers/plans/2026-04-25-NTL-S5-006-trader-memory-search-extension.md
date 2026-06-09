# NTL-S5-006: TraderMemory 检索扩展实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展 `TraderMemoryStore` 检索能力，支持按 `tags`（topic）、`strategy_version_id`、`symbol` 三个维度检索记忆。

**Architecture:**
- `TraderMemoryItem` 新增 `topic_source`、`raw_topic_ids` 字段（Python schema，JSONL 存储）
- `TraderMemoryFilter` 新增 `tags`、`strategy_version_id` 过滤字段
- `_apply_filter` 实现按 tags 匹配（任一命中）+ strategy_version_id 精确匹配
- `topic_mapping` 表（PostgreSQL）存储 provider → canonical name 映射

**Tech Stack:** Python (Pydantic), PostgreSQL (Alembic), JSONL

---

## 文件清单

| 文件 | 变更 |
|------|------|
| `src/trader_memory/schemas.py` | 修改：TraderMemoryItem + TraderMemoryFilter 新增字段 |
| `src/trader_memory/service.py` | 修改：_apply_filter 新增过滤逻辑 |
| `src/db/migrations/versions/YYYY_MM_DD_XXXX_add_topic_mapping_table.py` | 新增：topic_mapping 表 |
| `tests/unit/trader_memory/test_trader_memory_service.py` | 修改：新增 filter 测试 |
| `tests/unit/trader_memory/test_trader_memory_schemas.py` | 修改：新增 schema 测试 |
| `docs/superpowers/specs/YYYY-MM-DD-NTL-S5-006-trader-memory-search-extension-design.md` | 修正：删除错误的 trader_memory migration 描述 |

---

## Task 1: 更新 TraderMemoryItem 和 TraderMemoryFilter schema

**Files:**
- Modify: `src/trader_memory/schemas.py`

- [ ] **Step 1: 添加 TraderMemoryItem 新增字段的测试**

```python
# tests/unit/trader_memory/test_trader_memory_schemas.py

def test_trader_memory_item_with_topic_fields():
    item = TraderMemoryItem(
        trader_id="trader_a",
        memory_type=TraderMemoryType.postmortem,
        as_of_date=date(2026, 4, 25),
        title="postmortem entry timing",
        content="Entry timing poor for SH600519",
        topic_source="kaipan",
        raw_topic_ids={"kaipan": "AI_chip_001", "akshare": "AISemi"},
        tags=["AI_chip", "半导体"],
    )
    assert item.topic_source == "kaipan"
    assert item.raw_topic_ids == {"kaipan": "AI_chip_001", "akshare": "AISemi"}
    assert "AI_chip" in item.tags
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/trader_memory/test_trader_memory_schemas.py::test_trader_memory_item_with_topic_fields -v`
Expected: FAIL with "topic_source" not found

- [ ] **Step 3: 更新 TraderMemoryItem 添加新字段**

```python
# src/trader_memory/schemas.py - TraderMemoryItem 类中新增字段

topic_source: str | None = None              # provider 名称，如 "kaipan"
raw_topic_ids: dict[str, str] | None = None  # {provider: raw_topic_id}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/trader_memory/test_trader_memory_schemas.py::test_trader_memory_item_with_topic_fields -v`
Expected: PASS

- [ ] **Step 5: 添加 TraderMemoryFilter 新增字段的测试**

```python
# tests/unit/trader_memory/test_trader_memory_schemas.py

def test_trader_memory_filter_with_tags_and_version():
    f = TraderMemoryFilter(
        trader_id="trader_a",
        tags=["AI_chip", "半导体"],
        strategy_version_id="v_2026_04_25",
    )
    assert f.tags == ["AI_chip", "半导体"]
    assert f.strategy_version_id == "v_2026_04_25"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/unit/trader_memory/test_trader_memory_schemas.py::test_trader_memory_filter_with_tags_and_version -v`
Expected: FAIL with "tags" not found

- [ ] **Step 7: 更新 TraderMemoryFilter 添加新字段**

```python
# src/trader_memory/schemas.py - TraderMemoryFilter 类中新增字段

tags: list[str] | None = None               # 按标签检索（匹配任一 tag 即可）
strategy_version_id: str | None = None     # 按策略版本检索
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/unit/trader_memory/test_trader_memory_schemas.py::test_trader_memory_filter_with_tags_and_version -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/trader_memory/schemas.py tests/unit/trader_memory/test_trader_memory_schemas.py
git commit -m "feat(NTL-S5-006): extend TraderMemory schema with topic fields and filter"
```

---

## Task 2: 实现 _apply_filter 过滤逻辑

**Files:**
- Modify: `src/trader_memory/service.py:57-85`（`_apply_filter` 方法）

- [ ] **Step 1: 编写 tags 过滤测试**

```python
# tests/unit/trader_memory/test_trader_memory_service.py

def test_filter_by_tags(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="AI chip postmortem",
            content="Entry timing poor",
            tags=["AI_chip", "半导体"],
        )
    )
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 24),
            symbol="SH600519",
            title="新能源 postmortem",
            content="Position sizing issue",
            tags=["新能源车"],
        )
    )

    result = store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", tags=["AI_chip"])
    )
    assert len(result) == 1
    assert result[0].title == "AI chip postmortem"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/trader_memory/test_trader_memory_service.py::test_filter_by_tags -v`
Expected: FAIL

- [ ] **Step 3: 编写 strategy_version_id 过滤测试**

```python
# tests/unit/trader_memory/test_trader_memory_service.py

def test_filter_by_strategy_version(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="v1 postmortem",
            content="Version 1 analysis",
            strategy_version_id="v_2026_04_25",
        )
    )
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 24),
            symbol="SH600519",
            title="v2 postmortem",
            content="Version 2 analysis",
            strategy_version_id="v_2026_04_24",
        )
    )

    result = store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", strategy_version_id="v_2026_04_25")
    )
    assert len(result) == 1
    assert result[0].title == "v1 postmortem"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/unit/trader_memory/test_trader_memory_service.py::test_filter_by_strategy_version -v`
Expected: FAIL

- [ ] **Step 5: 编写组合过滤测试**

```python
# tests/unit/trader_memory/test_trader_memory_service.py

def test_filter_by_tags_and_symbol(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="AI chip SH600519",
            content="Entry timing poor",
            tags=["AI_chip"],
        )
    )
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="000001.SZ",
            title="AI chip 000001",
            content="Breakout analysis",
            tags=["AI_chip"],
        )
    )

    result = store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", tags=["AI_chip"], symbol="SH600519")
    )
    assert len(result) == 1
    assert result[0].symbol == "SH600519"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/unit/trader_memory/test_trader_memory_service.py::test_filter_by_tags_and_symbol -v`
Expected: FAIL

- [ ] **Step 7: 更新 _apply_filter 实现过滤逻辑**

```python
# src/trader_memory/service.py - _apply_filter 方法末尾追加

    if f.tags:
        result = [
            i for i in result
            if i.tags and any(tag in i.tags for tag in f.tags)
        ]

    if f.strategy_version_id:
        result = [
            i for i in result
            if i.strategy_version_id == f.strategy_version_id
        ]

    return result
```

- [ ] **Step 8: Run all new tests to verify they pass**

Run: `pytest tests/unit/trader_memory/test_trader_memory_service.py::test_filter_by_tags tests/unit/trader_memory/test_trader_memory_service.py::test_filter_by_strategy_version tests/unit/trader_memory/test_trader_memory_service.py::test_filter_by_tags_and_symbol -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/trader_memory/service.py tests/unit/trader_memory/test_trader_memory_service.py
git commit -m "feat(NTL-S5-006): implement tags and strategy_version filter in _apply_filter"
```

---

## Task 3: 添加 topic_mapping Alembic migration

**Files:**
- Create: `src/db/migrations/versions/YYYY_MM_DD_XXXX_add_topic_mapping_table.py`

> **确定最新 migration revision：**
> 查看 `src/db/migrations/versions/` 目录下最新的 migration 文件名，取得其 `revision` 值作为 `down_revision`。

- [ ] **Step 1: 查看最新 migration 的 revision**

Run: `ls src/db/migrations/versions/ | sort | tail -1`
Result: 找最新文件名，如 `2026_04_23_0001_add_stage1_models_and_signal_tracking.py`

- [ ] **Step 2: 读取该 migration 的 revision**

```bash
grep "^revision" src/db/migrations/versions/2026_04_23_0001_add_stage1_models_and_signal_tracking.py
```
Result: `revision = "2026_04_23_0001"`

- [ ] **Step 3: 创建新 migration 文件**

文件名：`2026_04_25_0001_add_topic_mapping_table.py`

```python
"""Add topic_mapping table for canonical topic name resolution."""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "2026_04_25_0001"
down_revision = "2026_04_23_0001"  # 替换为实际最新 revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "topic_mapping",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("raw_topic_id", sa.String(100), nullable=False),
        sa.Column("canonical_name", sa.String(200), nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "raw_topic_id", name="uq_topic_mapping_provider_raw_id"),
    )
    op.create_index("ix_topic_mapping_provider", "topic_mapping", ["provider"])
    op.create_index("ix_topic_mapping_canonical", "topic_mapping", ["canonical_name"])


def downgrade() -> None:
    op.drop_index("ix_topic_mapping_canonical", table_name="topic_mapping")
    op.drop_index("ix_topic_mapping_provider", table_name="topic_mapping")
    op.drop_table("topic_mapping")
```

- [ ] **Step 4: 验证 migration 语法**

Run: `python -c "import alembic; print('OK')"`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add src/db/migrations/versions/2026_04_25_0001_add_topic_mapping_table.py
git commit -m "feat(NTL-S5-006): add topic_mapping table for canonical topic resolution"
```

---

## Task 4: 修正 design spec 中关于 trader_memory migration 的错误

**Files:**
- Modify: `docs/superpowers/specs/2026-04-25-NTL-S5-006-trader-memory-search-extension-design.md`

- [ ] **Step 1: 读取当前 spec**

- [ ] **Step 2: 删除"trader_memory 表新增字段"相关的 migration 描述**

删除以下内容：
- `2.2 trader_memory 表新增字段` 整个 section
- 表 schema 变更描述

保留：
- `2.1 topic_mapping 表`（正确）
- `3.1 TraderMemoryItem` Python schema 字段（正确）

- [ ] **Step 3: 更新交付物清单，删除 trader_memory migration 行**

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-25-NTL-S5-006-trader-memory-search-extension-design.md
git commit -m "docs(NTL-S5-006): fix design spec - trader_memory is JSONL, not PostgreSQL"
```

---

## Task 5: 最终验证 + TaskList 更新

- [ ] **Step 1: 运行所有 trader_memory 测试**

Run: `pytest tests/unit/trader_memory/ -v`
Expected: 全部 PASS

- [ ] **Step 2: 检查 schema 字段完整性**

确认 `TraderMemoryItem` 包含：
- topic_source
- raw_topic_ids
- tags（已有）

确认 `TraderMemoryFilter` 包含：
- tags
- strategy_version_id

- [ ] **Step 3: 更新 TaskList.md**

找到 `NTL-S5-006`，更新：
- 状态改为 `[x]`
- 完成情况添加：具体实现内容 + 测试结果

- [ ] **Step 4: Commit TaskList 更新**

```bash
git add docs/TaskList.md
git commit -m "feat(NTL-S5-006): complete trader memory search extension"
```

---

## 验收标准

1. `TraderMemoryItem` 包含 `topic_source`、`raw_topic_ids` 字段
2. `TraderMemoryFilter` 包含 `tags`、`strategy_version_id` 字段
3. `_apply_filter` 正确过滤：tags 任一命中、strategy_version_id 精确匹配
4. `topic_mapping` 表 migration 存在且语法正确
5. 所有新增测试 PASS
6. TaskList NTL-S5-006 标记完成
