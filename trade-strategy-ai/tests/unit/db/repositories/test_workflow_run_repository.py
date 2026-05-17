from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture()
async def workflow_run_repo_session_factory(tmp_path):
    """创建用于 WorkflowRunRepository 的 sqlite session factory。"""
    from src.models.workflow_run import WorkflowRun, WorkflowRunStep

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'workflow_run_repo.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(WorkflowRun.__table__.create)
        await conn.run_sync(WorkflowRunStep.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio()
async def test_workflow_run_repository_supports_upsert_lookup_and_filters(workflow_run_repo_session_factory) -> None:
    """仓储层应支持 workflow run 的写入、替换和过滤查询。"""
    from src.db.repositories import WorkflowRunRepository
    from src.models.workflow_run import WorkflowRun, WorkflowRunStep

    repo = WorkflowRunRepository()
    run_id = UUID("11111111-1111-1111-1111-111111111111")

    async with workflow_run_repo_session_factory() as session:
        first_run = WorkflowRun(
            id=run_id,
            workflow_id="market-scheduler",
            workflow_title="盘前工作台",
            workflow_version="run-pre-market",
            status="success",
            trigger_source="ui",
            created_by="web",
            confirmed=True,
            idempotency_key="run-001",
            started_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
            finished_at=datetime(2026, 5, 17, 10, 2, tzinfo=UTC),
            duration_ms=120000,
            input_params_json={"config_path": "config/app.yaml"},
            output_summary_json={"step_count": 1},
            error_json=None,
            metadata_json={"audit_source": {"channel": "ui"}},
            created_at=datetime(2026, 5, 17, 10, 2, tzinfo=UTC),
            updated_at=datetime(2026, 5, 17, 10, 2, tzinfo=UTC),
        )
        first_steps = [
            WorkflowRunStep(
                workflow_run_id=run_id,
                step_id="run-pre-market",
                step_name="盘前日报",
                step_order=1,
                job_id="job-001",
                job_type="run-pre-market",
                status="success",
                started_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
                finished_at=datetime(2026, 5, 17, 10, 1, tzinfo=UTC),
                duration_ms=60000,
                input_json={"config_path": "config/app.yaml"},
                output_json={"job_type": "run-pre-market"},
                error_json=None,
                artifact_refs_json=[{"artifact_id": "artifact-001", "kind": "report"}],
                metadata_json={"workflow_step_id": "run-pre-market"},
                created_at=datetime(2026, 5, 17, 10, 2, tzinfo=UTC),
                updated_at=datetime(2026, 5, 17, 10, 2, tzinfo=UTC),
            )
        ]
        await repo.upsert_run(session, first_run, first_steps)
        await session.commit()

        updated_run = WorkflowRun(
            id=run_id,
            workflow_id="market-scheduler",
            workflow_title="盘前工作台",
            workflow_version="run-pre-market",
            status="failed",
            trigger_source="ui",
            created_by="web",
            confirmed=False,
            idempotency_key="run-001",
            started_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
            finished_at=datetime(2026, 5, 17, 10, 3, tzinfo=UTC),
            duration_ms=180000,
            input_params_json={"config_path": "config/app.yaml"},
            output_summary_json={"step_count": 1},
            error_json={"type": "system_error", "message": "failed"},
            metadata_json={"audit_source": {"channel": "ui"}, "retry_count": 1},
            created_at=datetime(2026, 5, 17, 10, 3, tzinfo=UTC),
            updated_at=datetime(2026, 5, 17, 10, 3, tzinfo=UTC),
        )
        updated_steps = [
            WorkflowRunStep(
                workflow_run_id=run_id,
                step_id="run-pre-market",
                step_name="盘前日报",
                step_order=1,
                job_id="job-002",
                job_type="run-pre-market",
                status="failed",
                started_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
                finished_at=datetime(2026, 5, 17, 10, 3, tzinfo=UTC),
                duration_ms=180000,
                input_json={"config_path": "config/app.yaml"},
                output_json={"job_type": "run-pre-market"},
                error_json={"type": "system_error", "message": "failed"},
                artifact_refs_json=[],
                metadata_json={"workflow_step_id": "run-pre-market"},
                created_at=datetime(2026, 5, 17, 10, 3, tzinfo=UTC),
                updated_at=datetime(2026, 5, 17, 10, 3, tzinfo=UTC),
            )
        ]
        await repo.upsert_run(session, updated_run, updated_steps)
        await session.commit()

    async with workflow_run_repo_session_factory() as session:
        loaded = await repo.get_by_run_id(session, str(run_id))
        assert loaded is not None
        assert loaded.status == "failed"
        assert loaded.confirmed is False
        assert loaded.error_json["message"] == "failed"

        listed = await repo.list_runs(
            session,
            workflow_id="market-scheduler",
            status="failed",
            created_by="web",
            start_date=date(2026, 5, 17),
            end_date=date(2026, 5, 17),
            limit=10,
            offset=0,
        )
        assert len(listed) == 1
        assert listed[0].id == run_id

        count = await repo.count_runs(
            session,
            workflow_id="market-scheduler",
            status="failed",
            created_by="web",
            start_date=date(2026, 5, 17),
            end_date=date(2026, 5, 17),
        )
        assert count == 1

        steps = await repo.list_steps_by_run_id(session, str(run_id))
        assert len(steps) == 1
        assert steps[0].job_id == "job-002"
        assert steps[0].status == "failed"

        outside_range_count = await repo.count_runs(
            session,
            workflow_id="market-scheduler",
            start_date=date(2026, 5, 18),
            end_date=date(2026, 5, 18),
        )
        assert outside_range_count == 0
