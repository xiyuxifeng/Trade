from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.job import Job
from src.common.paths import project_root


def _build_job_service(tmp_path: Path):
    """创建一个可用于 JobService 单测的临时 SQLite 服务实例。"""
    from src.services.job_service import JobService

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

    service = JobService(session_scope_factory=_session_scope, job_base_dir=tmp_path / "jobs")
    return service, engine


def test_job_service_is_exported_and_instantiable() -> None:
    """JobService 应能直接导入并实例化。"""
    from src.services import JobService

    service = JobService()
    assert service.service_name == "job"
    assert service._job_base_dir == project_root() / "data" / "jobs"


def test_create_get_list_job(tmp_path: Path) -> None:
    """JobService 应支持创建、查询和列表。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(
        service.create_job(
            job_type="backtest-run",
            params={"trader_id": "trader_a"},
            created_by="web",
            idempotency_key="idem-001",
        )
    )
    job_id = created.payload["job"]["id"]
    loaded = asyncio.run(service.get_job(job_id))
    listed = asyncio.run(service.list_jobs())

    assert created.status == "ok"
    assert created.payload["created"] is True
    assert created.payload["job"]["created_by"] == "web"
    assert loaded.payload["job"]["job_type"] == "backtest-run"
    assert listed.payload["count"] == 1
    assert listed.payload["items"][0]["id"] == job_id

    asyncio.run(engine.dispose())


def test_idempotent_create_returns_existing_job(tmp_path: Path) -> None:
    """幂等键重复时不应创建新 Job。"""
    service, engine = _build_job_service(tmp_path)

    first = asyncio.run(
        service.create_job(job_type="pipeline-run", params={}, created_by="web", idempotency_key="idem-002")
    )
    second = asyncio.run(
        service.create_job(job_type="pipeline-run", params={}, created_by="web", idempotency_key="idem-002")
    )
    listed = asyncio.run(service.list_jobs())

    assert first.payload["created"] is True
    assert second.payload["created"] is False
    assert listed.payload["count"] == 1

    asyncio.run(engine.dispose())


def test_job_state_transitions_and_cancel(tmp_path: Path) -> None:
    """JobService 应支持启动、完成、失败和取消。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="pipeline-run", params={}, created_by="web"))
    job_id = created.payload["job"]["id"]

    running = asyncio.run(service.start_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))
    completed = asyncio.run(service.complete_job(job_id=job_id, result={"ok": True}))

    other = asyncio.run(service.create_job(job_type="run-pre-market", params={}, created_by="web"))
    other_id = other.payload["job"]["id"]
    failed = asyncio.run(service.fail_job(job_id=other_id, error="boom"))

    third = asyncio.run(service.create_job(job_type="run-after-close", params={}, created_by="web"))
    third_id = third.payload["job"]["id"]
    cancelled = asyncio.run(service.cancel_job(job_id=third_id, reason="stop now"))

    assert running.payload["job"]["status"] == "running"
    assert completed.payload["job"]["status"] == "success"
    assert failed.payload["job"]["status"] == "failed"
    assert failed.payload["job"]["retry_count"] == 1
    assert cancelled.payload["job"]["status"] == "cancelled"
    assert cancelled.payload["job"]["cancel_requested"] is True
    assert cancelled.payload["job"]["cancel_requested_at"] is not None
    assert cancelled.payload["job"]["created_by"] == "web"

    asyncio.run(engine.dispose())


def test_running_job_cancel_request_is_finalized_on_completion(tmp_path: Path) -> None:
    """运行中的 Job 收到取消请求后，应在完成时转为 cancelled。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="pipeline-run", params={}, created_by="web"))
    job_id = created.payload["job"]["id"]
    asyncio.run(service.start_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))

    requested = asyncio.run(service.cancel_job(job_id=job_id, reason="stop now"))
    completed = asyncio.run(service.complete_job(job_id=job_id, result={"ok": True}))

    assert requested.payload["job"]["status"] == "running"
    assert requested.payload["job"]["cancel_requested"] is True
    assert completed.payload["job"]["status"] == "cancelled"
    assert completed.payload["job"]["error"]["type"] == "cancelled"

    asyncio.run(engine.dispose())


def test_job_log_and_artifact_binding(tmp_path: Path) -> None:
    """JobService 应支持日志追加与产物绑定。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="run-pre-market", params={}, created_by="web"))
    job_id = created.payload["job"]["id"]

    logged = asyncio.run(service.append_log(job_id=job_id, line="hello"))
    bound = asyncio.run(
        service.bind_artifact(
            job_id=job_id,
            kind="html",
            path=tmp_path / "a.html",
            metadata={"source": "dashboard"},
        )
    )

    assert "job.log" in logged.payload["log_path"]
    assert Path(logged.payload["log_path"]).exists()
    assert bound.payload["artifact"]["kind"] == "html"
    assert bound.payload["job"]["artifacts"][0]["metadata"]["source"] == "dashboard"

    asyncio.run(engine.dispose())


def test_job_directory_materializes_files(tmp_path: Path) -> None:
    """Job 目录应固定包含 params、result 和 artifacts 文件。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(
        service.create_job(
            job_type="pipeline-run",
            params={"config_path": "config/app.yaml", "force": True},
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]
    job_dir = Path(created.payload["job_dir"])

    assert job_dir.exists()
    assert Path(created.payload["log_path"]).exists()
    assert Path(created.payload["params_path"]).exists()
    assert Path(created.payload["artifacts_path"]).exists()

    params_data = Path(created.payload["params_path"]).read_text(encoding="utf-8")
    assert '"config_path": "config/app.yaml"' in params_data
    assert '"force": true' in params_data

    completed = asyncio.run(service.complete_job(job_id=job_id, result={"ok": True}))
    result_path = Path(completed.payload["job_dir"]) / "result.json"
    assert result_path.exists()
    assert '"status": "success"' in result_path.read_text(encoding="utf-8")
    assert '"ok": true' in result_path.read_text(encoding="utf-8")

    asyncio.run(engine.dispose())


def test_job_timeout_and_recovery(tmp_path: Path) -> None:
    """JobService 应支持超时标记与 stale 恢复。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="crawl", params={}, created_by="web", retry_backoff_seconds=30))
    job_id = created.payload["job"]["id"]
    asyncio.run(service.start_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))

    timed_out = asyncio.run(service.mark_timed_out(job_id=job_id, reason="timeout"))
    assert timed_out.payload["job"]["status"] == "failed"
    assert timed_out.payload["job"]["error"]["type"] == "timeout"
    assert timed_out.payload["job"]["scheduled_at"] is not None

    stale = asyncio.run(service.create_job(job_type="pipeline-step", params={}, created_by="web"))
    stale_id = stale.payload["job"]["id"]
    asyncio.run(service.start_job(job_id=stale_id, worker_id="worker-2", lock_token="lock-2"))
    recovered = asyncio.run(service.recover_stale_jobs(stale_before=datetime.now(UTC) + timedelta(seconds=1)))

    assert recovered.payload["count"] >= 1
    assert stale_id in recovered.payload["job_ids"]

    asyncio.run(engine.dispose())
