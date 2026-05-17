from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.job import Job
from src.models.job_audit_event import JobAuditEvent
from src.services.job_audit_query_service import JobAuditQueryService
from src.services.job_service import JobService


def _build_services(tmp_path: Path):
    """创建可用于审计查询单测的临时服务。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Job.__table__.create)
            await conn.run_sync(JobAuditEvent.__table__.create)

    asyncio.run(_init_schema())

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    job_service = JobService(session_scope_factory=_session_scope, job_base_dir=tmp_path / "jobs")
    query_service = JobAuditQueryService(session_scope_factory=_session_scope)
    return job_service, query_service, engine


def test_list_job_audits_filters_and_paginates(tmp_path: Path) -> None:
    """Job 审计查询应支持过滤、确认标记和分页。"""
    job_service, query_service, engine = _build_services(tmp_path)

    async def _seed():
        created = await job_service.create_job(
            job_type="pipeline-run",
            params={"config_path": "config/app.yaml"},
            created_by="web",
            confirmed=True,
            audit_source={"channel": "ui", "path": "/api/ui/v1/jobs", "method": "POST"},
        )
        await job_service.create_job(
            job_type="run-pre-market",
            params={"config_path": "config/app.yaml"},
            created_by="ops",
            confirmed=False,
            audit_source={"channel": "ui", "path": "/api/ui/v1/jobs", "method": "POST"},
        )
        await job_service.start_job(job_id=created.payload["job"]["id"], worker_id="worker-1", lock_token="lock-1")
        await job_service.complete_job(job_id=created.payload["job"]["id"], result={"ok": True})

    asyncio.run(_seed())

    today = datetime.now(UTC).date()
    result = asyncio.run(
        query_service.list_job_audits(
            actor="web",
            job_type="pipeline-run",
            operation="create",
            start_date=today,
            end_date=today,
            confirmed=True,
            skip=0,
            limit=10,
        )
    )

    assert result.status == "ok"
    assert result.payload["page"]["total"] == 1
    assert result.payload["summary"]["confirmed_count"] == 1
    assert result.payload["items"][0]["job_type"] == "pipeline-run"
    assert result.payload["items"][0]["operation"] == "create"
    assert result.payload["items"][0]["confirmed"] is True
    assert result.payload["items"][0]["payload"]["request_context"]["confirmed"] is True

    asyncio.run(engine.dispose())


def test_get_job_audit_detail_returns_safe_summary_and_events(tmp_path: Path) -> None:
    """Job 审计详情应返回安全的 Job 摘要、审计事件和产物链接。"""
    job_service, query_service, engine = _build_services(tmp_path)

    async def _seed():
        created = await job_service.create_job(
            job_type="backtest-run",
            params={"config_path": "config/app.yaml"},
            created_by="web",
            confirmed=True,
            audit_source={"channel": "ui", "path": "/api/ui/v1/jobs", "method": "POST"},
        )
        job_id = created.payload["job"]["id"]
        await job_service.start_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1")
        report_path = tmp_path / "report.html"
        report_path.write_text("<html></html>", encoding="utf-8")
        await job_service.bind_artifact(
            job_id=job_id,
            kind="report",
            path=report_path,
            title="回测报告",
            summary="backtest report",
            metadata={"source": "job"},
        )
        await job_service.complete_job(job_id=job_id, result={"ok": True})
        return job_id

    job_id = asyncio.run(_seed())
    result = asyncio.run(query_service.get_job_audit_detail(job_id))

    assert result.status == "ok"
    assert result.payload["job"]["id"] == job_id
    assert "params" not in result.payload["job"]
    assert result.payload["summary"]["event_count"] >= 3
    assert result.payload["summary"]["confirmed_count"] == 1
    assert result.payload["items"][0]["operation"] == "create"
    assert result.payload["items"][0]["confirmed"] is True
    assert result.payload["items"][0]["payload"]["request_context"]["confirmed"] is True
    assert result.payload["job"]["artifacts"][0]["safe_download_url"].endswith("/download")

    asyncio.run(engine.dispose())
