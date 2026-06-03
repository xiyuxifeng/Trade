from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.config_profile import ConfigProfile
from src.models.backtest_result_run import BacktestResultRun
from src.models.job import Job
from src.models.job_audit_event import JobAuditEvent
from src.common.paths import project_root


def _build_job_service(tmp_path: Path, *, config_profile_service=None):
    """创建一个可用于 JobService 单测的临时 SQLite 服务实例。"""
    from src.services.job_service import JobService

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

    service = JobService(
        session_scope_factory=_session_scope,
        job_base_dir=tmp_path / "jobs",
        config_profile_service=config_profile_service,
    )
    return service, engine


def _build_backtest_job_service(tmp_path: Path):
    """创建一个可用于回测摘要落库的临时 JobService。"""
    from src.services.job_service import JobService

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'backtest_jobs.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Job.__table__.create)
            await conn.run_sync(JobAuditEvent.__table__.create)
            await conn.run_sync(BacktestResultRun.__table__.create)

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

    service = JobService(
        session_scope_factory=_session_scope,
        job_base_dir=tmp_path / "jobs",
    )
    return service, engine


def _build_profile_service(tmp_path: Path):
    """创建一个可用于 ConfigProfileService 单测的临时 SQLite 服务实例。"""
    from src.services.config_profile_service import ConfigProfileService

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'profiles.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(ConfigProfile.__table__.create)

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

    service = ConfigProfileService(session_scope_factory=_session_scope, snapshot_root=tmp_path / "profile_snapshots")
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
    assert created.payload["job"]["progress"] is None
    assert loaded.payload["job"]["job_type"] == "backtest-run"
    assert loaded.payload["job"]["progress"] is None
    assert loaded.payload["job"]["audit_events"][0]["operation"] == "create"
    assert loaded.payload["job"]["audit_events"][0]["actor"] == "web"
    assert loaded.payload["job"]["audit_events"][0]["params_summary"]["trader_id"] == "trader_a"
    assert listed.payload["count"] == 1
    assert listed.payload["items"][0]["id"] == job_id
    assert listed.payload["items"][0]["progress"] is None

    asyncio.run(engine.dispose())


def test_update_job_progress_persists_and_serializes(tmp_path: Path) -> None:
    """JobService 应支持写入并读取结构化进度。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="kaipan-fetch", params={}, created_by="web"))
    job_id = created.payload["job"]["id"]

    progress = {
        "current": 1,
        "total": 3,
        "percent": 33.3,
        "remaining": 2,
        "current_trade_date": "2026-05-20",
        "current_slot": "09-25",
        "current_fetcher": "market_sentiment",
    }
    updated = asyncio.run(service.update_job_progress(job_id=job_id, progress=progress))
    loaded = asyncio.run(service.get_job(job_id))
    listed = asyncio.run(service.list_jobs())

    assert updated.status == "ok"
    assert updated.payload["job"]["progress"]["current"] == progress["current"]
    assert updated.payload["job"]["progress"]["total"] == progress["total"]
    assert updated.payload["job"]["progress"]["percent"] == progress["percent"]
    assert updated.payload["job"]["progress"]["remaining"] == progress["remaining"]
    assert updated.payload["job"]["progress"]["current_trade_date"] == progress["current_trade_date"]
    assert updated.payload["job"]["progress"]["current_slot"] == progress["current_slot"]
    assert updated.payload["job"]["progress"]["current_fetcher"] == progress["current_fetcher"]
    assert updated.payload["job"]["progress"]["updated_at"] is not None
    assert loaded.payload["job"]["progress"] == updated.payload["job"]["progress"]
    assert listed.payload["items"][0]["progress"] == updated.payload["job"]["progress"]

    asyncio.run(engine.dispose())


def test_serialize_job_includes_runtime_state(tmp_path: Path) -> None:
    """Job 详情序列化应透出 runtime_state，供 pause/resume checkpoint 使用。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="ohlcv-crawl", params={"symbols": ["000001.SZ"]}, created_by="web"))
    job_id = created.payload["job"]["id"]

    async def _set_runtime_state() -> None:
        async with service._ensure_session_factory()() as session:  # noqa: SLF001
            job = await service._load_job(session, job_id)  # noqa: SLF001
            assert job is not None
            job.runtime_state = {"schema_version": 1, "checkpoint_type": "symbol"}
            await session.flush()

    asyncio.run(_set_runtime_state())
    loaded = asyncio.run(service.get_job(job_id))

    assert loaded.payload["job"]["runtime_state"]["checkpoint_type"] == "symbol"
    assert loaded.payload["job"]["runtime_state"]["schema_version"] == 1

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
    assert len(cancelled.payload["job"]["audit_events"]) >= 2

    asyncio.run(engine.dispose())


def test_heartbeat_job_records_audit_at_most_once_per_hour(tmp_path: Path) -> None:
    """心跳应持续刷新 heartbeat_at，但审计最多每小时记录一次。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="pipeline-run", params={}, created_by="web"))
    job_id = created.payload["job"]["id"]
    asyncio.run(service.start_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))

    first = asyncio.run(service.heartbeat_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))
    second = asyncio.run(service.heartbeat_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))

    first_heartbeat_at = datetime.fromisoformat(first.payload["job"]["heartbeat_at"])
    second_heartbeat_at = datetime.fromisoformat(second.payload["job"]["heartbeat_at"])

    assert second_heartbeat_at >= first_heartbeat_at
    assert len([event for event in second.payload["job"]["audit_events"] if event["operation"] == "heartbeat"]) == 1

    asyncio.run(engine.dispose())


def test_heartbeat_job_records_audit_again_after_one_hour(tmp_path: Path) -> None:
    """超过一小时后，心跳审计应再次记录。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="pipeline-run", params={}, created_by="web"))
    job_id = created.payload["job"]["id"]
    asyncio.run(service.start_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))

    asyncio.run(service.heartbeat_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))

    async def _backdate_last_heartbeat() -> None:
        session_scope = service._ensure_session_factory()  # noqa: SLF001
        async with session_scope() as session:
            stmt = (
                select(JobAuditEvent)
                .where(JobAuditEvent.job_id == UUID(job_id), JobAuditEvent.operation == "heartbeat")
                .order_by(JobAuditEvent.event_at.desc(), JobAuditEvent.created_at.desc(), JobAuditEvent.id.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            event = result.scalar_one()
            event.event_at = datetime.now(UTC) - timedelta(hours=2)

    asyncio.run(_backdate_last_heartbeat())

    updated = asyncio.run(service.heartbeat_job(job_id=job_id, worker_id="worker-1", lock_token="lock-1"))

    heartbeat_events = [event for event in updated.payload["job"]["audit_events"] if event["operation"] == "heartbeat"]
    assert len(heartbeat_events) == 2

    asyncio.run(engine.dispose())


def test_fail_job_emits_alerts_by_job_type(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """JobService.fail_job 应按 job_type 触发对应告警规则。"""
    service, engine = _build_job_service(tmp_path)

    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def fake_config(path=None):
        return SimpleNamespace(
            config=SimpleNamespace(
                alerting={
                    "enabled": True,
                    "channel": "dingtalk",
                    "aggregation": {"window_minutes": 60, "max_count": 100},
                    "dingtalk": {"webhook_url": "https://example.invalid"},
                    "feishu": {"webhook_url": ""},
                    "wecom": {"webhook_url": ""},
                    "min_level": "WARNING",
                    "console_output": True,
                }
            )
        )

    monkeypatch.setattr("src.common.config.load_app_config", fake_config)

    def record(name: str):
        def _inner(*args, **kwargs):
            calls.append((name, args, kwargs))

        return _inner

    monkeypatch.setattr("src.alerting.rules.fire_pipeline_failure_alert", record("pipeline"))
    monkeypatch.setattr("src.alerting.rules.fire_backtest_failure_alert", record("backtest"))
    monkeypatch.setattr("src.alerting.rules.fire_provider_failure_alert", record("provider"))
    monkeypatch.setattr("src.alerting.rules.fire_agent_failure_alert", record("agent"))

    job_ids = {}
    for job_type in ("pipeline-run", "backtest-run", "kaipan-fetch", "run-pre-market"):
        created = asyncio.run(service.create_job(job_type=job_type, params={}, created_by="web"))
        job_ids[job_type] = created.payload["job"]["id"]

    asyncio.run(service.fail_job(job_id=job_ids["pipeline-run"], error="boom"))
    asyncio.run(service.fail_job(job_id=job_ids["backtest-run"], error="boom"))
    asyncio.run(service.fail_job(job_id=job_ids["kaipan-fetch"], error="akshare timeout"))
    asyncio.run(service.fail_job(job_id=job_ids["run-pre-market"], error="boom"))

    assert [item[0] for item in calls] == ["pipeline", "backtest", "provider", "agent"]

    asyncio.run(engine.dispose())


def test_job_pause_resume_and_retry_flow(tmp_path: Path) -> None:
    """JobService 应支持暂停、恢复和错误重试。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="ohlcv-crawl", params={"symbols": ["000001.SZ"]}, created_by="web"))
    job_id = created.payload["job"]["id"]

    paused = asyncio.run(service.pause_job(job_id=job_id, actor="web", reason="need to wait"))
    resumed = asyncio.run(service.resume_job(job_id=job_id, actor="web"))

    failed_job = asyncio.run(service.create_job(job_type="backtest-run", params={"trader_id": "trader_a", "date_from": "2026-05-01", "date_to": "2026-05-02"}, created_by="web"))
    failed_job_id = failed_job.payload["job"]["id"]
    failed = asyncio.run(service.fail_job(job_id=failed_job_id, error={"type": "runner_error", "message": "boom"}))
    retried = asyncio.run(service.retry_job(job_id=failed_job_id, actor="web"))

    assert paused.payload["job"]["status"] == "paused"
    assert paused.payload["job"]["runtime_state"]["paused"] is True
    assert paused.payload["job"]["runtime_state"]["pause_reason"] == "need to wait"
    assert resumed.payload["job"]["status"] == "pending"
    assert resumed.payload["job"]["runtime_state"]["paused"] is False
    assert resumed.payload["job"]["runtime_state"]["resumed_at"] is not None
    assert failed.payload["job"]["status"] == "failed"
    assert retried.payload["job"]["status"] == "pending"
    assert retried.payload["job"]["error"] is None
    assert retried.payload["job"]["runtime_state"]["retried_at"] is not None

    asyncio.run(engine.dispose())


def test_complete_backtest_job_persists_summary_run(tmp_path: Path) -> None:
    """完成回测 Job 时应同步落库 backtest_result_runs。"""
    from src.db.repositories import BacktestResultRunRepository

    service, engine = _build_backtest_job_service(tmp_path)

    created = asyncio.run(
        service.create_job(
            job_type="backtest-run",
            params={
                "trader_id": "trader_a",
                "date_from": "2026-05-01",
                "date_to": "2026-05-05",
            },
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]

    result_payload = {
        "request": {
            "trader_id": "trader_a",
            "date_from": "2026-05-01",
            "date_to": "2026-05-05",
            "benchmark_symbol": "000300.SH",
            "market_regime_version": "market-regime-v3",
            "source_feature_version": "market-regime-features-v3",
            "mode": "full",
            "scoring_profile": "stage5",
            "strategy_version_id": "sv-1",
        },
        "result": {
            "benchmark_symbol": "000300.SH",
            "regime_version": "market-regime-v3",
            "source_feature_version": "market-regime-features-v3",
            "regime_metrics": [{"regime_version": "market-regime-v3"}],
            "rule_regime_metrics": {"rule-1": {"score": 0.9}},
            "summary": {
                "total_days": 5,
                "total_trades": 3,
                "valid_trades": 2,
                "skipped_trades": 1,
                "win_rate": 0.67,
                "avg_return_pct": 0.12,
            },
        },
        "summary": {
            "total_days": 5,
            "total_trades": 3,
            "valid_trades": 2,
            "skipped_trades": 1,
            "win_rate": 0.67,
            "avg_return_pct": 0.12,
        },
        "fingerprint": "fp-1",
    }

    completed = asyncio.run(service.complete_job(job_id=job_id, result=result_payload))
    assert completed.payload["job"]["status"] == "success"

    async def _assert_run() -> None:
        session_scope = service._ensure_session_factory()
        async with session_scope() as session:
            repo = BacktestResultRunRepository()
            run = await repo.get_by_source_job_id(session, job_id)
            assert run is not None
            assert run.request_trader_id == "trader_a"
            assert run.strategy_version_id == "sv-1"
            assert run.summary_json["total_days"] == 5
            assert run.fingerprint == "fp-1"

    asyncio.run(_assert_run())
    asyncio.run(engine.dispose())


def test_complete_backtest_job_raises_when_summary_persistence_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """回测摘要落库失败时不应静默成功。"""
    service, engine = _build_backtest_job_service(tmp_path)

    created = asyncio.run(
        service.create_job(
            job_type="backtest-run",
            params={
                "trader_id": "trader_a",
                "date_from": "2026-05-01",
                "date_to": "2026-05-05",
            },
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]

    async def _boom(*args, **kwargs):  # noqa: ANN001, ANN002
        raise RuntimeError("summary persistence boom")

    monkeypatch.setattr("src.services.job_service.BacktestResultRunRepository.upsert_run", _boom)

    with pytest.raises(RuntimeError, match="summary persistence boom"):
        asyncio.run(service.complete_job(job_id=job_id, result={"ok": True}))

    loaded = asyncio.run(service.get_job(job_id))
    assert loaded.payload["job"]["status"] == "pending"

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
            workflow_id="workflow-1",
            step_id="step-1",
            title="dashboard report",
            summary="rendered from dashboard",
            metadata={"source": "dashboard"},
        )
    )

    assert "job.log" in logged.payload["log_path"]
    assert Path(logged.payload["log_path"]).exists()
    assert bound.payload["artifact"]["kind"] == "html"
    assert bound.payload["artifact"]["step_id"] == "step-1"
    assert "path" not in bound.payload["artifact"]
    assert bound.payload["artifact"]["safe_download_url"].endswith(f"/artifacts/{bound.payload['artifact']['artifact_id']}/download")
    assert bound.payload["job"]["artifacts"][0]["metadata"]["source"] == "dashboard"
    assert bound.payload["job"]["artifacts"][0]["title"] == "dashboard report"
    assert "path" not in bound.payload["job"]["artifacts"][0]

    asyncio.run(engine.dispose())


def test_job_directory_materializes_files(tmp_path: Path) -> None:
    """Job 目录应固定包含 params、result 和 artifacts 文件。"""
    service, engine = _build_job_service(tmp_path)

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    created = asyncio.run(
        service.create_job(
            job_type="pipeline-run",
            params={"config_path": str(config_path), "force": True},
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
    assert f'"config_path": "{config_path}"' in params_data
    assert '"force": true' in params_data

    completed = asyncio.run(service.complete_job(job_id=job_id, result={"ok": True}))
    result_path = Path(completed.payload["job_dir"]) / "result.json"
    assert result_path.exists()
    assert '"status": "success"' in result_path.read_text(encoding="utf-8")
    assert '"ok": true' in result_path.read_text(encoding="utf-8")

    asyncio.run(engine.dispose())


def test_job_service_records_config_snapshot_when_config_path_present(tmp_path: Path) -> None:
    """JobService 在存在 config_path 时应记录脱敏配置快照。"""
    service, engine = _build_job_service(tmp_path)

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
database:
  url: postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai
llm:
  api_key: secret-key
""",
        encoding="utf-8",
    )

    created = asyncio.run(
        service.create_job(
            job_type="pipeline-run",
            params={"config_path": str(config_path)},
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]
    loaded = asyncio.run(service.get_job(job_id))

    assert created.status == "ok"
    assert created.payload["job"]["config_snapshot"]["config_source"] == str(config_path.resolve())
    assert created.payload["job"]["config_snapshot"]["masked_snapshot"]["llm"]["api_key"] == "***"
    assert loaded.payload["job"]["config_snapshot"]["config_hash"] == created.payload["job"]["config_snapshot"]["config_hash"]
    assert Path(created.payload["job"]["config_snapshot_path"]).exists()

    asyncio.run(engine.dispose())


def test_job_service_records_profile_snapshot_when_profile_id_present(tmp_path: Path) -> None:
    """JobService 在存在 profile_id 时应记录冻结 Profile 快照。"""
    profile_service, profile_engine = _build_profile_service(tmp_path)
    service, job_engine = _build_job_service(tmp_path, config_profile_service=profile_service)

    profile = asyncio.run(profile_service.create_default_profile(environment="dev", created_by="system"))
    asyncio.run(profile_service.update_profile(profile.profile_id, sections={"llm": {"model": "gpt-5"}}))

    created = asyncio.run(
        service.create_job(
            job_type="pipeline-run",
            params={"profile_id": profile.profile_id},
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]
    loaded = asyncio.run(service.get_job(job_id))

    assert created.status == "ok"
    assert created.payload["job"]["profile_snapshot"]["profile_id"] == profile.profile_id
    assert created.payload["profile_snapshot_path"] is not None
    assert Path(created.payload["profile_snapshot_path"]).exists()
    assert loaded.payload["job"]["profile_snapshot"]["profile_id"] == profile.profile_id
    assert loaded.payload["job"]["profile_snapshot"]["sections"]["llm"]["model"] == "gpt-5"
    assert Path(loaded.payload["job"]["profile_snapshot_path"]).exists()

    asyncio.run(profile_engine.dispose())
    asyncio.run(job_engine.dispose())


def test_job_service_rejects_missing_config_file_for_snapshot_jobs(tmp_path: Path) -> None:
    """config_path 缺失时应返回结构化错误，而不是创建不完整 Job。"""
    service, engine = _build_job_service(tmp_path)

    missing_config = tmp_path / "config" / "missing.yaml"
    result = asyncio.run(
        service.create_job(
            job_type="pipeline-run",
            params={"config_path": str(missing_config)},
            created_by="web",
        )
    )

    assert result.status == "error"
    assert result.message == "config file missing"

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
    loaded = asyncio.run(service.get_job(stale_id))

    assert recovered.payload["count"] >= 1
    assert stale_id in recovered.payload["job_ids"]
    assert loaded.payload["job"]["status"] == "failed"
    assert loaded.payload["job"]["audit_events"][-1]["operation"] == "stale_recovery"
    assert loaded.payload["job"]["audit_events"][-1]["actor"] == "web"

    asyncio.run(engine.dispose())


def test_failed_job_exhausts_retries_and_is_not_listed_again(tmp_path: Path) -> None:
    """超过最大重试次数后，failed Job 不应再次进入可领取队列。"""
    service, engine = _build_job_service(tmp_path)

    retryable = asyncio.run(
        service.create_job(job_type="crawl", params={}, created_by="web", max_retries=1, retry_backoff_seconds=0)
    )
    retryable_id = retryable.payload["job"]["id"]
    first_failed = asyncio.run(service.fail_job(job_id=retryable_id, error="boom"))
    ready_after_exhaustion = asyncio.run(service.list_ready_jobs(limit=10))

    assert first_failed.payload["job"]["retry_count"] == 1
    assert first_failed.payload["job"]["scheduled_at"] is None
    assert ready_after_exhaustion.payload["count"] == 0
    assert retryable_id not in {item["id"] for item in ready_after_exhaustion.payload["items"]}

    pending = asyncio.run(service.create_job(job_type="crawl", params={}, created_by="web", max_retries=0))
    pending_id = pending.payload["job"]["id"]
    ready_pending = asyncio.run(service.list_ready_jobs(limit=10))

    assert pending_id in {item["id"] for item in ready_pending.payload["items"]}

    asyncio.run(engine.dispose())


def test_failed_job_with_non_retryable_error_exhausts_retries_immediately(tmp_path: Path) -> None:
    """不可重试错误应直接耗尽 Job 重试次数。"""
    service, engine = _build_job_service(tmp_path)

    created = asyncio.run(service.create_job(job_type="crawl", params={}, created_by="web", max_retries=3, retry_backoff_seconds=0))
    job_id = created.payload["job"]["id"]
    failed = asyncio.run(
        service.fail_job(
            job_id=job_id,
            error={"type": "permission", "message": "403 forbidden", "retryable": False},
        )
    )
    ready_after_failure = asyncio.run(service.list_ready_jobs(limit=10))

    assert failed.payload["job"]["retry_count"] == failed.payload["job"]["max_retries"]
    assert failed.payload["job"]["scheduled_at"] is None
    assert ready_after_failure.payload["count"] == 0
    assert job_id not in {item["id"] for item in ready_after_failure.payload["items"]}

    asyncio.run(engine.dispose())
