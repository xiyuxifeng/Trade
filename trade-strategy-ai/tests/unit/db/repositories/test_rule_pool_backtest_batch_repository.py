from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.job import Job
from src.models.rule_pool_backtest_batch import RulePoolBacktestBatch, RulePoolBacktestBatchRun


def _build_session(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'rule_pool_batches.db'}")

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


def test_rule_pool_backtest_batch_repository_persists_run_and_batches(tmp_path: Path) -> None:
    from src.db.repositories.rule_pool_backtest_batch_repository import RulePoolBacktestBatchRepository

    session_scope, engine = _build_session(tmp_path)
    repo = RulePoolBacktestBatchRepository()

    async def _run() -> None:
        async with session_scope() as session:
            batch_run = RulePoolBacktestBatchRun(
                batch_run_id="batch-run-1",
                status="draft",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 6, 30),
                min_confidence=0.7,
                market_regime_version="market-regime-v3",
                profile_id="default",
                selected_rule_count=3,
                batch_size=2,
                created_by="operator",
                config_json={"source_surface": "/rules/backtests"},
                fingerprint="fp-1",
            )
            batches = [
                RulePoolBacktestBatch(
                    batch_id="batch-run-1-001",
                    batch_run_id="batch-run-1",
                    batch_index=1,
                    rule_ids_json=["rule-1", "rule-2"],
                    status="pending",
                ),
                RulePoolBacktestBatch(
                    batch_id="batch-run-1-002",
                    batch_run_id="batch-run-1",
                    batch_index=2,
                    rule_ids_json=["rule-3"],
                    status="pending",
                ),
            ]
            saved = await repo.create_batch_run(session, batch_run=batch_run, batches=batches)
            assert saved.batch_run_id == "batch-run-1"

        async with session_scope() as session:
            loaded = await repo.get_batch_run(session, "batch-run-1")
            assert loaded is not None
            assert len(loaded.batches) == 2
            assert loaded.batches[0].rule_ids_json == ["rule-1", "rule-2"]
            listed = await repo.list_batch_runs(session, limit=10, offset=0)
            assert [item.batch_run_id for item in listed] == ["batch-run-1"]

            updated_batch = await repo.update_batch_status(
                session,
                batch_run_id="batch-run-1",
                batch_index=1,
                status="completed",
                job_id="00000000-0000-0000-0000-000000000001",
                result_json={"summary": {"total_trades": 2}},
            )
            assert updated_batch is not None
            assert str(updated_batch.job_id) == "00000000-0000-0000-0000-000000000001"

    asyncio.run(_run())
    asyncio.run(engine.dispose())
