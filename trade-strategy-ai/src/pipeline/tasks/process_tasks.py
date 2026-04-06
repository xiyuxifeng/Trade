from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone as TZ, UTC
from pathlib import Path
from typing import Any, Callable, Awaitable

from src.common.config import AppConfig


@dataclass
class ProcessTasksStats:
    processed: int = 0
    skipped_dedup: int = 0
    retried: int = 0
    failed: int = 0
    dead: int = 0
    duration_ms: int = 0


TaskHandler = Callable[[dict[str, Any]], Awaitable[None]]

TASK_HANDLERS: dict[str, TaskHandler] = {}


def register_handler(task_type: str, handler: TaskHandler) -> None:
    TASK_HANDLERS[task_type] = handler


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


def _load_failed_with_metadata(path: Path) -> list[dict[str, Any]]:
    """Load failed tasks with retry metadata.

    Returns list of dicts with 'failed_at' (ISO8601) and 'retry_count' (int) fields.
    Backward compatible: tasks without these fields get default values.
    """
    if not path.exists():
        return []
    tasks = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            task = json.loads(line)
            # Backward compat: add defaults for old-format entries
            if "failed_at" not in task:
                task["failed_at"] = datetime.now(UTC).isoformat()
            if "retry_count" not in task:
                task["retry_count"] = 0
            tasks.append(task)
    return tasks


def _save_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")


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


MAX_RETRIES = 3
MAX_RETRY_COUNT = 3   # 超过此值移入 dead_tasks
FAILED_TTL_DAYS = 7   # 超过此天数的失败记录清理

DEAD_TASKS_PATH = Path("data/processed/pipeline/dead_tasks.jsonl")


async def _process_one(task: dict[str, Any], handlers: dict[str, TaskHandler]) -> tuple[bool, bool]:
    """Process a single task with retry.

    Returns: (success, skipped)
    """
    task_type = task.get("type")
    details = task.get("details", {})

    if task_type == "article_metadata_extracted":
        if await _should_skip_metadata_extracted(details):
            return True, True

    handler = handlers.get(task_type)
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

    print(f"Task {task.get('task_id')} failed after {MAX_RETRIES} retries: {last_error}")
    return False, False


PENDING_PATH = Path("data/processed/pipeline/pending_tasks.jsonl")
FAILED_PATH = Path("data/processed/pipeline/failed_tasks.jsonl")


def _create_handlers(config: AppConfig) -> dict[str, TaskHandler]:
    """Create handler closures that explicitly capture config.

    Each handler is a local async function that closes over the config
    passed in, eliminating the need for module-level global state.
    """

    async def handle_article_ingested(details: dict[str, Any]) -> None:
        from src.agents.data_agent.skills.extract_article_metadata import (
            extract_and_store_metadata,
        )

        await extract_and_store_metadata(
            config=config,
            base_dir=Path("."),
            limit=20,
        )

    async def handle_article_metadata_extracted(details: dict[str, Any]) -> None:
        from src.persona.cluster_builder import build_clusters_from_db

        dest = Path("data/processed/persona/clusters.real.json")
        await build_clusters_from_db(config=config, dest=dest)

    return {
        "article_ingested": handle_article_ingested,
        "article_metadata_extracted": handle_article_metadata_extracted,
    }


async def run_process_tasks(
    *,
    config: AppConfig,
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

    handlers = _create_handlers(config)

    for task in unique_tasks:
        task_id = task.get("task_id")
        if task_id in failed_ids:
            continue

        success, skipped = await _process_one(task, handlers)
        if success:
            if not skipped:
                stats.processed += 1
            # skipped=True means already-processed metadata (not a dedup skip)
        else:
            stats.failed += 1
            failed_tasks.append(task)

    _save_tasks(f_path, failed_tasks)
    _save_tasks(p_path, [])

    stats.duration_ms = int((time.monotonic() - start) * 1000)
    return stats
