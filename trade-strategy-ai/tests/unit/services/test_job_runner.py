from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.backtest_result_run import BacktestResultRun
from src.models.job import Job
from src.models.job_audit_event import JobAuditEvent
from src.services.base import ServiceResult


class _FakeBacktestService:
    def __init__(self) -> None:
        self.run_calls: list[dict[str, object]] = []
        self.validate_calls: list[dict[str, object]] = []
        self.repro_calls: list[dict[str, object]] = []
        self.rule_pool_calls: list[dict[str, object]] = []

    def run_backtest(self, **kwargs):
        self.run_calls.append(kwargs)
        progress_callback = kwargs.get("progress_callback")
        if progress_callback is not None:
            progress_callback(
                {
                    "job_type": "backtest-run",
                    "stage": "backtest",
                    "current": 1,
                    "total": 2,
                    "percent": 50.0,
                    "remaining": 1,
                    "current_step": "backtest:2026-04-01",
                    "current_trade_date": "2026-04-01",
                    "status": "running",
                }
            )
            progress_callback(
                {
                    "job_type": "backtest-run",
                    "stage": "backtest",
                    "current": 2,
                    "total": 2,
                    "percent": 100.0,
                    "remaining": 0,
                    "current_step": "backtest:2026-04-02",
                    "current_trade_date": "2026-04-02",
                    "status": "success",
                }
            )
        return ServiceResult(
            status="ok",
            message="backtest completed",
            payload={
                "request": {
                    "trader_id": kwargs["trader_id"],
                    "date_from": kwargs["date_from"].isoformat(),
                    "date_to": kwargs["date_to"].isoformat(),
                    "strategy_version_id": kwargs.get("strategy_version_id"),
                    "symbols": kwargs.get("symbols") or [],
                    "benchmark_symbol": kwargs.get("benchmark_symbol"),
                    "mode": kwargs.get("mode"),
                    "use_snapshot_only": kwargs.get("use_snapshot_only"),
                    "scoring_profile": kwargs.get("scoring_profile"),
                },
                "result": {
                    "request_trader_id": kwargs["trader_id"],
                    "request_date_from": kwargs["date_from"],
                    "request_date_to": kwargs["date_to"],
                    "records": [
                        {
                            "trade_date": kwargs["date_from"],
                            "trader_id": kwargs["trader_id"],
                            "strategy_version_id": kwargs.get("strategy_version_id") or "sv-001",
                            "symbol": "000001.SZ",
                            "status": "closed",
                            "entry_price": 10.0,
                            "exit_price": 10.5,
                            "entry_date": None,
                            "exit_date": None,
                            "return_pct": 0.05,
                            "mfe": None,
                            "mae": None,
                            "volume": None,
                            "is_valid_lot_size": None,
                            "skip_reason": None,
                            "evidence_refs": [],
                        }
                    ],
                    "summary": {
                        "total_days": 3,
                        "total_trades": 6,
                        "valid_trades": 4,
                        "skipped_trades": 2,
                        "win_rate": 0.5,
                        "avg_return_pct": 0.03,
                    },
                    "result_version": "1.0",
                },
                "summary": {
                    "total_days": 3,
                    "total_trades": 6,
                    "valid_trades": 4,
                    "skipped_trades": 2,
                    "win_rate": 0.5,
                    "avg_return_pct": 0.03,
                },
                "fingerprint": "f" * 64,
            },
        )

    async def validate_rules(self, **kwargs):
        self.validate_calls.append(kwargs)
        return ServiceResult(
            status="ok",
            message="rule validation completed",
            payload={
                "trader_id": kwargs["trader_id"],
                "date_from": kwargs["date_from"].isoformat(),
                "date_to": kwargs["date_to"].isoformat(),
                "coverage": {"total": 1, "programmable": 1, "validated": 1},
                "results": [
                    {
                        "trader_id": kwargs["trader_id"],
                        "strategy_version_id": kwargs.get("strategy_version_id") or "sv-001",
                        "rule_id": "rule-001",
                        "rule_text": "rsi < 30",
                        "programmable": True,
                        "validation_status": "validated",
                        "hit_count": 2,
                        "sample_count": 4,
                        "hit_rate": 0.5,
                        "posterior_return_mean": 0.02,
                        "posterior_return_median": 0.015,
                        "notes": [],
                        "result_version": "1.0",
                    }
                ],
                "report": "# Rule Validation Report\n",
            },
        )

    def reproducibility_check(self, **kwargs):
        self.repro_calls.append(kwargs)
        return ServiceResult(
            status="ok",
            message="reproducibility check completed",
            payload={
                "request": {
                    "trader_id": kwargs["trader_id"],
                    "date_from": kwargs["date_from"].isoformat(),
                    "date_to": kwargs["date_to"].isoformat(),
                    "strategy_version_id": kwargs.get("strategy_version_id"),
                    "symbols": kwargs.get("symbols") or [],
                    "benchmark_symbol": kwargs.get("benchmark_symbol"),
                    "mode": kwargs.get("mode"),
                    "use_snapshot_only": kwargs.get("use_snapshot_only"),
                    "scoring_profile": kwargs.get("scoring_profile"),
                },
                "fingerprint_a": "f" * 64,
                "fingerprint_b": "f" * 64,
                "matches": True,
                "result_a": {},
                "result_b": {},
            },
        )

    async def run_rule_pool_backtest(self, **kwargs):
        self.rule_pool_calls.append(kwargs)
        progress_callback = kwargs.get("progress_callback")
        if progress_callback is not None:
            progress_callback(
                {
                    "job_type": "rule-pool-backtest",
                    "stage": "rule_pool_backtest",
                    "current": 1,
                    "total": 2,
                    "percent": 50.0,
                    "remaining": 1,
                    "current_step": "rule-001:2026-04-01",
                    "current_trade_date": "2026-04-01",
                    "current_dataset": "rule-001",
                    "status": "running",
                }
            )
            progress_callback(
                {
                    "job_type": "rule-pool-backtest",
                    "stage": "rule_pool_backtest",
                    "current": 2,
                    "total": 2,
                    "percent": 100.0,
                    "remaining": 0,
                    "current_step": "rule-001:2026-04-02",
                    "current_trade_date": "2026-04-02",
                    "current_dataset": "rule-001",
                    "status": "success",
                }
            )
        return ServiceResult(
            status="ok",
            message="rule pool backtest completed",
            payload={
                "request": {
                    "start_date": kwargs["start_date"].isoformat(),
                    "end_date": kwargs["end_date"].isoformat(),
                    "rule_ids": kwargs.get("rule_ids"),
                    "min_confidence": kwargs.get("min_confidence"),
                    "market_regime_version": kwargs.get("market_regime_version"),
                },
                "result": {
                    "request_trader_id": "rule_pool",
                    "request_date_from": kwargs["start_date"],
                    "request_date_to": kwargs["end_date"],
                    "benchmark_symbol": None,
                    "regime_version": kwargs.get("market_regime_version"),
                    "source_feature_version": "market-regime-features-v3",
                    "records": [],
                    "summary": {
                        "total_days": 3,
                        "total_trades": 6,
                        "valid_trades": 4,
                        "skipped_trades": 2,
                        "win_rate": 0.5,
                        "avg_return_pct": 0.03,
                    },
                    "regime_metrics": [
                        {
                            "regime_label": "trend_up",
                            "sample_count": 4,
                            "win_trades": 3,
                            "loss_trades": 1,
                            "win_rate": 0.75,
                            "avg_return": 0.02,
                            "avg_win_return": 0.03,
                            "avg_loss_return": -0.01,
                            "max_drawdown": 0.05,
                            "profit_factor": 1.5,
                            "confidence": 0.8,
                            "low_sample": False,
                        }
                    ],
                    "rule_regime_metrics": {
                        "rule-001": [
                            {
                                "regime_label": "trend_up",
                                "sample_count": 4,
                                "win_trades": 3,
                                "loss_trades": 1,
                                "win_rate": 0.75,
                                "avg_return": 0.02,
                                "avg_win_return": 0.03,
                                "avg_loss_return": -0.01,
                                "max_drawdown": 0.05,
                                "profit_factor": 1.5,
                                "confidence": 0.8,
                                "low_sample": False,
                            }
                        ]
                    },
                    "result_version": "1.0",
                },
                "summary": {
                    "total_days": 3,
                    "total_trades": 6,
                    "valid_trades": 4,
                    "skipped_trades": 2,
                    "win_rate": 0.5,
                    "avg_return_pct": 0.03,
                },
                "fingerprint": "r" * 64,
            },
        )

    def render_backtest_report(self, result, *, format: str):
        del result
        if format == "csv":
            return ServiceResult(status="ok", message="backtest report rendered", payload={"content": "trade_date,trader_id,strategy_version_id\n"})
        return ServiceResult(status="ok", message="backtest report rendered", payload={"content": "# Backtest Report\n"})


def _build_job_runner(
    tmp_path: Path,
    handlers: dict[str, Any] | None = None,
    *,
    backtest_service_factory: Any | None = None,
):
    """创建一个可用于 JobRunner 单测的临时 SQLite runner。"""
    from src.services import JobRunner, JobService, ServiceResult

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}")

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

    job_service = JobService(session_scope_factory=_session_scope, job_base_dir=tmp_path / "jobs")

    class _FakeConfigSnapshotService:
        def capture_config_snapshot(self, config_path):
            return ServiceResult(
                status="ok",
                message="config snapshot captured",
                payload={
                    "config_path": str(config_path),
                    "config_snapshot_id": "config-snapshot-001",
                    "snapshot_path": str(tmp_path / "config-snapshot.json"),
                },
            )

    class _FakeConfigProfileService:
        async def capture_profile_snapshot(
            self,
            profile_id: str,
            *,
            job_id: str | None = None,
            source: str = "job",
            config_path: str | None = None,
        ) -> Any:
            del job_id, source, config_path
            return ServiceResult(
                status="ok",
                message="profile snapshot captured",
                payload={
                    "profile_id": profile_id,
                    "profile_snapshot_id": "profile-snapshot-001",
                    "snapshot_path": str(tmp_path / "profile-snapshot.json"),
                },
            )

    job_service._config_snapshot_service = _FakeConfigSnapshotService()  # noqa: SLF001
    job_service._config_profile_service = _FakeConfigProfileService()  # noqa: SLF001
    runner = JobRunner(
        job_service=job_service,
        handlers=handlers or {},
        heartbeat_interval_seconds=0.01,
        backtest_service_factory=backtest_service_factory or _FakeBacktestService,
    )
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
    assert loaded.payload["job"]["audit_events"][0]["payload"]["request_context"]["confirmed"] is False
    assert loaded.payload["job"]["result"]["payload"]["html_path"] == str(tmp_path / "report.html")
    assert loaded.payload["job"]["artifacts"][0]["kind"] == "result-json"
    assert any(item["kind"] == "html" for item in loaded.payload["job"]["artifacts"])
    assert (tmp_path / "jobs" / job_id / "result.json").exists()
    asyncio.run(engine.dispose())


def test_run_pre_market_handler_accepts_profile_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """盘前运行 handler 应允许仅通过 Profile 提交。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    class _FakeRunService:
        def __init__(self, manager):
            self.manager = manager

        async def run_pre_market(self, **kwargs):
            calls.update(kwargs)
            return ServiceResult(
                status="ok",
                payload={"html_path": str(tmp_path / "report.html"), "result": "pre market done"},
                message="pre market done",
            )

    def _fake_build_manager(self, *, config_path):
        calls["config_path"] = config_path
        return object(), tmp_path

    monkeypatch.setattr(job_runner_module, "RunService", _FakeRunService)
    monkeypatch.setattr(job_runner_module.JobRunner, "_build_manager", _fake_build_manager, raising=False)

    runner, _, engine, ServiceResult = _build_job_runner(tmp_path)
    handler = runner._build_default_handlers()["run-pre-market"]
    result = asyncio.run(
        handler(
            {
                "profile_id": "default",
                "as_of_date": "2026-05-16",
                "force": True,
                "export_html": False,
            }
        )
    )

    assert result.status == "ok"
    assert calls["config_path"] == "config/app.yaml"
    assert calls["as_of_date"].isoformat() == "2026-05-16"


def test_kaipan_run_handler_accepts_profile_only_and_resolves_config_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kaipan 一键运行 handler 应允许仅通过 Profile 提交并解析配置路径。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    async def _fake_resolve_profile_config_path(self, profile_id: str):
        calls["profile_id"] = profile_id
        return tmp_path / "config" / "kaipan.yaml"

    class _FakeKaipanService:
        def run(self, **kwargs):
            calls.update(kwargs)
            return ServiceResult(
                status="ok",
                payload={"config_path": str(kwargs["config_path"]), "result": "kaipan done"},
                message="kaipan done",
            )

    monkeypatch.setattr(job_runner_module.ConfigProfileService, "resolve_profile_config_path", _fake_resolve_profile_config_path, raising=False)
    monkeypatch.setattr(job_runner_module, "KaipanService", _FakeKaipanService)

    runner, _, engine, _ = _build_job_runner(tmp_path)
    handler = runner._build_default_handlers()["kaipan-run"]
    result = asyncio.run(
        handler(
            {
                "profile_id": "default",
                "start_scheduler": True,
                "block": False,
            }
        )
    )

    assert result.status == "ok"
    assert calls["profile_id"] == "default"
    assert calls["config_path"] == tmp_path / "config" / "kaipan.yaml"
    assert calls["start_scheduler"] is True
    assert calls["block"] is False
    asyncio.run(engine.dispose())


def test_kaipan_fetch_job_writes_progress_to_job_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kaipan 抓取 Job 执行时应把结构化进度写回 Job 记录。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    async def _fake_resolve_profile_config_path(self, profile_id: str):
        calls["profile_id"] = profile_id
        return tmp_path / "config" / "kaipan.yaml"

    class _FakeKaipanService:
        def fetch(self, **kwargs):
            calls.update(kwargs)
            progress_callback = kwargs.get("progress_callback")
            if progress_callback is not None:
                progress_callback(
                    {
                        "job_type": "kaipan-fetch",
                        "stage": "fetch",
                        "current": 1,
                        "total": 2,
                        "percent": 50.0,
                        "remaining": 1,
                        "current_trade_date": "2026-05-01",
                        "current_slot": "09-25",
                        "current_fetcher": "market_sentiment",
                        "current_dataset": None,
                        "current_step": "fetch:market_sentiment",
                        "status": "success",
                        "updated_at": "2026-05-25T00:00:00Z",
                    }
                )
                progress_callback(
                    {
                        "job_type": "kaipan-fetch",
                        "stage": "normalize",
                        "current": 2,
                        "total": 2,
                        "percent": 100.0,
                        "remaining": 0,
                        "current_trade_date": "2026-05-01",
                        "current_slot": "09-25",
                        "current_fetcher": None,
                        "current_dataset": "hot_topics",
                        "current_step": "normalize:hot_topics",
                        "status": "success",
                        "updated_at": "2026-05-25T00:00:01Z",
                    }
                )
            return ServiceResult(
                status="ok",
                payload={
                    "config_path": str(kwargs["config_path"]),
                    "base_dir": str(tmp_path),
                    "trade_date": "2026-05-01",
                    "start_date": kwargs.get("start_date"),
                    "end_date": kwargs.get("end_date"),
                    "trade_dates": ["2026-05-01"],
                    "slots": [kwargs.get("slot", "all")],
                    "date_results": {},
                    "slot_results": {},
                    "normalize_results": {},
                },
                message="kaipan done",
            )

    monkeypatch.setattr(job_runner_module.ConfigProfileService, "resolve_profile_config_path", _fake_resolve_profile_config_path, raising=False)
    monkeypatch.setattr(job_runner_module, "KaipanService", _FakeKaipanService)

    runner, job_service, engine, _ = _build_job_runner(tmp_path)
    submitted = asyncio.run(
        runner.submit_job(
            job_type="kaipan-fetch",
            params={
                "profile_id": "default",
                "start_date": "2026-05-01",
                "end_date": "2026-05-01",
                "slot": "09-25",
            },
            created_by="web",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))

    assert submitted.status == "ok"
    assert calls["profile_id"] == "default"
    assert calls["start_date"] == "2026-05-01"
    assert calls["end_date"] == "2026-05-01"
    assert calls["slot"] == "09-25"
    assert loaded.payload["job"]["status"] == "success"
    assert loaded.payload["job"]["progress"]["current"] == 2
    assert loaded.payload["job"]["progress"]["current_step"] == "normalize:hot_topics"
    assert loaded.payload["job"]["progress"]["percent"] == 100.0

    asyncio.run(engine.dispose())


def test_ohlcv_crawl_handler_accepts_profile_only_and_allows_full_crawl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OHLCV 抓取 handler 应允许仅通过 Profile 提交且支持留空上限。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    async def _fake_resolve_profile_config_path(self, profile_id: str):
        calls["profile_id"] = profile_id
        return tmp_path / "config" / "ohlcv.yaml"

    class _FakeMarketService:
        async def crawl_ohlcv(self, **kwargs):
            calls.update(kwargs)
            return ServiceResult(
                status="ok",
                payload={"config_path": str(kwargs["config_path"]), "result": "ohlcv done"},
                message="ohlcv done",
            )

    monkeypatch.setattr(job_runner_module.ConfigProfileService, "resolve_profile_config_path", _fake_resolve_profile_config_path, raising=False)
    monkeypatch.setattr(job_runner_module, "MarketService", _FakeMarketService)

    runner, _, engine, _ = _build_job_runner(tmp_path)
    handler = runner._build_default_handlers()["ohlcv-crawl"]
    result = asyncio.run(
        handler(
            {
                "profile_id": "default",
                "mode": "incremental",
                "symbols": ["000001.SZ", "000300.SH"],
                "start_date": "2026-04-01",
                "end_date": "2026-04-28",
            }
        )
    )

    assert result.status == "ok"
    assert calls["profile_id"] == "default"
    assert calls["config_path"] == tmp_path / "config" / "ohlcv.yaml"
    assert calls["mode"] == "incremental"
    assert calls["symbols"] == ["000001.SZ", "000300.SH"]
    assert calls["limit"] is None
    asyncio.run(engine.dispose())


def test_run_after_close_handler_accepts_profile_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """盘后运行 handler 应允许仅通过 Profile 提交。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    class _FakeRunService:
        def __init__(self, manager):
            self.manager = manager

        async def run_after_close(self, **kwargs):
            calls.update(kwargs)
            return ServiceResult(
                status="ok",
                payload={"html_path": str(tmp_path / "evaluation.html"), "result": "after close done"},
                message="after close done",
            )

    def _fake_build_manager(self, *, config_path):
        calls["config_path"] = config_path
        return object(), tmp_path

    monkeypatch.setattr(job_runner_module, "RunService", _FakeRunService)
    monkeypatch.setattr(job_runner_module.JobRunner, "_build_manager", _fake_build_manager, raising=False)

    runner, _, engine, ServiceResult = _build_job_runner(tmp_path)
    handler = runner._build_default_handlers()["run-after-close"]
    result = asyncio.run(
        handler(
            {
                "profile_id": "default",
                "as_of_date": "2026-05-16",
                "force": True,
                "export_html": True,
            }
        )
    )

    assert result.status == "ok"
    assert calls["config_path"] == "config/app.yaml"
    assert calls["as_of_date"].isoformat() == "2026-05-16"
    assert calls["force"] is True
    assert calls["export_html"] is True
    asyncio.run(engine.dispose())


def test_snapshot_build_handler_accepts_profile_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """快照构建 handler 应允许 benchmark_symbol 由配置回填。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    class _FakeSnapshotService:
        async def build_snapshot(self, **kwargs):
            calls.update(kwargs)
            return ServiceResult(
                status="ok",
                payload={"snapshot_path": str(tmp_path / "snapshot.json"), "result": "snapshot done"},
                message="snapshot done",
            )

    monkeypatch.setattr(job_runner_module, "SnapshotService", lambda: _FakeSnapshotService())

    runner, _, engine, ServiceResult = _build_job_runner(tmp_path)
    handler = runner._build_default_handlers()["snapshot-build"]
    result = asyncio.run(
        handler(
            {
                "profile_id": "default",
                "date": "2026-05-16",
                "slot": "17-30",
                "snapshot_type": "all",
            }
        )
    )

    assert result.status == "ok"
    assert calls["config_path"] == "config/app.yaml"
    assert calls["benchmark_symbol"] is None
    assert calls["profile_id"] == "default"
    assert calls["date"] == "2026-05-16"
    asyncio.run(engine.dispose())


def test_snapshot_build_handler_keeps_config_path_only_without_profile_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """仅传 config_path 时，handler 不应擅自注入默认 profile_id。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    class _FakeSnapshotService:
        async def build_snapshot(self, **kwargs):
            calls.update(kwargs)
            return ServiceResult(
                status="ok",
                payload={"snapshot_path": str(tmp_path / "snapshot.json"), "result": "snapshot done"},
                message="snapshot done",
            )

    monkeypatch.setattr(job_runner_module, "SnapshotService", lambda: _FakeSnapshotService())

    runner, _, engine, _ = _build_job_runner(tmp_path)
    handler = runner._build_default_handlers()["snapshot-build"]
    result = asyncio.run(
        handler(
            {
                "config_path": "config/app.yaml",
                "date": "2026-05-16",
                "slot": "17-30",
                "snapshot_type": "all",
            }
        )
    )

    assert result.status == "ok"
    assert calls["config_path"] == "config/app.yaml"
    assert calls["profile_id"] is None
    assert calls["date"] == "2026-05-16"
    asyncio.run(engine.dispose())


def test_submit_ohlcv_crawl_writes_progress_to_job_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ohlcv-crawl 执行时应把 symbol 级进度写回 Job 记录。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    class _FakeMarketService:
        async def crawl_ohlcv(self, **kwargs):
            calls.update(kwargs)
            progress_callback = kwargs.get("progress_callback")
            if progress_callback is not None:
                progress_callback(
                    {
                        "job_type": "ohlcv-crawl",
                        "stage": "crawl",
                        "current": 1,
                        "total": 2,
                        "percent": 50.0,
                        "remaining": 1,
                        "current_step": "crawl:000001.SZ",
                        "current_fetcher": "000001.SZ",
                        "status": "running",
                    }
                )
                progress_callback(
                    {
                        "job_type": "ohlcv-crawl",
                        "stage": "crawl",
                        "current": 2,
                        "total": 2,
                        "percent": 100.0,
                        "remaining": 0,
                        "current_step": "crawl:000300.SH",
                        "current_fetcher": "000300.SH",
                        "status": "success",
                    }
                )
            return ServiceResult(status="ok", payload={"results": {"000001.SZ": 1, "000300.SH": 1}}, message="ohlcv done")

    monkeypatch.setattr(job_runner_module, "MarketService", lambda: _FakeMarketService())

    runner, job_service, engine, _ = _build_job_runner(tmp_path)
    submitted = asyncio.run(
        runner.submit_job(
            job_type="ohlcv-crawl",
            params={
                "config_path": "config/app.yaml",
                "symbols": ["000001.SZ", "000300.SH"],
                "mode": "full",
                "start_date": "2026-05-01",
                "end_date": "2026-05-02",
            },
            created_by="web",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))

    assert submitted.status == "ok"
    assert calls["symbols"] == ["000001.SZ", "000300.SH"]
    assert loaded.payload["job"]["progress"]["current"] == 2
    assert loaded.payload["job"]["progress"]["current_step"] == "crawl:000300.SH"
    assert loaded.payload["job"]["progress"]["percent"] == 100.0
    asyncio.run(engine.dispose())


def test_submit_snapshot_build_writes_progress_to_job_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """snapshot-build 执行时应把日期 x 快照类型进度写回 Job 记录。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    class _FakeSnapshotService:
        async def build_snapshot(self, **kwargs):
            calls.update(kwargs)
            progress_callback = kwargs.get("progress_callback")
            if progress_callback is not None:
                progress_callback(
                    {
                        "job_type": "snapshot-build",
                        "stage": "snapshot",
                        "current": 1,
                        "total": 4,
                        "percent": 25.0,
                        "remaining": 3,
                        "current_step": "snapshot:hot_topics",
                        "current_trade_date": "2026-05-01",
                        "current_dataset": "hot_topics",
                        "status": "running",
                    }
                )
                progress_callback(
                    {
                        "job_type": "snapshot-build",
                        "stage": "snapshot",
                        "current": 4,
                        "total": 4,
                        "percent": 100.0,
                        "remaining": 0,
                        "current_step": "snapshot:strong_symbols",
                        "current_trade_date": "2026-05-02",
                        "current_dataset": "strong_symbols",
                        "status": "success",
                    }
                )
            return ServiceResult(status="ok", payload={"snapshot_paths": [str(tmp_path / "snapshot.json")]}, message="snapshot done")

    monkeypatch.setattr(job_runner_module, "SnapshotService", lambda: _FakeSnapshotService())

    runner, job_service, engine, _ = _build_job_runner(tmp_path)
    submitted = asyncio.run(
        runner.submit_job(
            job_type="snapshot-build",
            params={
                "config_path": "config/app.yaml",
                "benchmark_symbol": "000300.SH",
                "start_date": "2026-05-01",
                "end_date": "2026-05-02",
                "slot": "17-30",
                "snapshot_type": "all",
            },
            created_by="web",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))

    assert submitted.status == "ok"
    assert calls["start_date"] == "2026-05-01"
    assert calls["end_date"] == "2026-05-02"
    assert loaded.payload["job"]["progress"]["current"] == 4
    assert loaded.payload["job"]["progress"]["current_step"] == "snapshot:strong_symbols"
    assert loaded.payload["job"]["progress"]["percent"] == 100.0
    asyncio.run(engine.dispose())


def test_submit_pipeline_run_writes_progress_to_job_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """pipeline-run 执行时应把步骤与文章进度写回 Job 记录。"""
    from src.services import job_runner as job_runner_module

    calls: dict[str, Any] = {}

    class _FakePipelineService:
        async def run_pipeline(self, **kwargs):
            calls.update(kwargs)
            progress_callback = kwargs.get("progress_callback")
            if progress_callback is not None:
                progress_callback(
                    {
                        "job_type": "pipeline-run",
                        "stage": "crawl",
                        "current": 1,
                        "total": 3,
                        "percent": 33.33,
                        "remaining": 2,
                        "current_step": "crawl",
                        "status": "running",
                    }
                )
                progress_callback(
                    {
                        "job_type": "pipeline-run",
                        "stage": "process",
                        "current": 3,
                        "total": 3,
                        "percent": 100.0,
                        "remaining": 0,
                        "current_step": "process:article-003",
                        "current_dataset": "article_metadata_extracted",
                        "status": "success",
                    }
                )
            return ServiceResult(status="ok", payload={"result": "pipeline ok"}, message="pipeline done")

    runner, job_service, engine, _ = _build_job_runner(tmp_path)
    runner._pipeline_service_factory = lambda: _FakePipelineService()  # noqa: SLF001
    submitted = asyncio.run(
        runner.submit_job(
            job_type="pipeline-run",
            params={"config_path": "config/app.yaml", "max_articles": 10, "retry_failed": True},
            created_by="web",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))

    assert submitted.status == "ok"
    assert calls["retry_failed"] is True
    assert loaded.payload["job"]["progress"]["current"] == 3
    assert loaded.payload["job"]["progress"]["current_step"] == "process:article-003"
    assert loaded.payload["job"]["progress"]["percent"] == 100.0
    asyncio.run(engine.dispose())


def test_submit_backtest_jobs_write_progress_to_job_record(tmp_path: Path) -> None:
    """backtest-run 与 rule-pool-backtest 执行时应把日期级进度写回 Job 记录。"""
    fake_backtest_service = _FakeBacktestService()
    runner, job_service, engine, _ = _build_job_runner(
        tmp_path,
        backtest_service_factory=lambda: fake_backtest_service,
    )

    backtest_submitted = asyncio.run(
        runner.submit_job(
            job_type="backtest-run",
            params={
                "config_path": "config/app.yaml",
                "trader_id": "trader-a",
                "date_from": "2026-04-01",
                "date_to": "2026-04-02",
                "mode": "full",
                "use_snapshot_only": True,
                "scoring_profile": "stage5",
            },
            created_by="web",
        )
    )
    backtest_job_id = backtest_submitted.payload["execution"]["job"]["id"]
    backtest_loaded = asyncio.run(job_service.get_job(backtest_job_id))

    rule_pool_submitted = asyncio.run(
        runner.submit_job(
            job_type="rule-pool-backtest",
            params={
                "config_path": "config/app.yaml",
                "start_date": "2026-04-01",
                "end_date": "2026-04-02",
                "min_confidence": 0.6,
            },
            created_by="web",
            confirmed=True,
        )
    )
    rule_pool_job_id = rule_pool_submitted.payload["execution"]["job"]["id"]
    rule_pool_loaded = asyncio.run(job_service.get_job(rule_pool_job_id))

    assert backtest_submitted.status == "ok"
    assert backtest_loaded.payload["job"]["progress"]["current"] == 2
    assert backtest_loaded.payload["job"]["progress"]["current_step"] == "backtest:2026-04-02"
    assert backtest_loaded.payload["job"]["progress"]["percent"] == 100.0
    assert rule_pool_submitted.status == "ok"
    assert rule_pool_loaded.payload["job"]["progress"]["current"] == 2
    assert rule_pool_loaded.payload["job"]["progress"]["current_step"] == "rule-001:2026-04-02"
    assert rule_pool_loaded.payload["job"]["progress"]["percent"] == 100.0
    asyncio.run(engine.dispose())


def test_submit_backup_data_executes_default_handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """backup-data 应走默认 handler 并产出备份结果。"""

    from src.services import job_runner as job_runner_module

    class _FakeOpsRecoveryService:
        async def create_backup(
            self,
            *,
            profile_id: str,
            include_processed: bool = True,
            backup_dir: str | Path | None = None,
            backup_dir_id: str | None = None,
        ) -> Any:
            return job_runner_module.ServiceResult(
                status="ok",
                message="project backup created",
                payload={
                    "backup_dir": str(backup_dir or tmp_path / "data" / "backups" / "20260521-120000"),
                    "tables": ["jobs", "artifacts"],
                    "row_counts": {"jobs": 1, "artifacts": 2},
                    "processed_copied": include_processed,
                    "artifacts_copied": True,
                    "profile_id": profile_id,
                    "include_processed": include_processed,
                    "backup_item": {
                        "backup_id": "20260521-120000",
                        "path": str(backup_dir or tmp_path / "data" / "backups" / "20260521-120000"),
                        "name": "20260521-120000",
                    },
                },
            )

    monkeypatch.setattr(job_runner_module, "OpsRecoveryService", _FakeOpsRecoveryService)
    runner, job_service, engine, _ = _build_job_runner(tmp_path)

    class _FakeConfigProfileService:
        async def capture_profile_snapshot(
            self,
            profile_id: str,
            *,
            job_id: str | None = None,
            source: str = "job",
            config_path: str | None = None,
        ) -> Any:
            del job_id, source, config_path
            return job_runner_module.ServiceResult(
                status="ok",
                message="profile snapshot captured",
                payload={
                    "profile_id": profile_id,
                    "profile_snapshot_id": "profile-snapshot-001",
                    "snapshot_path": str(tmp_path / "profile-snapshot.json"),
                },
            )

    job_service._config_profile_service = _FakeConfigProfileService()  # noqa: SLF001
    created = asyncio.run(
        job_service.create_job(
            job_type="backup-data",
            params={
                "profile_id": "profile-001",
                "base_dir": "trade-strategy-ai",
                "backup_dir_id": "default",
                "include_processed": True,
            },
            created_by="web",
            confirmed=True,
        )
    )
    job_id = created.payload["job"]["id"]
    executed = asyncio.run(runner.execute_job(job_id=job_id))
    loaded = asyncio.run(job_service.get_job(job_id))

    assert executed.status == "ok"
    assert executed.payload["job"]["status"] == "success"
    assert loaded.payload["job"]["status"] == "success"
    assert loaded.payload["job"]["result"]["payload"]["profile_id"] == "profile-001"
    assert loaded.payload["job"]["result"]["payload"]["include_processed"] is True
    assert loaded.payload["job"]["result"]["payload"]["backup_item"]["backup_id"] == "20260521-120000"
    asyncio.run(engine.dispose())


def test_submit_restore_data_executes_default_handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """restore-data 应走默认 handler 并产出恢复结果。"""

    from src.services import job_runner as job_runner_module

    class _FakeOpsRecoveryService:
        async def restore_backup(
            self,
            *,
            profile_id: str,
            backup_id: str | None = None,
            backup_path: str | Path | None = None,
            include_processed: bool = True,
            confirmed: bool = False,
        ) -> Any:
            return job_runner_module.ServiceResult(
                status="ok",
                message="project backup restored",
                payload={
                    "backup_dir": str(backup_path or tmp_path / "data" / "backups" / (backup_id or "20260521-130000")),
                    "tables": ["jobs", "artifacts"],
                    "row_counts": {"jobs": 1, "artifacts": 2},
                    "processed_restored": include_processed,
                    "artifacts_restored": True,
                    "profile_id": profile_id,
                    "include_processed": include_processed,
                    "confirmed": confirmed,
                    "backup_item": {
                        "backup_id": backup_id or "20260521-130000",
                        "path": str(backup_path or tmp_path / "data" / "backups" / (backup_id or "20260521-130000")),
                        "name": backup_id or "20260521-130000",
                    },
                },
            )

    monkeypatch.setattr(job_runner_module, "OpsRecoveryService", _FakeOpsRecoveryService)
    runner, job_service, engine, _ = _build_job_runner(tmp_path)

    class _FakeConfigProfileService:
        async def capture_profile_snapshot(
            self,
            profile_id: str,
            *,
            job_id: str | None = None,
            source: str = "job",
            config_path: str | None = None,
        ) -> Any:
            del job_id, source, config_path
            return job_runner_module.ServiceResult(
                status="ok",
                message="profile snapshot captured",
                payload={
                    "profile_id": profile_id,
                    "profile_snapshot_id": "profile-snapshot-002",
                    "snapshot_path": str(tmp_path / "profile-snapshot.json"),
                },
            )

    job_service._config_profile_service = _FakeConfigProfileService()  # noqa: SLF001
    created = asyncio.run(
        job_service.create_job(
            job_type="restore-data",
            params={
                "profile_id": "profile-001",
                "base_dir": "trade-strategy-ai",
                "backup_id": "20260521-130000",
                "backup_dir": str(tmp_path / "data" / "backups" / "20260521-130000"),
                "include_processed": True,
                "force": True,
            },
            created_by="web",
            confirmed=True,
        )
    )
    job_id = created.payload["job"]["id"]
    executed = asyncio.run(runner.execute_job(job_id=job_id))
    loaded = asyncio.run(job_service.get_job(job_id))

    assert executed.status == "ok"
    assert executed.payload["job"]["status"] == "success"
    assert loaded.payload["job"]["status"] == "success"
    assert loaded.payload["job"]["result"]["payload"]["profile_id"] == "profile-001"
    assert loaded.payload["job"]["result"]["payload"]["include_processed"] is True
    assert loaded.payload["job"]["result"]["payload"]["backup_item"]["backup_id"] == "20260521-130000"
    asyncio.run(engine.dispose())


def test_submit_strategy_build_executes_with_default_handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """strategy-build 应走默认 handler 并可通过 Web 提交执行。"""

    from src.services import job_runner as job_runner_module

    class _FakeStrategyService:
        async def build_strategy_version(
            self,
            *,
            config_path: str | Path | None = None,
            profile_id: str | None = None,
            trader_id: str,
            strategy_date: str,
            force: bool = False,
            regime_selection: dict | None = None,
            snapshot_id: str | None = None,
            market_regime_version: str | None = None,
            source_feature_version: str | None = None,
            applicability_profile_version: str | None = None,
            selected_by: str | None = None,
        ) -> Any:
            del force
            return job_runner_module.ServiceResult(
                status="ok",
                payload={
                    "config_path": str(config_path) if config_path is not None else None,
                    "profile_id": profile_id,
                    "trader_id": trader_id,
                    "strategy_date": strategy_date,
                    "regime_selection": regime_selection
                    or {
                        "snapshot_id": snapshot_id,
                        "market_regime_version": market_regime_version,
                        "source_feature_version": source_feature_version,
                        "applicability_profile_version": applicability_profile_version,
                        "selected_by": selected_by,
                    },
                    "strategy_version_path": str(tmp_path / "strategy-version.json"),
                },
                message="strategy version build completed",
            )

    monkeypatch.setattr(job_runner_module, "StrategyService", _FakeStrategyService)
    runner, job_service, engine, _ = _build_job_runner(tmp_path)

    class _FakeConfigProfileService:
        async def capture_profile_snapshot(
            self,
            profile_id: str,
            *,
            job_id: str | None = None,
            source: str = "job",
            config_path: str | None = None,
        ) -> Any:
            del job_id, source, config_path
            return job_runner_module.ServiceResult(
                status="ok",
                message="profile snapshot captured",
                payload={
                    "profile_id": profile_id,
                    "profile_snapshot_id": "profile-snapshot-001",
                    "snapshot_path": str(tmp_path / "profile-snapshot.json"),
                },
            )

    job_service._config_profile_service = _FakeConfigProfileService()  # noqa: SLF001
    submitted = asyncio.run(
        runner.submit_job(
            job_type="strategy-build",
            params={
                "profile_id": "default",
                "trader_id": "trader-001",
                "strategy_date": "2026-05-16",
                "force": False,
                "snapshot_id": "snap-1",
                "market_regime_version": "market-regime-v3",
                "source_feature_version": "market-regime-features-v3",
                "applicability_profile_version": "rule-applicability-v1",
                "selected_by": "web",
            },
            created_by="web",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))

    assert submitted.status == "ok"
    assert submitted.payload["execution"]["job"]["status"] == "success"
    assert loaded.payload["job"]["status"] == "success"
    assert loaded.payload["job"]["result"]["payload"]["trader_id"] == "trader-001"
    assert loaded.payload["job"]["result"]["payload"]["strategy_date"] == "2026-05-16"
    assert loaded.payload["job"]["result"]["payload"]["profile_id"] == "default"
    assert loaded.payload["job"]["result"]["payload"]["regime_selection"]["snapshot_id"] == "snap-1"
    assert loaded.payload["job"]["result"]["payload"]["regime_selection"]["selected_by"] == "web"
    asyncio.run(engine.dispose())


def test_submit_candidate_review_binds_review_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """candidate-review 应通过默认 handler 执行并绑定审核产物。"""

    from src.services import job_runner as job_runner_module

    class _FakeOptimizeService:
        async def review_candidate(
            self,
            *,
            candidate_version_id: str,
            decision: str,
            reviewed_by: str = "web",
            force: bool = False,
        ) -> Any:
            return job_runner_module.ServiceResult(
                status="ok",
                message="candidate reviewed",
                payload={
                    "candidate_version_id": candidate_version_id,
                    "decision": decision,
                    "review_status": "released" if decision == "approve" else "draft",
                    "reviewed_by": reviewed_by,
                    "force": force,
                    "candidate": {
                        "version_id": candidate_version_id,
                        "status": "released" if decision == "approve" else "draft",
                    },
                    "report": "# Candidate Review Report\n",
                    "audit_log": {
                        "candidate_version_id": candidate_version_id,
                        "decision": decision,
                        "reviewed_by": reviewed_by,
                        "force": force,
                        "review_status": "released" if decision == "approve" else "draft",
                    },
                },
            )

    monkeypatch.setattr(job_runner_module, "OptimizeService", _FakeOptimizeService)
    runner, job_service, engine, _ = _build_job_runner(tmp_path)
    created = asyncio.run(
        job_service.create_job(
            job_type="candidate-review",
            params={
                "candidate_version_id": "candidate-001",
                "decision": "approve",
                "reviewed_by": "web",
                "force": True,
            },
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]
    executed = asyncio.run(runner.execute_job(job_id=job_id))
    loaded = asyncio.run(job_service.get_job(job_id))
    artifact_kinds = [item["kind"] for item in loaded.payload["job"]["artifacts"]]

    assert executed.status == "ok"
    assert loaded.payload["job"]["status"] == "success"
    assert "review-report-markdown" in artifact_kinds
    assert "audit-log-json" in artifact_kinds
    assert (tmp_path / "jobs" / job_id / "candidate_review_report.md").exists()
    assert (tmp_path / "jobs" / job_id / "candidate_review_audit.json").exists()
    asyncio.run(engine.dispose())


def test_submit_backtest_run_binds_report_and_csv_artifacts(tmp_path: Path) -> None:
    """backtest-run 应通过默认 handler 执行并绑定报告与 CSV 产物。"""
    fake_backtest_service = _FakeBacktestService()
    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        backtest_service_factory=lambda: fake_backtest_service,
    )
    submitted = asyncio.run(
        runner.submit_job(
            job_type="backtest-run",
            params={
                "trader_id": "trader_a",
                "date_from": "2026-04-01",
                "date_to": "2026-04-03",
                "strategy_version_id": "sv-001",
                "symbols": ["000001.SZ"],
                "mode": "full",
                "config_path": "config/app.yaml",
                "use_snapshot_only": True,
                "scoring_profile": "stage5",
            },
            created_by="web",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))
    artifact_kinds = [item["kind"] for item in loaded.payload["job"]["artifacts"]]
    result_payload = json.loads((tmp_path / "jobs" / str(job_id) / "result.json").read_text(encoding="utf-8"))

    assert submitted.status == "ok"
    assert submitted.payload["execution"]["job"]["status"] == "success"
    assert loaded.payload["job"]["status"] == "success"
    assert "report-markdown" in artifact_kinds
    assert "records-csv" in artifact_kinds
    assert result_payload["result"]["payload"]["fingerprint"] == "f" * 64
    assert result_payload["result"]["payload"]["request"]["symbols"] == ["000001.SZ"]
    assert (tmp_path / "jobs" / job_id / "backtest_report.md").exists()
    assert (tmp_path / "jobs" / job_id / "backtest_records.csv").exists()
    asyncio.run(engine.dispose())


def test_submit_rule_pool_backtest_binds_regime_artifacts(tmp_path: Path) -> None:
    """rule-pool-backtest 应通过默认 handler 执行并绑定 regime breakdown。"""
    fake_backtest_service = _FakeBacktestService()
    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        backtest_service_factory=lambda: fake_backtest_service,
    )
    submitted = asyncio.run(
        runner.submit_job(
            job_type="rule-pool-backtest",
            params={
                "rule_id": "rule-001",
                "start_date": "2026-04-01",
                "end_date": "2026-04-03",
                "min_confidence": 0.6,
                "market_regime_version": "market-regime-v3",
                "config_path": "config/app.yaml",
            },
            created_by="web",
            confirmed=True,
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))
    artifact_kinds = [item["kind"] for item in loaded.payload["job"]["artifacts"]]
    result_payload = json.loads((tmp_path / "jobs" / str(job_id) / "result.json").read_text(encoding="utf-8"))

    assert submitted.status == "ok"
    assert submitted.payload["execution"]["job"]["status"] == "success"
    assert loaded.payload["job"]["status"] == "success"
    assert "report-markdown" in artifact_kinds
    assert "records-csv" in artifact_kinds
    assert result_payload["result"]["payload"]["request"]["market_regime_version"] == "market-regime-v3"
    assert result_payload["result"]["payload"]["result"]["regime_version"] == "market-regime-v3"
    assert result_payload["result"]["payload"]["result"]["regime_metrics"][0]["regime_label"] == "trend_up"
    assert result_payload["result"]["payload"]["result"]["rule_regime_metrics"]["rule-001"][0]["regime_label"] == "trend_up"
    assert (tmp_path / "jobs" / job_id / "backtest_report.md").exists()
    assert (tmp_path / "jobs" / job_id / "backtest_records.csv").exists()
    assert fake_backtest_service.rule_pool_calls[0]["market_regime_version"] == "market-regime-v3"
    asyncio.run(engine.dispose())


def test_submit_backtest_validate_rules_binds_validation_report(tmp_path: Path) -> None:
    """backtest-validate-rules 应绑定规则验真报告。"""
    fake_backtest_service = _FakeBacktestService()
    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        backtest_service_factory=lambda: fake_backtest_service,
    )
    submitted = asyncio.run(
        runner.submit_job(
            job_type="backtest-validate-rules",
            params={
                "trader_id": "trader_a",
                "date_from": "2026-04-01",
                "date_to": "2026-04-03",
                "strategy_version_id": "sv-001",
                "symbols": ["000001.SZ"],
                "config_path": "config/app.yaml",
                "use_snapshot_only": True,
                "scoring_profile": "stage5",
            },
            created_by="web",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))
    artifact_kinds = [item["kind"] for item in loaded.payload["job"]["artifacts"]]
    result_payload = json.loads((tmp_path / "jobs" / str(job_id) / "result.json").read_text(encoding="utf-8"))

    assert submitted.status == "ok"
    assert "validation-report-markdown" in artifact_kinds
    assert result_payload["result"]["payload"]["report"].startswith("# Rule Validation Report")
    assert (tmp_path / "jobs" / job_id / "backtest_validation_report.md").exists()
    asyncio.run(engine.dispose())


def test_submit_market_state_job_binds_result_artifact(tmp_path: Path) -> None:
    """Market state job 应能绑定结构化产物引用。"""

    async def _handler(params: dict[str, Any]) -> Any:
        artifact_path = tmp_path / "market_state.json"
        artifact_path.write_text("{}", encoding="utf-8")
        return ServiceResult(
            status="ok",
            payload={
                "config_path": params.get("config_path", "config/app.yaml"),
                "market_state_path": str(artifact_path),
                "market_state": {"state": "bull"},
            },
            message="market state done",
        )

    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        handlers={"market-state-build": _handler},
    )
    submitted = asyncio.run(
        runner.submit_job(
            job_type="market-state-build",
            params={"config_path": "config/app.yaml", "benchmark_symbol": "000300.SH", "as_of": "2026-05-16"},
            created_by="web",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))

    assert submitted.status == "ok"
    assert loaded.payload["job"]["status"] == "success"
    assert loaded.payload["job"]["artifacts"][0]["kind"] == "result-json"
    assert any(item["kind"] == "market-state-json" for item in loaded.payload["job"]["artifacts"])
    asyncio.run(engine.dispose())


def test_submit_snapshot_job_binds_summary_and_quality_artifacts(tmp_path: Path) -> None:
    """结构化 snapshot job 应绑定摘要与质量报告产物。"""

    async def _handler(params: dict[str, Any]) -> Any:
        del params
        snapshot_path = tmp_path / "snapshot.json"
        summary_path = tmp_path / "snapshot.summary.json"
        quality_path = tmp_path / "snapshot.quality.json"
        snapshot_path.write_text("{}", encoding="utf-8")
        summary_path.write_text("{}", encoding="utf-8")
        quality_path.write_text("{}", encoding="utf-8")
        return ServiceResult(
            status="ok",
            payload={
                "snapshot_path": str(snapshot_path),
                "snapshot_summary_path": str(summary_path),
                "quality_report_path": str(quality_path),
            },
            message="snapshot done",
        )

    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        handlers={"snapshot-build": _handler},
    )
    created = asyncio.run(
        job_service.create_job(
            job_type="snapshot-build",
            params={"config_path": "config/app.yaml", "benchmark_symbol": "000300.SH", "trade_date": "2026-05-16"},
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]
    executed = asyncio.run(runner.execute_job(job_id=job_id))
    loaded = asyncio.run(job_service.get_job(job_id))
    result_payload = json.loads((tmp_path / "jobs" / str(job_id) / "result.json").read_text(encoding="utf-8"))

    kinds = [item["kind"] for item in loaded.payload["job"]["artifacts"]]
    assert executed.status == "ok"
    assert str(tmp_path) not in json.dumps(result_payload, ensure_ascii=False)
    assert result_payload["result"]["payload"]["snapshot_path"] == "snapshot.json"
    assert result_payload["result"]["payload"]["snapshot_summary_path"] == "snapshot.summary.json"
    assert result_payload["result"]["payload"]["quality_report_path"] == "snapshot.quality.json"
    assert "snapshot-json" in kinds
    assert "snapshot-summary-json" in kinds
    assert "snapshot-quality-json" in kinds
    asyncio.run(engine.dispose())


def test_submit_market_job_classifies_external_dependency_failure(tmp_path: Path) -> None:
    """市场 job 失败时应保留结构化错误分类。"""

    async def _handler(params: dict[str, Any]) -> Any:
        del params
        raise RuntimeError("provider unavailable: akshare offline")

    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        handlers={"ohlcv-crawl": _handler},
    )
    submitted = asyncio.run(
        runner.submit_job(
            job_type="ohlcv-crawl",
            params={"config_path": "config/app.yaml", "symbols": ["000001.SZ"]},
            created_by="web",
        )
    )
    job_id = submitted.payload["execution"]["job"]["id"]
    loaded = asyncio.run(job_service.get_job(job_id))

    assert submitted.status == "error"
    assert loaded.payload["job"]["status"] == "failed"
    assert loaded.payload["job"]["error"]["type"] == "external_dependency"
    assert loaded.payload["job"]["error"]["code"] == "provider_unavailable"
    asyncio.run(engine.dispose())


def test_run_pending_jobs_once_processes_pending_jobs(tmp_path: Path) -> None:
    """JobRunner 应能轮询并执行 pending Job。"""
    calls: dict[str, Any] = {}

    async def _pipeline_handler(params: dict[str, Any]) -> Any:
        calls["pipeline"] = dict(params)
        return await asyncio.sleep(
            0,
            result=ServiceResult(
                status="ok",
                payload={
                    "config_path": params.get("config_path", "config/app.yaml"),
                    "result": "pipeline ok",
                },
                message="pipeline done",
            ),
        )

    runner, job_service, engine, ServiceResult = _build_job_runner(
        tmp_path,
        handlers={
            "pipeline-run": _pipeline_handler,
        },
    )
    created = asyncio.run(
        job_service.create_job(
            job_type="pipeline-run",
            params={"config_path": "config/app.yaml", "retry_failed": True},
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]
    processed = asyncio.run(runner.run_pending_jobs_once(limit=1))
    loaded = asyncio.run(job_service.get_job(job_id))

    assert processed.payload["count"] == 1
    assert processed.payload["items"][0]["job_id"] == job_id
    assert loaded.payload["job"]["status"] == "success"
    assert calls["pipeline"]["retry_failed"] is True
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


def test_job_runner_pauses_running_job_on_request(tmp_path: Path) -> None:
    """JobRunner 收到 pause 请求后应在安全边界停止并保留 paused 状态。"""

    async def _handler(params: dict[str, Any]) -> Any:
        del params
        await asyncio.sleep(0.05)
        return ServiceResult(
            status="ok",
            payload={"result": "ok"},
            message="done",
        )

    runner, job_service, engine, _ = _build_job_runner(
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
        await asyncio.sleep(0.01)
        await job_service.pause_job(job_id=job_id, actor="web", reason="maintenance")
        result = await task
        assert result.status == "ok"
        assert result.message == "job paused"

    asyncio.run(_run())
    loaded = asyncio.run(job_service.get_job(job_id))
    assert loaded.payload["job"]["status"] == "paused"
    assert loaded.payload["job"]["runtime_state"]["paused"] is True
    asyncio.run(engine.dispose())


def test_job_runner_cancels_running_job_on_request(tmp_path: Path) -> None:
    """JobRunner 收到 cancel 请求后应在安全边界停止并标记 cancelled。"""

    async def _handler(params: dict[str, Any]) -> Any:
        del params
        await asyncio.sleep(0.05)
        return ServiceResult(
            status="ok",
            payload={"result": "ok"},
            message="done",
        )

    runner, job_service, engine, _ = _build_job_runner(
        tmp_path,
        handlers={"run-after-close": _handler},
    )
    created = asyncio.run(
        job_service.create_job(
            job_type="run-after-close",
            params={"config_path": "config/app.yaml"},
            created_by="web",
        )
    )
    job_id = created.payload["job"]["id"]

    async def _run() -> None:
        task = asyncio.create_task(runner.execute_job(job_id=job_id))
        await asyncio.sleep(0.01)
        await job_service.cancel_job(job_id=job_id, reason="stop now")
        result = await task
        assert result.status == "ok"
        assert result.message == "job cancelled"

    asyncio.run(_run())
    loaded = asyncio.run(job_service.get_job(job_id))
    assert loaded.payload["job"]["status"] == "cancelled"
    assert loaded.payload["job"]["error"]["type"] == "cancelled"
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


def test_job_runner_logs_handler_context(tmp_path: Path, caplog) -> None:
    """JobRunner 执行 handler 时应把 job 上下文注入日志。"""

    async def _handler(params: dict[str, Any]) -> ServiceResult:
        logging.getLogger("tests.job.handler").info("handler invoked")
        return ServiceResult(status="ok", payload={"profile_id": params.get("profile_id")}, message="done")

    runner, job_service, engine, _ = _build_job_runner(
        tmp_path,
        handlers={"run-pre-market": _handler},
    )

    with caplog.at_level(logging.INFO):
            submitted = asyncio.run(
                runner.submit_job(
                    job_type="run-pre-market",
                    params={"profile_id": "profile-a", "config_path": "config/app.yaml"},
                    created_by="web",
                    idempotency_key="job-context-001",
                )
            )

    job_id = submitted.payload["execution"]["job"]["id"]
    handler_records = [record for record in caplog.records if record.name == "tests.job.handler" and record.message == "handler invoked"]
    assert handler_records, "handler log should be captured"
    assert handler_records[-1].job_id == job_id
    assert handler_records[-1].profile_id == "profile-a"
    assert handler_records[-1].config_path == "config/app.yaml"
    asyncio.run(engine.dispose())
