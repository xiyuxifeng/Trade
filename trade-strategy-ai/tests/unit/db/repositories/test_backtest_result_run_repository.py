from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.backtest_result_run import BacktestResultRun


def _build_backtest_run_session(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'backtest_runs.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
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

    return _session_scope, engine


def test_backtest_result_run_repository_upserts_and_lists(tmp_path: Path) -> None:
    from src.db.repositories import BacktestResultRunRepository

    session_scope, engine = _build_backtest_run_session(tmp_path)
    repo = BacktestResultRunRepository()

    async def _run() -> None:
        async with session_scope() as session:
            run = BacktestResultRun(
                result_run_id="run-1",
                source_job_id="job-1",
                job_type="backtest-run",
                request_trader_id="trader_a",
                strategy_version_id="sv-1",
                request_date_from=date(2026, 5, 1),
                request_date_to=date(2026, 5, 5),
                benchmark_symbol="000300.SH",
                regime_version="market-regime-v3",
                source_feature_version="market-regime-features-v3",
                mode="full",
                scoring_profile="stage5",
                result_version="1.0",
                status="success",
                quality_status="ok",
                total_days=5,
                total_trades=3,
                valid_trades=2,
                skipped_trades=1,
                win_rate=0.67,
                avg_return_pct=0.12,
                summary_json={"total_days": 5},
                regime_metrics_json=[{"regime_version": "market-regime-v3"}],
                rule_regime_metrics_json={"rule_a": {"score": 0.9}},
                fingerprint="fp-1",
                storage_ref={"source": "file"},
                artifact_ref={"artifact_type": "backtest-result-json"},
            )
            saved = await repo.upsert_run(session, run)
            assert saved.result_run_id == "run-1"

        async with session_scope() as session:
            loaded = await repo.get_by_source_job_id(session, "job-1")
            assert loaded is not None
            assert loaded.request_trader_id == "trader_a"
            assert loaded.summary_json["total_days"] == 5

            listed = await repo.list_runs(session, trader_id="trader_a", date_from=date(2026, 5, 1), date_to=date(2026, 5, 5))
            assert len(listed) == 1
            assert listed[0].result_run_id == "run-1"

            counted = await repo.count_runs(session, trader_id="trader_a", date_from=date(2026, 5, 1), date_to=date(2026, 5, 5))
            assert counted == 1

    asyncio.run(_run())
    asyncio.run(engine.dispose())
