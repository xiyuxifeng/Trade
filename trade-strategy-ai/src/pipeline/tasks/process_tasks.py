from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone as TZ, UTC
from pathlib import Path
from typing import Any, Callable, Awaitable

from src.common.config import AppConfig
from src.common.logger import get_logger
from src.common.paths import resolve_project_path
from src.llm.client import from_env_and_config
from src.llm.runtime import LLMClientGateway
from src.services.job_control import JobControlInterrupted
from src.services.stage3_prompt_runtime_service import Stage3PromptRuntimeService
from src.services.stage3_single_article_service import Stage3SingleArticleError, Stage3SingleArticleService

_logger = get_logger(__name__)


@dataclass
class ProcessTasksStats:
    processed: int = 0
    skipped_dedup: int = 0
    retried: int = 0
    failed: int = 0
    dead: int = 0
    duration_ms: int = 0
    failure_details: list[dict[str, Any]] = field(default_factory=list)
    fatal_error: str | None = None
    fatal_error_type: str | None = None
    fatal_task_id: str | None = None
    fatal_task_type: str | None = None


TaskHandler = Callable[[dict[str, Any]], Awaitable[None]]

TASK_HANDLERS: dict[str, TaskHandler] = {}


class ProcessFatalError(RuntimeError):
    """表示当前 process job 应立即中止的不可恢复错误。"""

    def __init__(self, message: str, *, task: dict[str, Any] | None = None, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.task = task or {}
        self.details = details or {}


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


def _configured_llm_model(config: AppConfig) -> str:
    model = getattr(getattr(config, "llm", None), "model", None)
    if isinstance(model, list):
        for item in model:
            if isinstance(item, str) and item.strip():
                return item.strip()
    if isinstance(model, str) and model.strip():
        return model.strip()
    return "gpt-5.4"


def _optional_config_str(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _configured_llm_gateway(config: AppConfig, *, model: str) -> LLMClientGateway:
    llm_config = getattr(config, "llm", None)
    return LLMClientGateway.from_config(
        from_env_and_config(
            provider=_optional_config_str(getattr(llm_config, "provider", None)),
            model=model,
            url=_optional_config_str(getattr(llm_config, "url", None)),
            api_key=_optional_config_str(getattr(llm_config, "api_key", None)),
        )
    )


async def _should_skip_article_analysis(details: dict[str, Any]) -> bool:
    """Check if the latest article revision already has Stage3 analysis output."""
    from sqlalchemy import select
    from src.db.session import session_scope
    from src.models.stage2_canonical import ArticleRevision, ArticleStructure

    article_id_str = details.get("article_id")
    if not article_id_str:
        return False

    import uuid
    try:
        article_uuid = uuid.UUID(article_id_str)
    except (ValueError, TypeError):
        return False

    async with session_scope() as session:
        revision = await session.scalar(
            select(ArticleRevision)
            .where(ArticleRevision.article_id == article_uuid)
            .order_by(ArticleRevision.revision_no.desc(), ArticleRevision.captured_at.desc())
            .limit(1)
        )
        if revision is None:
            return False
        structure = await session.scalar(
            select(ArticleStructure.article_structure_id)
            .where(ArticleStructure.article_id == article_uuid)
            .where(ArticleStructure.article_revision_id == revision.article_revision_id)
            .limit(1)
        )
        return structure is not None


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

    if task_type == "article_ingested":
        if await _should_skip_article_analysis(details):
            return True, True

    handler = handlers.get(task_type)
    if handler is None:
        return True, False  # unknown type, skip silently

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            await handler(details)
            return True, False
        except ProcessFatalError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)  # exponential backoff

    print(f"Task {task.get('task_id')} failed after {MAX_RETRIES} retries: {last_error}")
    return False, False


PENDING_PATH = resolve_project_path("data/processed/pipeline/pending_tasks.jsonl")
FAILED_PATH = resolve_project_path("data/processed/pipeline/failed_tasks.jsonl")


def _create_handlers(
    config: AppConfig,
    *,
    force: bool = False,
    version: str = "v1",
    cancel_check: Callable[[], Awaitable[bool]] | None = None,
) -> dict[str, TaskHandler]:
    """Create handler closures that explicitly capture config.

    Each handler is a local async function that closes over the config
    passed in, eliminating the need for module-level global state.
    """

    async def handle_article_ingested(details: dict[str, Any]) -> None:
        from src.db.session import session_scope
        from src.models.stage2_canonical import ArticleRevision, ArticleStructure
        from sqlalchemy import select
        from uuid import UUID

        article_id_str = details.get("article_id")
        if not isinstance(article_id_str, str) or not article_id_str:
            raise ValueError("article_ingested task missing article_id")
        article_id = UUID(article_id_str)
        if cancel_check is not None and await cancel_check():
            raise JobControlInterrupted("cancel")

        model = _configured_llm_model(config)
        service = Stage3SingleArticleService(
            session_scope_factory=session_scope,
            prompt_runtime_service=Stage3PromptRuntimeService(
                session_scope_factory=session_scope,
                gateway=_configured_llm_gateway(config, model=model),
                model=model,
            ),
        )
        try:
            journey = await service.run_analysis(article_id=article_id, article_revision_id=None)
        except Stage3SingleArticleError as exc:
            raise ProcessFatalError(
                str(exc),
                task={"type": "article_ingested", "details": details},
                details={
                    "error_type": "stage3_article_analysis",
                    "article_id": article_id_str,
                },
            ) from exc
        if cancel_check is not None and await cancel_check():
            raise JobControlInterrupted("cancel")

        revision_id = getattr(getattr(journey, "revision", None), "article_revision_id", None)
        async with session_scope() as session:
            if revision_id is None:
                revision_id = await session.scalar(
                    select(ArticleRevision.article_revision_id)
                    .where(ArticleRevision.article_id == article_id)
                    .order_by(ArticleRevision.revision_no.desc(), ArticleRevision.captured_at.desc())
                    .limit(1)
                )
            persisted_structure = None
            if revision_id is not None:
                persisted_structure = await session.scalar(
                    select(ArticleStructure.article_structure_id).where(
                        ArticleStructure.article_id == article_id,
                        ArticleStructure.article_revision_id == revision_id,
                    )
                )
        if persisted_structure is None:
            raise ProcessFatalError(
                "article analysis was not persisted after Stage3 extraction",
                task={"type": "article_ingested", "details": details},
                details={
                    "article_id": article_id_str,
                    "article_revision_id": str(revision_id) if revision_id is not None else None,
                    "journey_status": getattr(journey, "status", None),
                },
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
    from src.models.stage2_canonical import ArticleRevision, ArticleStructure
    from sqlalchemy import and_, func, select

    pending_path.parent.mkdir(parents=True, exist_ok=True)

    async with session_scope() as session:
        latest_revision = (
            select(
                ArticleRevision.article_id.label("article_id"),
                ArticleRevision.article_revision_id.label("article_revision_id"),
                func.row_number()
                .over(
                    partition_by=ArticleRevision.article_id,
                    order_by=(ArticleRevision.revision_no.desc(), ArticleRevision.captured_at.desc()),
                )
                .label("revision_rank"),
            )
            .subquery()
        )
        rows = await session.execute(
            select(
                BlogArticle.id,
                BlogArticle.source,
                BlogArticle.author_id,
                BlogArticle.author_name,
                BlogArticle.source_url,
                BlogArticle.content_hash,
                BlogArticle.raw_payload,
            )
            .join(latest_revision, latest_revision.c.article_id == BlogArticle.id)
            .outerjoin(
                ArticleStructure,
                and_(
                    ArticleStructure.article_id == BlogArticle.id,
                    ArticleStructure.article_revision_id == latest_revision.c.article_revision_id,
                ),
            )
            .where(latest_revision.c.revision_rank == 1)
            .where(ArticleStructure.article_structure_id.is_(None))
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
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    overall_current: int | None = None,
    overall_total: int | None = None,
    cancel_check: Callable[[], Awaitable[bool]] | None = None,
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
    total = len(unique_tasks)

    # Save cleaned failed tasks
    _save_failed_with_metadata(f_path, alive_failed)

    # Append dead tasks to dead_tasks file
    if dead_failed:
        _save_failed_with_metadata(d_path, dead_failed)

    failed_ids = {t.get("task_id") for t in alive_failed}

    handlers = _create_handlers(config, force=force, version=version, cancel_check=cancel_check)
    remaining_tasks: list[dict[str, Any]] = []

    def _track_failure(
        task: dict[str, Any],
        *,
        fatal: bool,
        error_message: str | None = None,
        error_type: str | None = None,
    ) -> None:
        """更新失败队列与统计。"""
        task_id = task.get("task_id")
        now = datetime.now(UTC).isoformat()
        detail = {
            "task_id": task_id,
            "task_type": task.get("type"),
            "fatal": fatal,
            "retryable": not fatal,
            "error": error_message,
            "error_type": error_type,
        }
        details = task.get("details", {})
        if isinstance(details, dict):
            detail.update({
                "article_id": details.get("article_id"),
                "source_url": details.get("source_url"),
            })
        stats.failure_details.append(detail)

        matching = [t for t in alive_failed if t.get("task_id") == task_id]
        if matching:
            existing = matching[0]
            existing["retry_count"] = existing.get("retry_count", 0) + 1
            existing["failed_at"] = now
            existing["error"] = error_message
            existing["error_type"] = error_type
            existing["fatal"] = fatal
            if fatal:
                existing["fatal_error"] = error_message
                existing["fatal_error_type"] = error_type
            if existing["retry_count"] >= MAX_RETRY_COUNT:
                dead_failed.append(existing)
                alive_failed.remove(existing)
                stats.dead += 1
        else:
            new_failed = dict(task)
            new_failed["failed_at"] = now
            new_failed["retry_count"] = 1
            new_failed["error"] = error_message
            new_failed["error_type"] = error_type
            new_failed["fatal"] = fatal
            if fatal:
                new_failed["fatal_error"] = error_message
                new_failed["fatal_error_type"] = error_type
            alive_failed.append(new_failed)

    for index, task in enumerate(unique_tasks, start=1):
        if cancel_check is not None and await cancel_check():
            raise JobControlInterrupted("cancel")
        task_id = task.get("task_id")
        if task_id in failed_ids:
            if progress_callback is not None and total > 0:
                details = task.get("details", {})
                progress_callback(
                    {
                        "job_type": "pipeline-run",
                        "stage": "process",
                        "current": overall_current if overall_current is not None else index,
                        "total": overall_total if overall_total is not None else total,
                        "percent": round(((overall_current if overall_current is not None else index) / (overall_total if overall_total else total)) * 100, 2) if (overall_total or total) else 0.0,
                        "remaining": max((overall_total if overall_total is not None else total) - (overall_current if overall_current is not None else index), 0),
                        "current_step": f"process:{details.get('article_id') or task_id or task.get('type')}",
                        "current_trade_date": None,
                        "current_dataset": task.get("type"),
                        "status": "skipped",
                        "error": None,
                        "sub_current": index,
                        "sub_total": total,
                        "sub_percent": round((index / total) * 100, 2) if total else 0.0,
                        "sub_remaining": max(total - index, 0),
                    }
                )
            continue

        try:
            success, skipped = await _process_one(task, handlers)
        except ProcessFatalError as exc:
            error_message = str(exc)
            error_type = str(exc.details.get("error_type") or "") or None
            stats.failed += 1
            stats.fatal_error = error_message
            stats.fatal_error_type = error_type
            stats.fatal_task_id = task_id
            stats.fatal_task_type = task.get("type")
            _track_failure(task, fatal=True, error_message=error_message, error_type=error_type)
            remaining_tasks = unique_tasks[index:]
            if progress_callback is not None and total > 0:
                details = task.get("details", {})
                progress_callback(
                    {
                        "job_type": "pipeline-run",
                        "stage": "process",
                        "current": overall_current if overall_current is not None else index,
                        "total": overall_total if overall_total is not None else total,
                        "percent": round(((overall_current if overall_current is not None else index) / (overall_total if overall_total else total)) * 100, 2) if (overall_total or total) else 0.0,
                        "remaining": max((overall_total if overall_total is not None else total) - (overall_current if overall_current is not None else index), 0),
                        "current_step": f"process:{details.get('article_id') or task_id or task.get('type')}",
                        "current_trade_date": None,
                        "current_dataset": task.get("type"),
                        "status": "error",
                        "error": error_message,
                        "sub_current": index,
                        "sub_total": total,
                        "sub_percent": round((index / total) * 100, 2) if total else 0.0,
                        "sub_remaining": max(total - index, 0),
                    }
                )
            break
        if progress_callback is not None and total > 0:
            details = task.get("details", {})
            progress_callback(
                {
                    "job_type": "pipeline-run",
                    "stage": "process",
                    "current": overall_current if overall_current is not None else index,
                    "total": overall_total if overall_total is not None else total,
                    "percent": round(((overall_current if overall_current is not None else index) / (overall_total if overall_total else total)) * 100, 2) if (overall_total or total) else 0.0,
                    "remaining": max((overall_total if overall_total is not None else total) - (overall_current if overall_current is not None else index), 0),
                    "current_step": f"process:{details.get('article_id') or task_id or task.get('type')}",
                    "current_trade_date": None,
                    "current_dataset": task.get("type"),
                    "status": "success" if success and not skipped else ("skipped" if skipped else "error"),
                    "error": None if success else "task failed",
                    "sub_current": index,
                    "sub_total": total,
                    "sub_percent": round((index / total) * 100, 2) if total else 0.0,
                    "sub_remaining": max(total - index, 0),
                }
            )
        if success:
            if not skipped:
                stats.processed += 1
        else:
            stats.failed += 1
            _track_failure(task, fatal=False, error_message="task failed", error_type=None)

    if stats.fatal_error:
        _save_tasks(p_path, remaining_tasks)
    else:
        _save_tasks(p_path, [])

    # Save updated failed tasks
    _save_failed_with_metadata(f_path, alive_failed)
    # Save dead tasks discovered during processing
    if dead_failed:
        _save_failed_with_metadata(d_path, dead_failed)

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
            error=stats.fatal_error or (f"{stats.failed} failed" if stats.failed > 0 else None),
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
