from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_regime_record import MarketRegimeRecord
from src.models.stage2_canonical import BacktestResult, BacktestRun, DatasetSnapshot, RuleFamily, RuleFamilyMembership, RuleVersion


@dataclass(frozen=True)
class RuleFamilyFact:
    rule_family_id: UUID
    canonical_fingerprint: str
    members: list[RuleVersion]


class BacktestRunRepository:
    async def get_rule_version(self, session: AsyncSession, rule_version_id: UUID) -> RuleVersion | None:
        return await session.get(RuleVersion, rule_version_id)

    async def get_rule_family_with_members(self, session: AsyncSession, rule_family_id: UUID) -> RuleFamilyFact | None:
        family = await session.get(RuleFamily, rule_family_id)
        if family is None:
            return None
        stmt = (
            select(RuleVersion)
            .join(RuleFamilyMembership, RuleFamilyMembership.rule_version_id == RuleVersion.rule_version_id)
            .where(RuleFamilyMembership.rule_family_id == rule_family_id)
            .order_by(RuleVersion.created_at.asc(), RuleVersion.version_no.asc(), RuleVersion.rule_version_id.asc())
        )
        members = list((await session.execute(stmt)).scalars().all())
        return RuleFamilyFact(
            rule_family_id=family.rule_family_id,
            canonical_fingerprint=family.canonical_fingerprint,
            members=members,
        )

    async def find_dataset_snapshot(
        self,
        session: AsyncSession,
        *,
        date_from: date,
        date_to: date,
        benchmark_symbol: str,
        universe: dict[str, Any],
    ) -> DatasetSnapshot | None:
        del universe
        stmt = (
            select(DatasetSnapshot)
            .where(DatasetSnapshot.date_from <= date_from)
            .where(DatasetSnapshot.date_to >= date_to)
            .where(DatasetSnapshot.date_to <= date_to)
            .where(DatasetSnapshot.benchmark_symbol == benchmark_symbol)
            .where(DatasetSnapshot.lifecycle_state == "ready")
            .order_by(DatasetSnapshot.date_to.desc(), DatasetSnapshot.frozen_at.desc().nullslast(), DatasetSnapshot.created_at.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def list_market_snapshots(
        self,
        session: AsyncSession,
        *,
        date_from: date,
        date_to: date,
        market: str = "CN",
    ) -> list[MarketSnapshot]:
        stmt = (
            select(MarketSnapshot)
            .where(MarketSnapshot.trade_date >= date_from)
            .where(MarketSnapshot.trade_date <= date_to)
            .where(MarketSnapshot.market == market)
            .order_by(MarketSnapshot.trade_date.asc(), MarketSnapshot.slot.asc(), MarketSnapshot.created_at.asc())
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_market_states_for_run(
        self,
        session: AsyncSession,
        *,
        date_from: date,
        date_to: date,
        market: str,
        definition_version: str | None,
        decision_times: dict[date, datetime],
        market_snapshot_ids: list[str] | None = None,
    ) -> list[MarketRegimeRecord]:
        stmt = (
            select(MarketRegimeRecord)
            .join(MarketSnapshot, MarketSnapshot.id == MarketRegimeRecord.market_snapshot_id)
            .where(MarketRegimeRecord.trade_date >= date_from)
            .where(MarketRegimeRecord.trade_date <= date_to)
            .where(MarketRegimeRecord.market == market)
            .where(MarketSnapshot.available_at <= MarketRegimeRecord.available_at)
        )
        if definition_version:
            stmt = stmt.where(MarketRegimeRecord.definition_version == definition_version)
        if market_snapshot_ids:
            parsed_ids = [UUID(item) for item in market_snapshot_ids]
            stmt = stmt.where(MarketRegimeRecord.market_snapshot_id.in_(parsed_ids))
        stmt = stmt.order_by(
            MarketRegimeRecord.trade_date.asc(),
            MarketRegimeRecord.available_at.desc(),
            MarketRegimeRecord.created_at.desc(),
        )
        candidates = list((await session.execute(stmt)).scalars().all())
        selected: dict[date, MarketRegimeRecord] = {}
        for candidate in candidates:
            decision_time = decision_times.get(candidate.trade_date)
            if decision_time is None or candidate.available_at is None:
                continue
            if candidate.available_at <= decision_time:
                selected.setdefault(candidate.trade_date, candidate)
        return list(selected.values())

    async def list_formal_samples_for_run(self, session: AsyncSession, *, run: BacktestRun) -> list[Any]:
        dataset = await session.get(DatasetSnapshot, run.dataset_snapshot_id)
        if dataset is None:
            return []
        storage_ref = dataset.storage_ref or {}
        samples = storage_ref.get("formal_samples")
        if not isinstance(samples, list):
            samples = (dataset.ohlcv_manifest or {}).get("formal_samples")
        if not isinstance(samples, list):
            return []
        normalized = []
        for item in samples:
            if not isinstance(item, dict):
                continue
            trade_date = item.get("trade_date")
            if isinstance(trade_date, str):
                trade_date = date.fromisoformat(trade_date)
            normalized.append(SimpleNamespace(**{**item, "trade_date": trade_date}))
        return normalized

    async def create_backtest_run(self, session: AsyncSession, payload: dict[str, Any]) -> BacktestRun:
        run = BacktestRun(**payload)
        session.add(run)
        await session.flush()
        return run

    async def get_backtest_run(self, session: AsyncSession, run_id: UUID) -> BacktestRun | None:
        return await session.get(BacktestRun, run_id)

    async def create_backtest_result(self, session: AsyncSession, payload: dict[str, Any]) -> BacktestResult:
        result = BacktestResult(**payload)
        session.add(result)
        await session.flush()
        return result

    async def get_backtest_result_by_run(self, session: AsyncSession, run_id: UUID) -> BacktestResult | None:
        return await session.scalar(select(BacktestResult).where(BacktestResult.run_id == run_id))

    async def find_reusable_backtest_result(
        self,
        session: AsyncSession,
        *,
        input_fingerprint: str,
        rule_family_fingerprint: str | None,
        rule_version_fingerprint: str | None,
        dataset_fingerprint: str,
        market_state_model_version: str | None,
        engine_version: str,
        decision_time_policy: str,
    ) -> BacktestResult | None:
        stmt = (
            select(BacktestResult)
            .join(BacktestRun, BacktestRun.run_id == BacktestResult.run_id)
            .where(BacktestResult.input_fingerprint == input_fingerprint)
            .where(BacktestRun.dataset_fingerprint == dataset_fingerprint)
            .where(BacktestRun.engine_version == engine_version)
            .where(BacktestRun.decision_time_policy == decision_time_policy)
            .order_by(BacktestResult.created_at.desc())
            .limit(1)
        )
        if rule_family_fingerprint:
            stmt = stmt.where(BacktestRun.rule_family_fingerprint == rule_family_fingerprint)
        if rule_version_fingerprint:
            stmt = stmt.where(BacktestRun.rule_version_fingerprint == rule_version_fingerprint)
        if market_state_model_version is None:
            stmt = stmt.where(BacktestRun.market_state_model_version.is_(None))
        else:
            stmt = stmt.where(BacktestRun.market_state_model_version == market_state_model_version)
        return await session.scalar(stmt)
