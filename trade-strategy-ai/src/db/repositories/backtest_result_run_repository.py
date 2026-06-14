from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.backtest_result_run import BacktestResultRun
from src.common.stage2_writer_routing import require_canonical_write


class BacktestResultRunRepository:
    """回测结果摘要仓储。"""

    async def upsert_run(self, session: AsyncSession, run: BacktestResultRun) -> BacktestResultRun:
        """按 result_run_id 写入或更新回测结果摘要。"""
        require_canonical_write("backtest_run", "BacktestResultRunRepository.upsert_run")
        existing = await session.scalar(select(BacktestResultRun).where(BacktestResultRun.result_run_id == run.result_run_id))
        if existing is None:
            session.add(run)
            await session.flush()
            return run

        for field in (
            "source_job_id",
            "job_type",
            "request_trader_id",
            "legacy_strategy_version_id",
            "strategy_version_id",
            "rule_version_id",
            "dataset_snapshot_id",
            "market_state_definition_version",
            "request_date_from",
            "request_date_to",
            "benchmark_symbol",
            "regime_version",
            "source_feature_version",
            "mode",
            "scoring_profile",
            "result_version",
            "status",
            "quality_status",
            "total_days",
            "total_trades",
            "valid_trades",
            "skipped_trades",
            "win_rate",
            "avg_return_pct",
            "summary_json",
            "regime_metrics_json",
            "rule_regime_metrics_json",
            "fingerprint",
            "storage_ref",
            "artifact_ref",
        ):
            setattr(existing, field, getattr(run, field))
        await session.flush()
        return existing

    async def get_by_run_id(self, session: AsyncSession, run_id: str) -> BacktestResultRun | None:
        """按 result_run_id 查询。"""
        return await session.scalar(select(BacktestResultRun).where(BacktestResultRun.result_run_id == run_id))

    async def get_by_source_job_id(self, session: AsyncSession, source_job_id: str) -> BacktestResultRun | None:
        """按 source_job_id 查询。"""
        return await session.scalar(select(BacktestResultRun).where(BacktestResultRun.source_job_id == source_job_id))

    async def list_runs(
        self,
        session: AsyncSession,
        *,
        trader_id: str | None = None,
        strategy_version_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        regime_version: str | None = None,
        source_feature_version: str | None = None,
        benchmark_symbol: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[BacktestResultRun]:
        """按条件查询回测结果摘要列表。"""
        stmt = select(BacktestResultRun)
        if trader_id:
            stmt = stmt.where(BacktestResultRun.request_trader_id == trader_id)
        if strategy_version_id:
            try:
                stmt = stmt.where(BacktestResultRun.strategy_version_id == UUID(strategy_version_id))
            except ValueError:
                stmt = stmt.where(BacktestResultRun.legacy_strategy_version_id == strategy_version_id)
        if date_from is not None:
            stmt = stmt.where(BacktestResultRun.request_date_from >= date_from)
        if date_to is not None:
            stmt = stmt.where(BacktestResultRun.request_date_to <= date_to)
        if regime_version:
            stmt = stmt.where(BacktestResultRun.regime_version == regime_version)
        if source_feature_version:
            stmt = stmt.where(BacktestResultRun.source_feature_version == source_feature_version)
        if benchmark_symbol:
            stmt = stmt.where(BacktestResultRun.benchmark_symbol == benchmark_symbol)
        stmt = stmt.order_by(BacktestResultRun.request_date_to.desc(), BacktestResultRun.request_date_from.desc(), BacktestResultRun.created_at.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def count_runs(
        self,
        session: AsyncSession,
        *,
        trader_id: str | None = None,
        strategy_version_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        regime_version: str | None = None,
        source_feature_version: str | None = None,
        benchmark_symbol: str | None = None,
    ) -> int:
        """统计满足条件的回测结果摘要数。"""
        stmt = select(func.count()).select_from(BacktestResultRun)
        if trader_id:
            stmt = stmt.where(BacktestResultRun.request_trader_id == trader_id)
        if strategy_version_id:
            try:
                stmt = stmt.where(BacktestResultRun.strategy_version_id == UUID(strategy_version_id))
            except ValueError:
                stmt = stmt.where(BacktestResultRun.legacy_strategy_version_id == strategy_version_id)
        if date_from is not None:
            stmt = stmt.where(BacktestResultRun.request_date_from >= date_from)
        if date_to is not None:
            stmt = stmt.where(BacktestResultRun.request_date_to <= date_to)
        if regime_version:
            stmt = stmt.where(BacktestResultRun.regime_version == regime_version)
        if source_feature_version:
            stmt = stmt.where(BacktestResultRun.source_feature_version == source_feature_version)
        if benchmark_symbol:
            stmt = stmt.where(BacktestResultRun.benchmark_symbol == benchmark_symbol)
        result = await session.scalar(stmt)
        return int(result or 0)
