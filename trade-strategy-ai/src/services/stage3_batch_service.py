from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import UUID, uuid4

from sqlalchemy import select

from src.models.job import Job, JobStatus
from src.services.stage3_prompt_runtime_service import ArticlePromptInput, Stage3PromptRuntimeService
from src.services.stage3_regression_fixtures import (
    STAGE3_FIXED_SET_GATE_VERSION,
    STAGE3_FIXED_SET_MODEL,
    RegressionArticleFixture,
    get_stage3_fixed_regression_set,
)
from src.services.stage3_regression_service import FixedFixtureGateway, RegressionRunResult, Stage3RegressionService
from src.services.stage3_single_article_service import Stage3SingleArticleService


@dataclass(slots=True)
class BatchRunResult:
    status: str
    gate_result: RegressionRunResult
    run_id: str | None
    processed_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    cached_count: int = 0
    repaired_count: int = 0
    human_attention_count: int = 0
    retry_count: int = 0
    quality_stats: dict[str, Any] = field(default_factory=dict)
    failure_reasons: list[str] = field(default_factory=list)
    rejected_or_conflicted_items: list[str] = field(default_factory=list)


class Stage3BatchService:
    service_name = "stage3-batch-service"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any],
        regression_service: Stage3RegressionService,
        manifest: list[RegressionArticleFixture] | None = None,
        gateway: FixedFixtureGateway | None = None,
        model: str = STAGE3_FIXED_SET_MODEL,
        concurrency_limit: int = 2,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._regression_service = regression_service
        self._manifest = manifest or get_stage3_fixed_regression_set()
        self._gateway = gateway or FixedFixtureGateway({item.article_revision_id: item for item in self._manifest})
        self._model = model
        self._concurrency_limit = max(1, int(concurrency_limit))
        self._runtime_service = Stage3PromptRuntimeService(
            session_scope_factory=session_scope_factory,
            gateway=self._gateway,
            model=model,
        )
        self._single_article_service = Stage3SingleArticleService(
            session_scope_factory=session_scope_factory,
            prompt_runtime_service=self._runtime_service,
        )

    async def run(self, *, dry_run: bool, limit: int, fail_after_items: int | None = None) -> BatchRunResult:
        gate_result = await self._regression_service.run_fixed_set()
        if gate_result.status != "passed":
            return BatchRunResult(status="blocked", gate_result=gate_result, run_id=None, failure_reasons=["fixed regression gate failed"])

        manifest = self._manifest[:limit]
        job = await self._get_or_create_job(dry_run=dry_run, limit=limit)
        checkpoint = ((job.runtime_state or {}).get("checkpoint") or {})
        processed_revision_ids = set(checkpoint.get("processed_revision_ids", []))
        processed_items = checkpoint.get("processed_items", [])
        processed_item_map = {
            str(item.get("article_revision_id")): item
            for item in processed_items
            if isinstance(item, dict) and item.get("article_revision_id")
        }
        existing_result = job.result if isinstance(job.result, dict) else {}
        rejected_or_conflicted_items = existing_result.get("rejected_or_conflicted_items", [])

        result = BatchRunResult(status="completed", gate_result=gate_result, run_id=str(job.id))
        if isinstance(rejected_or_conflicted_items, list):
            result.rejected_or_conflicted_items = [str(item) for item in rejected_or_conflicted_items]
        auto_review_stats: dict[str, int] = {}
        for fixture in manifest:
            revision_key = str(fixture.article_revision_id)
            if revision_key in processed_revision_ids:
                result.skipped_count += 1
                continue

            async with self._session_scope_factory() as session:
                article = await self._single_article_service._repository.get_article(session, article_id=fixture.article_id)  # noqa: SLF001
                revision = await self._single_article_service._repository.get_article_revision(  # noqa: SLF001
                    session,
                    article_id=fixture.article_id,
                    article_revision_id=fixture.article_revision_id,
                )
                assert article is not None
                assert revision is not None
                assert revision.content_hash == fixture.content_hash

            runtime_result = await self._runtime_service.analyze_article(
                ArticlePromptInput(
                    article_id=fixture.article_id,
                    article_revision_id=fixture.article_revision_id,
                    article_title=article.title,
                    article_content=revision.content_text,
                    article_content_hash=revision.content_hash,
                    source_url=article.source_url,
                    published_at=article.published_at,
                )
            )
            journey = await self._single_article_service.get_journey(
                article_id=fixture.article_id,
                article_revision_id=fixture.article_revision_id,
            )
            processed_revision_ids.add(revision_key)
            item_states = list(journey.extraction_items)
            rejected_or_conflicted = [
                str(item.review_state)
                for item in item_states
                if str(item.review_state) == "rejected"
            ]
            processed_item_map[revision_key] = {
                "article_revision_id": revision_key,
                "input_hash": runtime_result.input_hash,
                "prompt_run_id": str(runtime_result.prompt_run_id),
                "validation_state": runtime_result.validation_state,
                "prompt_retry_count": runtime_result.prompt_retry_count,
                "review_destinations": [str(item.review_destination) for item in item_states],
                "rejected_or_conflicted": bool(rejected_or_conflicted),
                "resume_point": revision_key,
            }
            result.processed_count += 1
            result.success_count += 1
            result.cached_count += int(runtime_result.cache_hit)
            result.repaired_count += runtime_result.repair_count
            human_attention = any(
                bool((item.confidence or {}).get("requires_human_confirmation"))
                for item in journey.extraction_items
            )
            result.human_attention_count += int(human_attention)
            if rejected_or_conflicted:
                result.rejected_or_conflicted_items.append(revision_key)
            for item in journey.extraction_items:
                destination = str(item.review_destination)
                auto_review_stats[destination] = auto_review_stats.get(destination, 0) + 1

            await self._update_job_checkpoint(
                job_id=job.id,
                dry_run=dry_run,
                limit=limit,
                gate_result=gate_result,
                processed_revision_ids=sorted(processed_revision_ids),
                processed_items=[processed_item_map[key] for key in sorted(processed_item_map)],
                status=JobStatus.running.value,
                quality_stats={"automatic_review_status_counts": auto_review_stats},
                rejected_or_conflicted_items=sorted(result.rejected_or_conflicted_items),
            )

            if fail_after_items is not None and result.processed_count >= fail_after_items:
                result.status = "failed"
                result.failure_count = 1
                result.failure_reasons.append("injected failure for checkpoint resume test")
                await self._update_job_checkpoint(
                    job_id=job.id,
                    dry_run=dry_run,
                    limit=limit,
                    gate_result=gate_result,
                    processed_revision_ids=sorted(processed_revision_ids),
                    processed_items=[processed_item_map[key] for key in sorted(processed_item_map)],
                    status=JobStatus.failed.value,
                    quality_stats={"automatic_review_status_counts": auto_review_stats},
                    error={"message": "injected failure for checkpoint resume test"},
                    rejected_or_conflicted_items=sorted(result.rejected_or_conflicted_items),
                )
                result.quality_stats = {"automatic_review_status_counts": auto_review_stats}
                return result

        await self._update_job_checkpoint(
            job_id=job.id,
            dry_run=dry_run,
            limit=limit,
            gate_result=gate_result,
            processed_revision_ids=sorted(processed_revision_ids),
            processed_items=[processed_item_map[key] for key in sorted(processed_item_map)],
            status=JobStatus.success.value,
            quality_stats={"automatic_review_status_counts": auto_review_stats},
            rejected_or_conflicted_items=sorted(result.rejected_or_conflicted_items),
        )
        result.quality_stats = {"automatic_review_status_counts": auto_review_stats, "concurrency_limit": self._concurrency_limit}
        return result

    async def _get_or_create_job(self, *, dry_run: bool, limit: int) -> Job:
        idempotency_key = f"stage3-article-batch:{STAGE3_FIXED_SET_GATE_VERSION}:{self._model}:{int(bool(dry_run))}:{limit}"
        async with self._session_scope_factory() as session:
            existing = (await session.execute(select(Job).where(Job.idempotency_key == idempotency_key))).scalars().first()
            if existing is not None:
                return existing
            now = datetime.now(UTC)
            job = Job(
                id=uuid4(),
                job_type="stage3-article-batch",
                status=JobStatus.pending.value,
                params={
                    "dry_run": dry_run,
                    "limit": limit,
                    "gate_version": STAGE3_FIXED_SET_GATE_VERSION,
                    "model": self._model,
                    "prompt_version": "article_taxonomy_v1",
                    "schema_version": "article_taxonomy_v1",
                    "concurrency_limit": self._concurrency_limit,
                    "retry_cap": 1,
                },
                result=None,
                error=None,
                runtime_state={
                    "schema_version": 1,
                    "checkpoint": {"processed_revision_ids": []},
                    "cursor": {"next_index": 0},
                    "stage": "ready",
                },
                progress=None,
                artifacts=[],
                created_by=self.service_name,
                idempotency_key=idempotency_key,
                retry_count=0,
                max_retries=1,
                retry_backoff_seconds=0,
                timeout_seconds=None,
                cancel_requested=False,
                cancel_requested_at=None,
                worker_id=None,
                lock_token=None,
                lock_acquired_at=None,
                heartbeat_at=None,
                scheduled_at=None,
                started_at=None,
                finished_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(job)
            await session.flush()
            return job

    async def _update_job_checkpoint(
        self,
        *,
        job_id: UUID,
        dry_run: bool,
        limit: int,
        gate_result: RegressionRunResult,
        processed_revision_ids: list[str],
        processed_items: list[dict[str, Any]],
        status: str,
        quality_stats: dict[str, Any],
        rejected_or_conflicted_items: list[str],
        error: dict[str, Any] | None = None,
    ) -> None:
        async with self._session_scope_factory() as session:
            job = await session.get(Job, job_id)
            assert job is not None
            now = datetime.now(UTC)
            checkpoint = {
                "processed_revision_ids": processed_revision_ids,
                "processed_count": len(processed_revision_ids),
                "processed_items": processed_items,
            }
            job.status = status
            job.runtime_state = {
                "schema_version": 1,
                "checkpoint": checkpoint,
                "cursor": {"next_index": len(processed_revision_ids)},
                "stage": "completed" if status == JobStatus.success.value else "processing",
                "last_safe_point": processed_revision_ids[-1] if processed_revision_ids else None,
            }
            job.progress = {
                "dry_run": dry_run,
                "limit": limit,
                "gate_version": gate_result.gate_version,
                "gate_status": gate_result.status,
                "processed_revision_ids": processed_revision_ids,
                "processed_items": processed_items,
                "resume_point": processed_revision_ids[-1] if processed_revision_ids else None,
                "quality_stats": quality_stats,
                "updated_at": now.isoformat(),
            }
            job.result = {
                "gate_version": gate_result.gate_version,
                "gate_status": gate_result.status,
                "quality_stats": quality_stats,
                "processed_revision_ids": processed_revision_ids,
                "rejected_or_conflicted_items": rejected_or_conflicted_items,
                "limit": limit,
                "dry_run": dry_run,
            }
            job.error = error
            job.updated_at = now
            if status == JobStatus.running.value and job.started_at is None:
                job.started_at = now
            if status in {JobStatus.success.value, JobStatus.failed.value}:
                job.finished_at = now
            await session.flush()
