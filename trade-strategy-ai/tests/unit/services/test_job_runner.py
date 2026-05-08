from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.job import Job


def _build_job_runner(tmp_path: Path, handlers: dict[str, Any] | None = None):
    """创建一个可用于 JobRunner 单测的临时 SQLite runner。"""
    from src.services import JobRunner, JobService, ServiceResult

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Job.__table__.create)

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
    runner = JobRunner(job_service=job_service, handlers=handlers or {}, heartbeat_interval_seconds=0.01)
    return runner, job_service, engine, ServiceResult


def test_job_runner_is_exported_and_instantiable() -> None:
    """JobRunner 应能直接导入并实例化。"""
    from src.services import JobRunner
    from src.services.job_registry import get_runnable_job_types

    runner = JobRunner()
    assert runner.service_name == "job-runner"
    assert runner.supported_job_types() == get_runnable_job_types()


def test_submit_job_executes_supported_job(tmp_path: Path) -> None:
    """JobRunner 应能通过 Job 执行受控任务。"""
    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        handlers={
            "run-pre-market": lambda params: asyncio.sleep(
                0,
                result=ServiceResult(
                    status="ok",
                    payload={
                        "as_of_date": params.get("as_of_date", "2026-05-08"),
                        "html_path": str(tmp_path / "report.html"),
                    },
                    message="pre market done",
                ),
            ),
        },
    )
    submitted = asyncio.run(
        runner.submit_job(
            job_type="run-pre-market",
            params={"config_path": "config/app.yaml", "force": True, "export_html": True},
            created_by="web",
            idempotency_key="job-runner-001",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))

    assert submitted.status == "ok"
    assert submitted.payload["execution"]["job"]["status"] == "success"
    assert loaded.payload["job"]["created_by"] == "web"
    assert loaded.payload["job"]["result"]["payload"]["html_path"] == str(tmp_path / "report.html")
    assert loaded.payload["job"]["artifacts"][0]["kind"] == "result-json"
    assert any(item["kind"] == "html" for item in loaded.payload["job"]["artifacts"])
    assert (tmp_path / "jobs" / job_id / "result.json").exists()
    asyncio.run(engine.dispose())


def test_run_pending_jobs_once_processes_pending_jobs(tmp_path: Path) -> None:
    """JobRunner 应能轮询并执行 pending Job。"""
    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        handlers={
            "pipeline-run": lambda params: asyncio.sleep(
                0,
                result=ServiceResult(
                    status="ok",
                    payload={
                        "config_path": params.get("config_path", "config/app.yaml"),
                        "result": "pipeline ok",
                    },
                    message="pipeline done",
                ),
            ),
        },
    )
    created = asyncio.run(
        job_service.create_job(
            job_type="pipeline-run",
            params={"config_path": "config/app.yaml"},
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]
    processed = asyncio.run(runner.run_pending_jobs_once(limit=1))
    loaded = asyncio.run(job_service.get_job(job_id))

    assert processed.payload["count"] == 1
    assert processed.payload["items"][0]["job_id"] == job_id
    assert loaded.payload["job"]["status"] == "success"
    asyncio.run(engine.dispose())


def test_job_runner_emits_heartbeat(tmp_path: Path) -> None:
    """JobRunner 执行长任务时应定期刷新心跳。"""

    async def _handler(params: dict[str, Any]) -> Any:
        await asyncio.sleep(0.05)
        return ServiceResult(
            status="ok",
            payload={"result": "ok", "html_path": str(tmp_path / "report.html")},
            message="done",
        )

    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        handlers={"run-pre-market": _handler},
    )
    created = asyncio.run(
        job_service.create_job(
            job_type="run-pre-market",
            params={"config_path": "config/app.yaml"},
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]

    async def _run() -> None:
        task = asyncio.create_task(runner.execute_job(job_id=job_id))
        await asyncio.sleep(0.02)
        mid = await job_service.get_job(job_id)
        assert datetime.fromisoformat(mid.payload["job"]["heartbeat_at"]) >= datetime.fromisoformat(
            mid.payload["job"]["started_at"]
        )
        await task

    asyncio.run(_run())
    asyncio.run(engine.dispose())


def test_worker_respects_job_type_concurrency_limit(tmp_path: Path) -> None:
    """JobRunner 应按 job type 限制并发领取。"""

    async def _handler(params: dict[str, Any]) -> Any:
        await asyncio.sleep(0.03)
        return ServiceResult(status="ok", payload={"result": "pipeline ok"}, message="pipeline done")

    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        handlers={"pipeline-run": _handler},
    )
    runner._job_type_limits = {"pipeline-run": 1}  # noqa: SLF001
    first = asyncio.run(job_service.create_job(job_type="pipeline-run", params={}, created_by="web"))
    second = asyncio.run(job_service.create_job(job_type="pipeline-run", params={}, created_by="web"))
    processed = asyncio.run(runner.run_worker_once(limit=2))
    first_loaded = asyncio.run(job_service.get_job(first.payload["job"]["id"]))
    second_loaded = asyncio.run(job_service.get_job(second.payload["job"]["id"]))

    assert processed.payload["count"] == 1
    assert first_loaded.payload["job"]["status"] == "success"
    assert second_loaded.payload["job"]["status"] == "pending"
    asyncio.run(engine.dispose())


def test_recover_stale_jobs_marks_retryable(tmp_path: Path) -> None:
    """JobRunner 应暴露 stale 恢复后的可重试列表。"""
    runner, job_service, engine, _ = _build_job_runner(tmp_path)
    created = asyncio.run(job_service.create_job(job_type="run-after-close", params={}, created_by="web"))
    job_id = created.payload["job"]["id"]
    asyncio.run(job_service.start_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))

    async def _set_stale() -> None:
        async with job_service._ensure_session_factory()() as session:  # noqa: SLF001
            await session.execute(
                update(Job).where(Job.id == UUID(job_id)).values(heartbeat_at=datetime.now(UTC) - timedelta(hours=2))
            )
            await session.commit()

    asyncio.run(_set_stale())

    recovered = asyncio.run(runner.recover_stale_jobs(stale_before=datetime.now(UTC) - timedelta(minutes=5)))

    assert recovered.payload["count"] == 1
    assert job_id in recovered.payload["job_ids"]
    assert job_id in recovered.payload["retryable_job_ids"]
    asyncio.run(engine.dispose())
