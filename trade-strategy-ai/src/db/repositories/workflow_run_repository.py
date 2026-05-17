from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.workflow_run import WorkflowRun, WorkflowRunStep


def _date_start(value: date | None) -> datetime | None:
    """把日期转成 UTC 当日开始时间。"""
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _date_end(value: date | None) -> datetime | None:
    """把日期转成 UTC 次日开始时间，作为开区间上界。"""
    if value is None:
        return None
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone.utc)


def _coerce_uuid(value: str | UUID) -> UUID:
    """把字符串主键统一转成 UUID。"""
    return value if isinstance(value, UUID) else UUID(str(value))


class WorkflowRunRepository:
    """Workflow 运行事实源仓储。"""

    async def upsert_run(self, session: AsyncSession, run: WorkflowRun, steps: list[WorkflowRunStep]) -> WorkflowRun:
        """写入或更新 workflow run 及其 step 明细。"""
        existing = await session.get(WorkflowRun, run.id)
        if existing is None:
            session.add(run)
            await session.flush()
            existing = run
        else:
            for field in (
                "workflow_id",
                "workflow_title",
                "workflow_version",
                "status",
                "trigger_source",
                "created_by",
                "confirmed",
                "idempotency_key",
                "started_at",
                "finished_at",
                "duration_ms",
                "input_params_json",
                "output_summary_json",
                "error_json",
                "metadata_json",
            ):
                setattr(existing, field, getattr(run, field))
            await session.flush()
            await session.execute(delete(WorkflowRunStep).where(WorkflowRunStep.workflow_run_id == existing.id))
            await session.flush()

        for step in steps:
            step.workflow_run_id = existing.id
            session.add(step)
        await session.flush()
        return existing

    async def get_by_run_id(self, session: AsyncSession, run_id: str | UUID) -> WorkflowRun | None:
        """按 run_id 查询 workflow run。"""
        return await session.get(WorkflowRun, _coerce_uuid(run_id))

    async def list_runs(
        self,
        session: AsyncSession,
        *,
        workflow_id: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[WorkflowRun]:
        """按条件查询 workflow run 列表。"""
        stmt = select(WorkflowRun)
        if workflow_id:
            stmt = stmt.where(WorkflowRun.workflow_id == workflow_id)
        if status:
            stmt = stmt.where(WorkflowRun.status == status)
        if created_by:
            stmt = stmt.where(WorkflowRun.created_by == created_by)
        start_at = _date_start(start_date)
        end_at = _date_end(end_date)
        if start_at is not None:
            stmt = stmt.where(func.coalesce(WorkflowRun.created_at, WorkflowRun.started_at) >= start_at)
        if end_at is not None:
            stmt = stmt.where(func.coalesce(WorkflowRun.created_at, WorkflowRun.started_at) < end_at)
        stmt = stmt.order_by(WorkflowRun.created_at.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def count_runs(
        self,
        session: AsyncSession,
        *,
        workflow_id: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        """按条件统计 workflow run 总数。"""
        stmt = select(func.count(WorkflowRun.id))
        if workflow_id:
            stmt = stmt.where(WorkflowRun.workflow_id == workflow_id)
        if status:
            stmt = stmt.where(WorkflowRun.status == status)
        if created_by:
            stmt = stmt.where(WorkflowRun.created_by == created_by)
        start_at = _date_start(start_date)
        end_at = _date_end(end_date)
        if start_at is not None:
            stmt = stmt.where(func.coalesce(WorkflowRun.created_at, WorkflowRun.started_at) >= start_at)
        if end_at is not None:
            stmt = stmt.where(func.coalesce(WorkflowRun.created_at, WorkflowRun.started_at) < end_at)
        result = await session.scalar(stmt)
        return int(result or 0)

    async def list_steps_by_run_id(self, session: AsyncSession, run_id: str | UUID) -> list[WorkflowRunStep]:
        """按 workflow_run_id 查询 step 明细。"""
        result = await session.scalars(
            select(WorkflowRunStep)
            .where(WorkflowRunStep.workflow_run_id == _coerce_uuid(run_id))
            .order_by(WorkflowRunStep.step_order.asc())
        )
        return list(result.all())
