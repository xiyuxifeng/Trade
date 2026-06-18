from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_data_snapshot import MarketSnapshot
from src.models.stage2_canonical import BacktestRun, DatasetSnapshot, RuleFamily, RuleFamilyMembership, RuleVersion


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
            .where(DatasetSnapshot.benchmark_symbol == benchmark_symbol)
            .where(DatasetSnapshot.lifecycle_state == "ready")
            .order_by(DatasetSnapshot.frozen_at.desc().nullslast(), DatasetSnapshot.created_at.desc())
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

    async def create_backtest_run(self, session: AsyncSession, payload: dict[str, Any]) -> BacktestRun:
        run = BacktestRun(**payload)
        session.add(run)
        await session.flush()
        return run

    async def get_backtest_run(self, session: AsyncSession, run_id: UUID) -> BacktestRun | None:
        return await session.get(BacktestRun, run_id)
