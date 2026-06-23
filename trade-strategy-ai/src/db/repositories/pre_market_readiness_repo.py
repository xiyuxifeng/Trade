from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import FormalLifecycleState
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_regime_record import MarketRegimeRecord
from src.models.rule_applicability import RuleApplicabilityProfile
from src.models.stage2_canonical import AuthorProfileVersion, DatasetSnapshot, Strategy, StrategyRuleMembership, StrategyVersion


OHLCV_DATASET_TYPES = ("ohlcv_1d", "ohlcv_daily", "ohlcv_partial")


class PreMarketReadinessRepository:
    async def list_current_strategies(self, session: AsyncSession) -> list[Strategy]:
        result = await session.scalars(
            select(Strategy)
            .where(Strategy.current_published_version_id.is_not(None))
            .order_by(Strategy.updated_at.desc(), Strategy.created_at.desc())
        )
        return list(result.all())

    async def get_strategy_version(self, session: AsyncSession, strategy_version_id: UUID) -> StrategyVersion | None:
        return await session.get(StrategyVersion, strategy_version_id)

    async def list_strategy_rule_memberships(
        self,
        session: AsyncSession,
        *,
        strategy_version_id: UUID,
    ) -> list[StrategyRuleMembership]:
        result = await session.scalars(
            select(StrategyRuleMembership)
            .where(StrategyRuleMembership.strategy_version_id == strategy_version_id)
            .order_by(StrategyRuleMembership.membership_id.asc())
        )
        return list(result.all())

    async def get_latest_dataset_snapshot(
        self,
        session: AsyncSession,
        *,
        trade_date: date,
        available_at_before: datetime | None = None,
    ) -> DatasetSnapshot | None:
        stmt = select(DatasetSnapshot).where(
            DatasetSnapshot.trade_date.is_not(None),
            DatasetSnapshot.trade_date <= trade_date,
            DatasetSnapshot.market == "CN",
            DatasetSnapshot.dataset_type.in_(OHLCV_DATASET_TYPES),
        )
        if available_at_before is not None:
            stmt = stmt.where(
                DatasetSnapshot.available_at.is_not(None),
                DatasetSnapshot.available_at <= available_at_before,
            )
        stmt = stmt.order_by(DatasetSnapshot.trade_date.desc(), DatasetSnapshot.available_at.desc(), DatasetSnapshot.created_at.desc()).limit(1)
        return await session.scalar(stmt)

    async def get_market_snapshot_for_trade_date_and_slot(
        self,
        session: AsyncSession,
        *,
        trade_date: date,
        slot: str,
        available_at_before: datetime | None = None,
    ) -> MarketSnapshot | None:
        stmt = select(MarketSnapshot).where(MarketSnapshot.trade_date == trade_date, MarketSnapshot.slot == slot)
        if available_at_before is not None:
            stmt = stmt.where(
                MarketSnapshot.available_at.is_not(None),
                MarketSnapshot.available_at <= available_at_before,
            )
        stmt = stmt.order_by(MarketSnapshot.available_at.desc(), MarketSnapshot.created_at.desc()).limit(1)
        return await session.scalar(stmt)

    async def get_market_state_for_snapshot(
        self,
        session: AsyncSession,
        *,
        market_snapshot_id: UUID,
        available_at_before: datetime | None = None,
    ) -> MarketRegimeRecord | None:
        stmt = select(MarketRegimeRecord).where(MarketRegimeRecord.market_snapshot_id == market_snapshot_id)
        if available_at_before is not None:
            stmt = stmt.where(
                MarketRegimeRecord.available_at.is_not(None),
                MarketRegimeRecord.available_at <= available_at_before,
            )
        stmt = stmt.order_by(MarketRegimeRecord.available_at.desc(), MarketRegimeRecord.created_at.desc()).limit(1)
        return await session.scalar(stmt)

    async def list_author_profile_versions(
        self,
        session: AsyncSession,
        *,
        author_profile_version_ids: list[UUID],
    ) -> list[AuthorProfileVersion]:
        if not author_profile_version_ids:
            return []
        result = await session.scalars(
            select(AuthorProfileVersion).where(AuthorProfileVersion.author_profile_version_id.in_(author_profile_version_ids))
        )
        return list(result.all())

    async def list_published_rule_applicability_profiles(
        self,
        session: AsyncSession,
        *,
        rule_version_ids: list[UUID],
        dataset_snapshot_id: UUID,
    ) -> list[RuleApplicabilityProfile]:
        if not rule_version_ids:
            return []
        result = await session.scalars(
            select(RuleApplicabilityProfile).where(
                RuleApplicabilityProfile.lifecycle_state == FormalLifecycleState.published,
                RuleApplicabilityProfile.dataset_snapshot_id == dataset_snapshot_id,
                RuleApplicabilityProfile.rule_version_id.in_(rule_version_ids),
            ).order_by(
                RuleApplicabilityProfile.rule_version_id.asc(),
                RuleApplicabilityProfile.reviewed_at.asc(),
                RuleApplicabilityProfile.created_at.asc(),
                RuleApplicabilityProfile.applicability_profile_id.asc(),
            )
        )
        return list(result.all())
