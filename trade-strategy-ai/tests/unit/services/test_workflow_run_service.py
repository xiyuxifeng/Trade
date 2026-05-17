from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture()
async def workflow_run_service_session_factory(tmp_path):
    """创建用于 WorkflowRunService 的 sqlite session factory。"""
    from src.models.workflow_run import WorkflowRun, WorkflowRunStep

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'workflow_run_service.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(WorkflowRun.__table__.create)
        await conn.run_sync(WorkflowRunStep.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


def _build_workflow_run_context() -> tuple[object, object]:
    """构造一个最小可持久化的 workflow runtime context。"""
    from src.services.runtime_contracts import ArtifactRef, RunContext, StepInput, StepResult, UserContext, WorkflowRunContext

    run_context = RunContext(
        run_id="11111111-1111-1111-1111-111111111111",
        job_id="11111111-1111-1111-1111-111111111111",
        workflow_id="market-scheduler",
        status="success",
        created_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
        started_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
        finished_at=datetime(2026, 5, 17, 10, 2, tzinfo=UTC),
        trigger_source="ui",
    )
    user_context = UserContext(user_id="web", username="web", roles=["operator"])
    step_input = StepInput(
        step_name="run-pre-market",
        payload={"config_path": "config/app.yaml"},
        input_id="11111111-1111-1111-1111-111111111111:run-pre-market",
        metadata={"order": 1, "required_job_type": "run-pre-market"},
    )
    step_result = StepResult(
        step_name="run-pre-market",
        status="success",
        payload={"summary": {"status": "ok"}},
        artifacts=[
            ArtifactRef(
                artifact_id="artifact-001",
                job_id="job-001",
                kind="report",
                title="盘前日报",
                safe_download_url="/api/ui/v1/artifacts/artifact-001/download",
                metadata={"format": "json"},
            )
        ],
        started_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
        finished_at=datetime(2026, 5, 17, 10, 2, tzinfo=UTC),
        duration_ms=120000,
        metadata={"job_id": "job-001", "job_type": "run-pre-market"},
    )
    workflow_run = WorkflowRunContext(
        run_context=run_context,
        user_context=user_context,
        workflow_params={"config_path": "config/app.yaml"},
        step_inputs=[step_input],
        step_results=[step_result],
        artifacts=step_result.artifacts,
        metadata={"idempotency_key": "run-001"},
    )
    return run_context, workflow_run


@pytest.mark.asyncio()
async def test_workflow_run_service_records_and_queries_runs(workflow_run_service_session_factory) -> None:
    """WorkflowRunService 应能落库并查询 workflow run 事实源。"""
    from src.db.repositories import WorkflowRunRepository
    from src.services.workflow_run_service import WorkflowRunService
    from src.services.workflow_service import WorkflowDefinition, WorkflowStep

    workflow = WorkflowDefinition(
        workflow_id="market-scheduler",
        title="盘前工作台",
        description="market workflow",
        job_type="run-pre-market",
        permissions="operator",
        steps=[
            WorkflowStep(
                step_id="run-pre-market",
                title="执行盘前日报",
                description="generate report",
                required_job_type="run-pre-market",
                parameters=["config_path"],
                param_schema={"fields": {"config_path": {"type": "string"}}},
                risk="low",
                requires_confirmation=False,
            )
        ],
    )
    _, workflow_run = _build_workflow_run_context()
    service = WorkflowRunService(
        session_factory=workflow_run_service_session_factory,
        repository=WorkflowRunRepository(),
    )

    recorded = await service.record_workflow_run(
        workflow=workflow,
        workflow_run=workflow_run,
        confirmed=True,
        audit_source={"channel": "ui", "path": "/api/ui/v1/workflows/market-scheduler/run"},
    )
    assert recorded.status == "ok"
    assert recorded.payload["workflow_run"]["confirmed"] is True
    assert recorded.payload["workflow_run"]["workflow_id"] == "market-scheduler"
    assert recorded.payload["step_count"] == 1

    listed = await service.list_workflow_runs(
        workflow_id="market-scheduler",
        status="success",
        created_by="web",
        limit=10,
        offset=0,
    )
    assert listed.status == "ok"
    assert listed.payload["page"]["count"] == 1
    assert listed.payload["items"][0]["confirmed"] is True
    assert listed.payload["items"][0]["workflow_title"] == "盘前工作台"

    detail = await service.get_workflow_run("11111111-1111-1111-1111-111111111111")
    assert detail.status == "ok"
    assert detail.payload["workflow_run"]["workflow_id"] == "market-scheduler"
    assert detail.payload["steps"][0]["artifact_refs_json"][0]["artifact_id"] == "artifact-001"
    assert detail.payload["page"]["count"] == 1

    steps = await service.list_workflow_run_steps("11111111-1111-1111-1111-111111111111", limit=10, offset=0)
    assert steps.status == "ok"
    assert steps.payload["workflow_run_id"] == "11111111-1111-1111-1111-111111111111"
    assert steps.payload["items"][0]["job_type"] == "run-pre-market"


@pytest.mark.asyncio()
async def test_workflow_run_service_rejects_invalid_pagination(workflow_run_service_session_factory) -> None:
    """分页参数非法时应返回结构化错误。"""
    from src.services.workflow_run_service import WorkflowRunService

    service = WorkflowRunService(session_factory=workflow_run_service_session_factory)

    result = await service.list_workflow_runs(limit=0, offset=-1)
    assert result.status == "error"
    assert result.payload["error"]["type"] == "invalid_query"


@pytest.mark.asyncio()
async def test_workflow_run_service_rejects_invalid_workflow_run_id(workflow_run_service_session_factory) -> None:
    """非法 workflow run id 应返回结构化错误。"""
    from src.services.workflow_run_service import WorkflowRunService

    service = WorkflowRunService(session_factory=workflow_run_service_session_factory)

    detail = await service.get_workflow_run("not-a-uuid")
    assert detail.status == "error"
    assert detail.payload["error"]["type"] == "invalid_query"

    steps = await service.list_workflow_run_steps("not-a-uuid")
    assert steps.status == "error"
    assert steps.payload["error"]["type"] == "invalid_query"
