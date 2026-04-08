# Data Audit Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为关键写入路径增加批次级数据审计日志，能回答“谁在什么时候通过哪条流程改了什么数据版本”。

**Architecture:** 新增一张轻量审计表 `data_audit_events`，把关键写入动作统一归一成事件记录，而不是在每个业务表里塞复杂变更历史。审计只覆盖会改数据的核心入口：文章入库、初始化导入、备份、恢复和相关 CLI；读取路径不做审计。数据版本用 `dataset_version` 标识一次批次写入或恢复来源，和事件 payload 一起存储，便于后续回查。

**Tech Stack:** Python 3.11+, SQLAlchemy async, Alembic, PostgreSQL, SQLite（测试用）, Typer CLI, pytest/pytest-asyncio, JSONL/JSON payloads

---

## Tasks

### Task 1: Add audit event model and migration

**Files:**
- Create: `trade-strategy-ai/src/models/data_audit_event.py`
- Modify: `trade-strategy-ai/src/models/__init__.py`
- Create: `trade-strategy-ai/src/db/migrations/versions/20260406_0004_add_data_audit_events.py`
- Modify: `trade-strategy-ai/tests/unit/models/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
from src.models.data_audit_event import DataAuditEvent

def test_data_audit_event_table_metadata() -> None:
    index_names = {index.name for index in DataAuditEvent.__table__.indexes}
    assert "ix_data_audit_events_created_at" in index_names
    assert "ix_data_audit_events_event_type_created_at" in index_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q trade-strategy-ai/tests/unit/models/test_models.py -k data_audit_event -v`
Expected: FAIL with import error / missing model

- [ ] **Step 3: Write minimal implementation**

```python
class DataAuditEvent(TimestampMixin, Base):
    __tablename__ = "data_audit_events"
    __table_args__ = (
        Index("ix_data_audit_events_created_at", "created_at"),
        Index("ix_data_audit_events_event_type_created_at", "event_type", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(128))
    dataset_version: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q trade-strategy-ai/tests/unit/models/test_models.py -k data_audit_event -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/models/data_audit_event.py trade-strategy-ai/src/models/__init__.py trade-strategy-ai/src/db/migrations/versions/20260406_0004_add_data_audit_events.py trade-strategy-ai/tests/unit/models/test_models.py
git commit -m "feat: add audit event model"
```

### Task 2: Add audit service and wire key write paths

**Files:**
- Create: `trade-strategy-ai/src/audit/service.py`
- Create: `trade-strategy-ai/src/audit/__init__.py`
- Modify: `trade-strategy-ai/src/agents/data_agent/skills/store_db.py`
- Modify: `trade-strategy-ai/scripts/seed_data.py`
- Modify: `trade-strategy-ai/src/backup/service.py`
- Modify: `trade-strategy-ai/cli/main.py`
- Test: `trade-strategy-ai/tests/unit/audit/test_service.py`
- Test: `trade-strategy-ai/tests/unit/cli/test_audit_cli.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

import pytest

from src.audit.service import AuditService

@pytest.mark.asyncio
async def test_audit_event_written_for_seed_and_backup(tmp_path: Path) -> None:
    service = AuditService(base_dir=tmp_path)
    event = await service.record(
        event_type="seed_project_data",
        actor="cli.seed_data",
        entity_type="database",
        entity_id=None,
        dataset_version="seed-2026-04-06-001",
        payload={"article_jsonl_paths": ["data/processed/crawl/tgb/10461311/articles.jsonl"]},
        source="seed-data",
    )
    assert event.event_type == "seed_project_data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q trade-strategy-ai/tests/unit/audit/test_service.py -v`
Expected: FAIL because `AuditService` is missing

- [ ] **Step 3: Write minimal implementation**

```python
class AuditService:
    async def record(
        self,
        *,
        event_type: str,
        actor: str,
        entity_type: str,
        entity_id: str | None,
        dataset_version: str | None,
        payload: dict[str, Any],
        source: str,
    ) -> DataAuditEvent:
        event = DataAuditEvent(
            event_type=event_type,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            dataset_version=dataset_version,
            payload=payload,
            source=source,
        )
        async with session_scope() as session:
            session.add(event)
            await session.flush()
        return event
```

Hook points:
- `store_articles_jsonl_to_db()` records `article_ingested_batch`
- `seed_project_data()` records `seed_project_data`
- `backup_project_state()` records `backup_project_state`
- `restore_project_state()` records `restore_project_state`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q trade-strategy-ai/tests/unit/audit/test_service.py trade-strategy-ai/tests/unit/cli/test_audit_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/audit trade-strategy-ai/src/agents/data_agent/skills/store_db.py trade-strategy-ai/scripts/seed_data.py trade-strategy-ai/src/backup/service.py trade-strategy-ai/cli/main.py trade-strategy-ai/tests/unit/audit/test_service.py trade-strategy-ai/tests/unit/cli/test_audit_cli.py
git commit -m "feat: add data audit logging"
```

### Task 3: Verify migrations and end-to-end regression

**Files:**
- Modify: `trade-strategy-ai/tests/unit/models/test_models.py`
- Modify: `trade-strategy-ai/tests/e2e/test_full_flow.py` if the new migration or audit hook changes setup expectations

- [ ] **Step 1: Write the failing test**

```python
from src.models.data_audit_event import DataAuditEvent

def test_audit_event_index_names_present() -> None:
    index_names = {index.name for index in DataAuditEvent.__table__.indexes}
    assert "ix_data_audit_events_created_at" in index_names
    assert "ix_data_audit_events_event_type_created_at" in index_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q trade-strategy-ai/tests/unit/models/test_models.py trade-strategy-ai/tests/unit/audit/test_service.py -v`
Expected: PASS after tasks 1-2; if not, fix before moving on

- [ ] **Step 3: Write minimal implementation**

```python
# No new logic if tasks 1-2 already cover everything; this step is a verification gate.
```

- [ ] **Step 4: Run verification**

Run:
- `make smoke`
- `python -m pytest -q`
- `python -m cli.main e2e-regression --config config/app.yaml --max-articles 1 --extract-limit 1`

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/tests/e2e/test_full_flow.py docs/TaskList.md daily-sessions/2026-04-06.md daily-report/2026-04-06.md
git commit -m "chore: finalize data audit logging"
```

---

## Verification

- `python -m pytest -q trade-strategy-ai/tests/unit/models/test_models.py`
- `python -m pytest -q trade-strategy-ai/tests/unit/audit/test_service.py`
- `make smoke`
- `python -m pytest -q`
- `python -m cli.main e2e-regression --config config/app.yaml --max-articles 1 --extract-limit 1`

## Phase Gate

- Task 1 完成后，审计事件表和版本标识具备持久化基础。
- Task 2 完成后，关键写入路径已有统一审计落点。
- Task 3 完成后，审计和现有回归门禁一起被验证，`P1-021` 可关闭。
