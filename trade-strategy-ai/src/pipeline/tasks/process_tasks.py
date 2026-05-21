from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone as TZ, UTC
from pathlib import Path
from typing import Any, Callable, Awaitable

from src.common.config import AppConfig
from src.common.logger import get_logger
from src.common.paths import resolve_project_path

_logger = get_logger(__name__)


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


def _save_failed_with_metadata(path: Path, tasks: list[dict[str, Any]]) -> None:
    """Save failed tasks with retry metadata to JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")


def _cleanup_failed_tasks(
    tasks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate alive tasks from dead tasks based on retry count and TTL.

    Returns: (alive_tasks, dead_tasks)
    - alive: retry_count < MAX_RETRY_COUNT AND failed_at within FAILED_TTL_DAYS
    - dead: retry_count >= MAX_RETRY_COUNT OR failed_at > FAILED_TTL_DAYS ago
    """
    from datetime import timedelta

    now = datetime.now(UTC)
    ttl_cutoff = now - timedelta(days=FAILED_TTL_DAYS)

    alive: list[dict[str, Any]] = []
    dead: list[dict[str, Any]] = []

    for task in tasks:
        retry_count = task.get("retry_count", 0)
        failed_at_str = task.get("failed_at")
        if failed_at_str:
            try:
                failed_at = datetime.fromisoformat(failed_at_str.replace("Z", "+00:00"))
                # Handle naive datetime
                if failed_at.tzinfo is None:
                    failed_at = failed_at.replace(tzinfo=TZ)
            except (ValueError, TypeError):
                failed_at = now
        else:
            failed_at = now

        is_dead = (
            retry_count >= MAX_RETRY_COUNT
            or failed_at < ttl_cutoff
        )
        if is_dead:
            dead.append(task)
        else:
            alive.append(task)

    return alive, dead


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

DEAD_TASKS_PATH = resolve_project_path("data/processed/pipeline/dead_tasks.jsonl")


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


PENDING_PATH = resolve_project_path("data/processed/pipeline/pending_tasks.jsonl")
FAILED_PATH = resolve_project_path("data/processed/pipeline/failed_tasks.jsonl")


def _create_handlers(config: AppConfig, *, force: bool = False, version: str = "v1") -> dict[str, TaskHandler]:
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
            base_dir=resolve_project_path("."),
            force=force,
            version=version,
        )

    async def handle_article_metadata_extracted(details: dict[str, Any]) -> None:
        from src.persona.cluster_builder import build_clusters_from_db

        dest = resolve_project_path("data/processed/persona/clusters.real.json")
        await build_clusters_from_db(config=config, dest=dest)

    # 候选池快照 handlers（NTL-S2-020 ~ NTL-S2-022）
    from src.pipeline.tasks.snapshot_tasks import (
        handle_hot_topics_snapshot,
        handle_topic_constituents_snapshot,
        handle_strong_symbols_snapshot,
    )

    async def handle_hot_topics_snapshot_wrapped(details: dict[str, Any]) -> None:
        await handle_hot_topics_snapshot(details, config=config)

    async def handle_topic_constituents_snapshot_wrapped(details: dict[str, Any]) -> None:
        await handle_topic_constituents_snapshot(details, config=config)

    async def handle_strong_symbols_snapshot_wrapped(details: dict[str, Any]) -> None:
        await handle_strong_symbols_snapshot(details, config=config)

    # 策略版本构建 handler（NTL-S3-008）
    from src.pipeline.tasks.strategy_version_tasks import (
        handle_build_trader_strategy_version,
    )

    async def handle_build_trader_strategy_version_wrapped(details: dict[str, Any]) -> None:
        await handle_build_trader_strategy_version(details, config=config)

    # postmortem_analysis handler（NTL-S5-008）
    from src.pipeline.tasks.postmortem_tasks import handle_postmortem_analysis

    async def handle_postmortem_analysis_wrapped(details: dict[str, Any]) -> None:
        await handle_postmortem_analysis(details, config=config)

    # ohlcv_crawl handler（S7-000）
    from src.pipeline.tasks.ohlcv_crawl_task import handle_ohlcv_crawl

    async def handle_ohlcv_crawl_wrapped(details: dict[str, Any]) -> None:
        await handle_ohlcv_crawl(details, config=config)

    return {
        "article_ingested": handle_article_ingested,
        "article_metadata_extracted": handle_article_metadata_extracted,
        "hot_topics_snapshot": handle_hot_topics_snapshot_wrapped,
        "topic_constituents_snapshot": handle_topic_constituents_snapshot_wrapped,
        "strong_symbols_snapshot": handle_strong_symbols_snapshot_wrapped,
        "build_trader_strategy_version": handle_build_trader_strategy_version_wrapped,
        "postmortem_analysis": handle_postmortem_analysis_wrapped,
        "ohlcv_crawl": handle_ohlcv_crawl_wrapped,
    }


async def _rebuild_pending_tasks(pending_path: Path, version: str) -> None:
    """从数据库重建 pending_tasks.jsonl。"""
    from src.schemas.contracts import AgentTask
    from src.common.utils import append_jsonl
    from src.db.session import session_scope
    from src.models.blog_article import BlogArticle
    from src.models.article_metadata import ArticleMetadata
    from sqlalchemy import select, or_

    pending_path.parent.mkdir(parents=True, exist_ok=True)

    async with session_scope() as session:
        if version == "v1":
            # v1: 找没有 metadata 记录的文章
            rows = await session.execute(
                select(BlogArticle.id, BlogArticle.source, BlogArticle.author_id,
                       BlogArticle.author_name, BlogArticle.source_url,
                       BlogArticle.content_hash, BlogArticle.raw_payload)
                .outerjoin(ArticleMetadata, ArticleMetadata.article_id == BlogArticle.id)
                .where(or_(
                    ArticleMetadata.id.is_(None),
                    ArticleMetadata.processed_at.is_(None)
                ))
            )
        else:
            # v2+: 找没有该版本 metadata 记录的文章
            subq = select(ArticleMetadata.article_id).where(
                ArticleMetadata.version == version
            )
            rows = await session.execute(
                select(BlogArticle.id, BlogArticle.source, BlogArticle.author_id,
                       BlogArticle.author_name, BlogArticle.source_url,
                       BlogArticle.content_hash, BlogArticle.raw_payload)
                .where(BlogArticle.id.not_in(subq))
            )

        for row in rows.all():
            article_id, source, author_id, author_name, source_url, content_hash, raw_payload = row
            trader_id = None
            if isinstance(raw_payload, dict):
                trader_id = raw_payload.get("trader_id")
            task = AgentTask(
                type="article_ingested",
                title="New/updated article ingested",
                trader_id=trader_id if isinstance(trader_id, str) else None,
                details={
                    "article_id": str(article_id),
                    "source": source,
                    "site": raw_payload.get("site") if isinstance(raw_payload, dict) else None,
                    "author_id": author_id,
                    "author_name": author_name,
                    "source_url": source_url,
                    "content_hash": content_hash,
                    "inserted": False,
                    "updated": False,
                },
            )
            append_jsonl(pending_path, task.model_dump())


async def run_process_tasks(
    *,
    config: AppConfig,
    pending_path: Path | None = None,
    failed_path: Path | None = None,
    dead_path: Path | None = None,
    force: bool = False,
    retry_failed: bool = False,
    version: str = "v1",
) -> ProcessTasksStats:
    start = time.monotonic()
    stats = ProcessTasksStats()

    p_path = pending_path or PENDING_PATH
    f_path = failed_path or FAILED_PATH
    d_path = dead_path or DEAD_TASKS_PATH

    # force 模式：pending_tasks.jsonl 不存在时从数据库重建
    if force and not p_path.exists():
        await _rebuild_pending_tasks(p_path, version)
        print(f"[process] force 模式：已从数据库重建 pending_tasks.jsonl（{p_path}）")

    all_tasks = _load_tasks(p_path)

    # Load failed tasks with metadata
    failed_tasks = _load_failed_with_metadata(f_path)

    # TTL cleanup: separate alive from dead
    alive_failed, dead_failed = _cleanup_failed_tasks(failed_tasks)
    stats.dead = len(dead_failed)

    if retry_failed and alive_failed:
        stats.retried = len(alive_failed)
        all_tasks.extend(alive_failed)
        alive_failed = []

    if not all_tasks:
        if dead_failed:
            _save_failed_with_metadata(d_path, dead_failed)
        _save_failed_with_metadata(f_path, alive_failed)
        stats.duration_ms = int((time.monotonic() - start) * 1000)
        return stats

    unique_tasks = _dedup_by_article_id(all_tasks)
    stats.skipped_dedup = len(all_tasks) - len(unique_tasks)

    # Save cleaned failed tasks
    _save_failed_with_metadata(f_path, alive_failed)

    # Append dead tasks to dead_tasks file
    if dead_failed:
        _save_failed_with_metadata(d_path, dead_failed)

    failed_ids = {t.get("task_id") for t in alive_failed}

    handlers = _create_handlers(config, force=force, version=version)

    for task in unique_tasks:
        task_id = task.get("task_id")
        if task_id in failed_ids:
            continue

        success, skipped = await _process_one(task, handlers)
        if success:
            if not skipped:
                stats.processed += 1
        else:
            stats.failed += 1
            # Update retry metadata for this task
            matching = [t for t in alive_failed if t.get("task_id") == task_id]
            if matching:
                existing = matching[0]
                existing["retry_count"] = existing.get("retry_count", 0) + 1
                if existing["retry_count"] >= MAX_RETRY_COUNT:
                    # Move to dead
                    dead_failed.append(existing)
                    alive_failed.remove(existing)
                    stats.dead += 1
                # else: stays in alive_failed for retry
            else:
                # New failure - add with metadata
                new_failed = dict(task)
                new_failed["failed_at"] = datetime.now(UTC).isoformat()
                new_failed["retry_count"] = 1
                alive_failed.append(new_failed)

    # Save updated failed tasks
    _save_failed_with_metadata(f_path, alive_failed)
    # Save dead tasks discovered during processing
    if dead_failed:
        _save_failed_with_metadata(d_path, dead_failed)
    _save_tasks(p_path, [])

    stats.duration_ms = int((time.monotonic() - start) * 1000)

    # 记录 Pipeline 健康快照（process_tasks 作为独立入口时的健康状态）
    try:
        from src.pipeline.health import PipelineHealthSnapshot, PipelineNodeResult
        from src.health.pipeline_checker import record_pipeline_snapshot

        snap = PipelineHealthSnapshot(graph_name="process_tasks")
        result = PipelineNodeResult(
            name="run_process_tasks",
            status="success" if stats.failed == 0 else "failed",
            duration_seconds=stats.duration_ms / 1000.0,
            error=f"{stats.failed} failed" if stats.failed > 0 else None,
        )
        snap.add_result(result)
        record_pipeline_snapshot(snap.finalize())
        _logger.debug(
            "process_tasks健康快照已记录: processed=%d failed=%d skipped_dedup=%d dead=%d duration=%dms",
            stats.processed,
            stats.failed,
            stats.skipped_dedup,
            stats.dead,
            stats.duration_ms,
        )
    except Exception:
        _logger.warning("process_tasks健康快照记录失败", exc_info=True)

    return stats
