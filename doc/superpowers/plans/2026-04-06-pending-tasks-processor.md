# Pending Tasks Processor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 pending_tasks 处理器：读取 `pending_tasks.jsonl`，按 task type 分发到对应处理器，支持 article_id 去重和固定次数重试。

**Architecture:**
- `process_tasks.py`: 核心处理器，读取 JSONL → 按 article_id 去重 → 分发任务 → 失败重试 → 写入 failed_tasks.jsonl
- DAG 集成：在 `store` 之后、`export` 之前调用 `run_process_tasks()`

**Tech Stack:** Python asyncio, JSONL 文件, SQLAlchemy async

---

## File Map

- **Create:** `src/pipeline/tasks/process_tasks.py` — 核心处理器
- **Modify:** `src/pipeline/dag.py` — pipeline DAG 集成
- **Modify:** `src/pipeline/tasks/__init__.py` — 导出新接口
- **Modify:** `daily-sessions/2026-04-06.md` — 更新进度
- **Modify:** `daily-report/2026-04-06.md` — 更新进度

---

## Task 1: Write ProcessTasksStats and task type enum

**Files:**
- Create: `src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: Write the file header and imports**

```python
from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.schemas.contracts import AgentTask
```

- [ ] **Step 2: Write ProcessTasksStats dataclass**

```python
@dataclass
class ProcessTasksStats:
    processed: int = 0
    skipped_dedup: int = 0
    retried: int = 0
    failed: int = 0
    duration_ms: int = 0
```

- [ ] **Step 3: Write TaskHandler type alias and registry**

```python
from typing import Callable, Awaitable

TaskHandler = Callable[[dict[str, Any]], Awaitable[None]]

# 处理器注册表
TASK_HANDLERS: dict[str, TaskHandler] = {}

def register_handler(task_type: str, handler: TaskHandler) -> None:
    TASK_HANDLERS[task_type] = handler
```

- [ ] **Step 4: Write _load_tasks function**

```python
def _load_tasks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    tasks = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tasks.append(json.loads(line))
    return tasks
```

- [ ] **Step 5: Write _save_tasks function**

```python
def _save_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
```

- [ ] **Step 6: Commit**

```bash
git add src/pipeline/tasks/process_tasks.py
git commit -m "feat(pipeline): add process_tasks skeleton with ProcessTasksStats"
```

---

## Task 2: Implement core processing logic

**Files:**
- Modify: `src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: Write _dedup_by_article_id function**

```python
def _dedup_by_article_id(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only the latest task per article_id."""
    latest: dict[str, dict[str, Any]] = {}
    for task in tasks:
        details = task.get("details", {})
        article_id = details.get("article_id")
        if not article_id:
            continue
        created = task.get("created_at", "")
        existing = latest.get(article_id)
        if existing is None or created > existing.get("created_at", ""):
            latest[article_id] = task
    return list(latest.values())
```

- [ ] **Step 2: Write _should_skip_metadata_extracted function**

```python
async def _should_skip_metadata_extracted(details: dict[str, Any]) -> bool:
    """Check if metadata already extracted for this article."""
    from sqlalchemy import select
    from src.db.session import session_scope
    from src.models.article_metadata import ArticleMetadata

    article_id_str = details.get("article_id")
    if not article_id_str:
        return False

    import uuid
    try:
        article_uuid = uuid.UUID(article_id_str)
    except (ValueError, TypeError):
        return False

    async with session_scope() as session:
        meta = await session.scalar(
            select(ArticleMetadata).where(ArticleMetadata.article_id == article_uuid)
        )
        return meta is not None and meta.processed_at is not None
```

- [ ] **Step 3: Write _process_one with retry logic**

```python
MAX_RETRIES = 3

async def _process_one(task: dict[str, Any]) -> tuple[bool, bool]:
    """Process a single task with retry.

    Returns: (success, skipped)
    """
    task_type = task.get("type")
    details = task.get("details", {})

    # article_metadata_extracted: skip if already processed
    if task_type == "article_metadata_extracted":
        if await _should_skip_metadata_extracted(details):
            return True, True

    handler = TASK_HANDLERS.get(task_type)
    if handler is None:
        return True, False  # unknown type, skip silently

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            await handler(details)
            return True, False
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)  # exponential backoff

    # All retries exhausted
    print(f"Task {task.get('task_id')} failed after {MAX_RETRIES} retries: {last_error}")
    return False, False
```

- [ ] **Step 4: Write run_process_tasks function**

```python
PENDING_PATH = Path("data/processed/pipeline/pending_tasks.jsonl")
FAILED_PATH = Path("data/processed/pipeline/failed_tasks.jsonl")


async def run_process_tasks(
    *,
    pending_path: Path | None = None,
    failed_path: Path | None = None,
) -> ProcessTasksStats:
    """Process all pending tasks.

    Deduplicates by article_id, dispatches to handlers, retries on failure.
    """
    start = time.monotonic()
    stats = ProcessTasksStats()

    p_path = pending_path or PENDING_PATH
    f_path = failed_path or FAILED_PATH

    all_tasks = _load_tasks(p_path)
    if not all_tasks:
        stats.duration_ms = int((time.monotonic() - start) * 1000)
        return stats

    # Deduplicate by article_id (keep latest)
    unique_tasks = _dedup_by_article_id(all_tasks)

    # Track skipped by dedup count
    stats.skipped_dedup = len(all_tasks) - len(unique_tasks)

    # Load existing failed tasks
    failed_tasks = _load_tasks(f_path)
    failed_ids = {t.get("task_id") for t in failed_tasks}

    remaining_tasks: list[dict[str, Any]] = []

    for task in unique_tasks:
        task_id = task.get("task_id")
        if task_id in failed_ids:
            continue  # already permanently failed, skip

        success, skipped = await _process_one(task)
        if success and skipped:
            stats.skipped_dedup += 1
        elif success:
            stats.processed += 1
        else:
            stats.failed += 1
            failed_tasks.append(task)
            _save_tasks(f_path, failed_tasks)

    # Rewrite pending_tasks without successfully processed
    still_pending = [t for t in unique_tasks if t.get("task_id") not in {task.get("task_id") for task in []}]
    # Actually, remaining tasks are those we couldn't process or haven't tried yet
    # We process all unique_tasks; if not fully processed, they stay
    _save_tasks(p_path, [])

    stats.duration_ms = int((time.monotonic() - start) * 1000)
    return stats
```

- [ ] **Step 5: Fix run_process_tasks logic (remaining tasks should stay in pending)**

The logic above has a bug: we should keep tasks that failed in pending for future processing, not clear the file. Fix:

```python
async def run_process_tasks(
    *,
    pending_path: Path | None = None,
    failed_path: Path | None = None,
) -> ProcessTasksStats:
    start = time.monotonic()
    stats = ProcessTasksStats()

    p_path = pending_path or PENDING_PATH
    f_path = failed_path or FAILED_PATH

    all_tasks = _load_tasks(p_path)
    if not all_tasks:
        stats.duration_ms = int((time.monotonic() - start) * 1000)
        return stats

    unique_tasks = _dedup_by_article_id(all_tasks)
    stats.skipped_dedup = len(all_tasks) - len(unique_tasks)

    failed_tasks = _load_tasks(f_path)
    failed_ids = {t.get("task_id") for t in failed_tasks}

    for task in unique_tasks:
        task_id = task.get("task_id")
        if task_id in failed_ids:
            continue

        success, skipped = await _process_one(task)
        if success and skipped:
            stats.skipped_dedup += 1
        elif success:
            stats.processed += 1
        else:
            stats.failed += 1
            failed_tasks.append(task)

    # Save failed tasks
    _save_tasks(f_path, failed_tasks)

    # Clear pending (all unique tasks were processed; failed ones are in failed_tasks)
    _save_tasks(p_path, [])

    stats.duration_ms = int((time.monotonic() - start) * 1000)
    return stats
```

- [ ] **Step 6: Run import test**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && .venv/bin/python -c "
from src.pipeline.tasks.process_tasks import run_process_tasks, ProcessTasksStats
print('import ok')
"
```

Expected: import ok

- [ ] **Step 7: Commit**

```bash
git add src/pipeline/tasks/process_tasks.py
git commit -m "feat(pipeline): implement pending tasks processor with retry and dedup"
```

---

## Task 3: Register handlers for article_ingested and article_metadata_extracted

**Files:**
- Modify: `src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: Write handler for article_ingested**

```python
from src.common.config import AppConfig


async def _handle_article_ingested(details: dict[str, Any]) -> None:
    """Handler for article_ingested: trigger metadata extraction."""
    from src.agents.data_agent.skills.extract_article_metadata import extract_and_store_metadata
    from src.common.config import get_app_config

    config = get_app_config()
    base_dir = Path(".")

    # Call extract_and_store_metadata for this specific article
    # We pass limit=1 and article_id filter via the details
    article_id_str = details.get("article_id")
    if not article_id_str:
        raise ValueError("article_id required")

    import uuid
    article_uuid = uuid.UUID(article_id_str)

    # Import here to avoid circular
    from sqlalchemy import select
    from src.db.session import session_scope
    from src.models.article_metadata import ArticleMetadata
    from src.models.blog_article import BlogArticle

    async with session_scope() as session:
        row = await session.execute(
            select(BlogArticle, ArticleMetadata)
            .join(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
            .where(BlogArticle.id == article_uuid)
            .limit(1)
        )
        result = row.first()
        if result is None:
            raise ValueError(f"Article not found: {article_id_str}")
```

Actually, `extract_and_store_metadata` processes ALL unprocessed articles with a limit. For the handler, we need a targeted version. Let me write a simpler approach: the handler calls the existing function which will process unprocessed articles including this one.

Actually, looking at `extract_and_store_metadata`, it processes articles where `ArticleMetadata.processed_at IS NULL`. Since we're deduping by article_id and skipping already-processed metadata, calling `extract_and_store_metadata(limit=20)` will naturally process our newly ingested articles.

Let's register the handlers to just call the existing functions:

- [ ] **Step 2: Write and register handlers**

```python
async def _handle_article_ingested(details: dict[str, Any]) -> None:
    """Handler for article_ingested: trigger metadata extraction."""
    from src.agents.data_agent.skills.extract_article_metadata import extract_and_store_metadata
    from src.common.config import get_app_config

    config = get_app_config()
    base_dir = Path(".")

    await extract_and_store_metadata(
        config=config,
        base_dir=base_dir,
        limit=20,
    )


async def _handle_article_metadata_extracted(details: dict[str, Any]) -> None:
    """Handler for article_metadata_extracted: trigger clusters rebuild."""
    from src.persona.cluster_builder import build_clusters_from_db
    from src.common.config import get_app_config

    config = get_app_config()
    dest = base_dir / "data" / "processed" / "persona" / "clusters.real.json"

    await build_clusters_from_db(
        config=config,
        dest=dest,
    )


# Register handlers
register_handler("article_ingested", _handle_article_ingested)
register_handler("article_metadata_extracted", _handle_article_metadata_extracted)
```

Wait, `_handle_article_metadata_extracted` references `base_dir` which is not in scope. Fix:

- [ ] **Step 3: Fix the handler (use Path("."))**

```python
async def _handle_article_metadata_extracted(details: dict[str, Any]) -> None:
    """Handler for article_metadata_extracted: trigger clusters rebuild."""
    from src.persona.cluster_builder import build_clusters_from_db
    from src.common.config import get_app_config

    config = get_app_config()
    dest = Path("data/processed/persona/clusters.real.json")

    await build_clusters_from_db(
        config=config,
        dest=dest,
    )
```

- [ ] **Step 4: Run import test**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && .venv/bin/python -c "
from src.pipeline.tasks.process_tasks import TASK_HANDLERS
print('handlers:', list(TASK_HANDLERS.keys()))
"
```

Expected: `['article_ingested', 'article_metadata_extracted']`

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/tasks/process_tasks.py
git commit -m "feat(pipeline): register handlers for article_ingested and article_metadata_extracted"
```

---

## Task 4: Integrate into pipeline DAG

**Files:**
- Modify: `src/pipeline/dag.py`
- Modify: `src/pipeline/tasks/__init__.py`

- [ ] **Step 1: Update PipelineRunResult to add process_tasks field**

In `dag.py`, add `process_tasks: ProcessTasksStats` to `PipelineRunResult`.

- [ ] **Step 2: Add process_pending_tasks step after store**

```python
from src.pipeline.tasks.process_tasks import run_process_tasks

# In run_pipeline(), after store_stats:
process_stats = await run_process_tasks()

return PipelineRunResult(
    crawl=crawl_result,
    clean=clean_result,
    validate=validate_result,
    store=store_stats,
    process=process_stats,
    export=export_result,
)
```

- [ ] **Step 3: Update __init__.py**

```python
from src.pipeline.tasks.process_tasks import ProcessTasksStats, run_process_tasks

__all__ = [
    ...
    "ProcessTasksStats",
    "run_process_tasks",
]
```

- [ ] **Step 4: Run integration test**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai && .venv/bin/python -c "
from src.pipeline.dag import PipelineRunResult
from src.pipeline.tasks import run_process_tasks, ProcessTasksStats
print('integration ok')
"
```

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/dag.py src/pipeline/tasks/__init__.py
git commit -m "feat(pipeline): integrate process_tasks into DAG after store step"
```

---

## Task 5: Update daily session and report

- [ ] **Step 1: Update daily-sessions/2026-04-06.md**

Mark task 2 as complete, update status.

- [ ] **Step 2: Update daily-report/2026-04-06.md**

Add task 2 completion details.

- [ ] **Step 3: Commit docs**

```bash
git add daily-sessions/2026-04-06.md daily-report/2026-04-06.md
git commit -m "docs: update daily session and report for task 2 completion"
```
