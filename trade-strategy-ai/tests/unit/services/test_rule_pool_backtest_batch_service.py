from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from uuid import UUID

from src.models.job import Job
from src.models.rule_pool_backtest_batch import RulePoolBacktestBatch, RulePoolBacktestBatchRun


def _build_session(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'rule_pool_batch_service.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Job.__table__.create)
            await conn.run_sync(RulePoolBacktestBatchRun.__table__.create)
            await conn.run_sync(RulePoolBacktestBatch.__table__.create)

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

    return _session_scope, engine


class _FakeServiceResult:
    def __init__(self, *, status: str, payload: dict, message: str = "ok") -> None:
        self.status = status
        self.payload = payload
        self.message = message


class _FakeJobService:
    def __init__(self) -> None:
        self.created_params: list[dict] = []
        self.jobs: dict[str, dict] = {}

    async def create_job(self, **kwargs):
        self.created_params.append(kwargs)
        job_id = f"00000000-0000-0000-0000-00000000000{len(self.created_params)}"
        self.jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "result": None,
            "progress": None,
            "artifacts": [],
        }
        return _FakeServiceResult(status="ok", payload={"job": self.jobs[job_id]})

    async def get_job(self, job_id):
        job = self.jobs.get(str(job_id))
        if job is None:
            return _FakeServiceResult(status="partial", message="not found", payload={})
        return _FakeServiceResult(status="ok", payload={"job": job})


def test_batch_service_creates_batches_and_starts_single_batch(tmp_path: Path) -> None:
    from src.services.rule_pool_backtest_batch_service import RulePoolBacktestBatchService

    session_scope, engine = _build_session(tmp_path)
    fake_job_service = _FakeJobService()
    service = RulePoolBacktestBatchService(session_scope_factory=session_scope, job_service=fake_job_service)

    async def _run() -> None:
        created = await service.create_batch_run(
            rule_ids=["rule-1", "rule-2", "rule-3"],
            batch_size=2,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            min_confidence=0.7,
            market_regime_version="market-regime-v3",
            profile_id="default",
            created_by="operator",
        )

        assert created["selected_rule_count"] == 3
        assert [batch["rule_ids"] for batch in created["batches"]] == [["rule-1", "rule-2"], ["rule-3"]]

        started = await service.start_batch(created["batch_run_id"], batch_index=1, actor="operator")
        assert started["batches"][0]["status"] == "running"
        assert fake_job_service.created_params[0]["job_type"] == "rule-pool-backtest"
        assert fake_job_service.created_params[0]["params"]["rule_ids"] == ["rule-1", "rule-2"]
        assert fake_job_service.created_params[0]["params"]["profile_id"] == "default"

    asyncio.run(_run())
    asyncio.run(engine.dispose())


def test_batch_service_merge_rejects_incomplete_or_failed_batches(tmp_path: Path) -> None:
    from src.services.rule_pool_backtest_batch_service import RulePoolBacktestBatchService

    session_scope, engine = _build_session(tmp_path)
    service = RulePoolBacktestBatchService(session_scope_factory=session_scope, job_service=_FakeJobService())

    async def _run() -> None:
        created = await service.create_batch_run(
            rule_ids=["rule-1", "rule-2"],
            batch_size=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            min_confidence=0.7,
            market_regime_version="market-regime-v3",
            profile_id="default",
            created_by="operator",
        )
        with pytest.raises(ValueError, match="completed"):
            await service.merge_batch_results(created["batch_run_id"])

    asyncio.run(_run())
    asyncio.run(engine.dispose())


def test_batch_service_merges_completed_batch_rule_results(tmp_path: Path) -> None:
    from src.services.rule_pool_backtest_batch_service import RulePoolBacktestBatchService

    session_scope, engine = _build_session(tmp_path)
    service = RulePoolBacktestBatchService(session_scope_factory=session_scope, job_service=_FakeJobService())

    async def _run() -> None:
        created = await service.create_batch_run(
            rule_ids=["rule-1", "rule-2"],
            batch_size=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            min_confidence=0.7,
            market_regime_version="market-regime-v3",
            profile_id="default",
            created_by="operator",
        )
        async with session_scope() as session:
            for index, rule_id in enumerate(["rule-1", "rule-2"], start=1):
                batch = await session.get(RulePoolBacktestBatch, f"{created['batch_run_id']}-{index:03d}")
                assert batch is not None
                batch.status = "completed"
                batch.job_id = UUID(f"00000000-0000-0000-0000-00000000000{index}")
                batch.result_json = {
                    "request": {
                        "start_date": "2026-01-01",
                        "end_date": "2026-06-30",
                        "min_confidence": 0.7,
                        "market_regime_version": "market-regime-v3",
                        "profile_id": "default",
                    },
                    "result": {
                        "summary": {"total_days": 2, "total_trades": 1, "valid_trades": 1, "skipped_trades": 0},
                        "records": [{"rule_id": rule_id, "return_pct": 0.01}],
                        "rule_regime_metrics": {rule_id: [{"regime_label": "强势", "sample_count": 1}]},
                    },
                }

        merged = await service.merge_batch_results(created["batch_run_id"])
        assert merged["status"] == "merged"
        assert merged["merged_result"]["summary"]["total_trades"] == 2
        assert [item["rule_id"] for item in merged["merged_result"]["rule_results"]] == ["rule-1", "rule-2"]
        assert merged["merged_result"]["rule_results"][0]["batch_index"] == 1

    asyncio.run(_run())
    asyncio.run(engine.dispose())


def test_batch_service_merges_job_service_result_payload_and_keeps_rule_provenance(tmp_path: Path) -> None:
    from src.services.rule_pool_backtest_batch_service import RulePoolBacktestBatchService

    session_scope, engine = _build_session(tmp_path)
    service = RulePoolBacktestBatchService(session_scope_factory=session_scope, job_service=_FakeJobService())

    async def _run() -> None:
        created = await service.create_batch_run(
            rule_ids=["rule-1", "rule-2", "rule-3"],
            batch_size=2,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
            min_confidence=0.7,
            market_regime_version="market-regime-v3",
            profile_id="default",
            created_by="operator",
        )
        async with session_scope() as session:
            for index, rule_ids in enumerate((["rule-1", "rule-2"], ["rule-3"]), start=1):
                batch = await session.get(RulePoolBacktestBatch, f"{created['batch_run_id']}-{index:03d}")
                assert batch is not None
                batch.status = "completed"
                batch.job_id = UUID(f"00000000-0000-0000-0000-00000000000{index}")
                batch.result_json = {
                    "status": "ok",
                    "message": "rule pool backtest completed",
                    "payload": {
                        "start_date": "2026-01-01",
                        "end_date": "2026-01-05",
                        "min_confidence": 0.7,
                        "market_regime_version": "market-regime-v3",
                        "profile_id": "default",
                        "rule_ids": rule_ids,
                        "summary": {"total_days": 0, "total_trades": 0, "valid_trades": 0, "skipped_trades": 0},
                        "result": {
                            "summary": {"total_days": 0, "total_trades": 0, "valid_trades": 0, "skipped_trades": 0},
                            "records": [],
                            "rule_regime_metrics": {},
                        },
                    },
                    "warnings": [],
                }

        merged = await service.merge_batch_results(created["batch_run_id"])

        assert merged["status"] == "merged"
        assert merged["merged_result"]["summary"]["total_trades"] == 0
        assert [item["rule_id"] for item in merged["merged_result"]["rule_results"]] == ["rule-1", "rule-2", "rule-3"]
        assert merged["merged_result"]["rule_results"][0]["batch_run_id"] == created["batch_run_id"]
        assert merged["merged_result"]["rule_results"][0]["job_id"] == "00000000-0000-0000-0000-000000000001"
        assert merged["merged_result"]["provenance"]["job_ids"] == [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        ]

    asyncio.run(_run())
    asyncio.run(engine.dispose())
