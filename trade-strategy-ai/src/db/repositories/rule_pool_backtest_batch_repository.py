from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.rule_pool_backtest_batch import RulePoolBacktestBatch, RulePoolBacktestBatchRun


class RulePoolBacktestBatchRepository:
    async def create_batch_run(
        self,
        session: AsyncSession,
        *,
        batch_run: RulePoolBacktestBatchRun,
        batches: list[RulePoolBacktestBatch],
    ) -> RulePoolBacktestBatchRun:
        session.add(batch_run)
        for batch in batches:
            session.add(batch)
        await session.flush()
        return batch_run

    async def get_batch_run(self, session: AsyncSession, batch_run_id: str) -> RulePoolBacktestBatchRun | None:
        stmt = (
            select(RulePoolBacktestBatchRun)
            .options(selectinload(RulePoolBacktestBatchRun.batches))
            .where(RulePoolBacktestBatchRun.batch_run_id == batch_run_id)
        )
        return await session.scalar(stmt)

    async def list_batch_runs(
        self,
        session: AsyncSession,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RulePoolBacktestBatchRun]:
        stmt = (
            select(RulePoolBacktestBatchRun)
            .options(selectinload(RulePoolBacktestBatchRun.batches))
            .order_by(RulePoolBacktestBatchRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.scalars(stmt)
        return list(result.all())

    async def count_batch_runs(self, session: AsyncSession) -> int:
        value = await session.scalar(select(func.count()).select_from(RulePoolBacktestBatchRun))
        return int(value or 0)

    async def get_batch(
        self,
        session: AsyncSession,
        *,
        batch_run_id: str,
        batch_index: int,
    ) -> RulePoolBacktestBatch | None:
        stmt = select(RulePoolBacktestBatch).where(
            RulePoolBacktestBatch.batch_run_id == batch_run_id,
            RulePoolBacktestBatch.batch_index == batch_index,
        )
        return await session.scalar(stmt)

    async def update_batch_status(
        self,
        session: AsyncSession,
        *,
        batch_run_id: str,
        batch_index: int,
        status: str,
        job_id: str | UUID | None = None,
        result_json: dict[str, Any] | None = None,
        result_artifact_id: str | None = None,
        error_json: dict[str, Any] | None = None,
    ) -> RulePoolBacktestBatch | None:
        batch = await self.get_batch(session, batch_run_id=batch_run_id, batch_index=batch_index)
        if batch is None:
            return None
        batch.status = status
        if job_id is not None:
            batch.job_id = UUID(str(job_id))
        if result_json is not None:
            batch.result_json = result_json
        if result_artifact_id is not None:
            batch.result_artifact_id = result_artifact_id
        if error_json is not None:
            batch.error_json = error_json
        now = datetime.now(UTC)
        if status == "running" and batch.started_at is None:
            batch.started_at = now
        if status in {"completed", "failed", "cancelled"}:
            batch.completed_at = now
        batch.updated_at = now
        await session.flush()
        return batch

    async def update_batch_run(
        self,
        session: AsyncSession,
        *,
        batch_run_id: str,
        status: str | None = None,
        merged_result_id: str | None = None,
        config_json: dict[str, Any] | None = None,
    ) -> RulePoolBacktestBatchRun | None:
        batch_run = await self.get_batch_run(session, batch_run_id)
        if batch_run is None:
            return None
        if status is not None:
            batch_run.status = status
        if merged_result_id is not None:
            batch_run.merged_result_id = merged_result_id
        if config_json is not None:
            batch_run.config_json = config_json
        batch_run.updated_at = datetime.now(UTC)
        await session.flush()
        return batch_run
