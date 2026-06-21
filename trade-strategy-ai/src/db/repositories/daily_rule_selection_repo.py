from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_regime_record import MarketRegimeRecord
from src.models.rule_applicability import RuleApplicabilityProfile
from src.models.stage2_canonical import (
    AuthorProfileVersion,
    DailyRuleSelection,
    DailyRuleSelectionItem,
    StrategyRuleMembership,
    StrategyVersion,
)
from src.domain.enums import FormalLifecycleState


class DailyRuleSelectionRepository:
    async def get_strategy_version(self, session: AsyncSession, strategy_version_id: UUID) -> StrategyVersion | None:
        return await session.get(StrategyVersion, strategy_version_id)

    async def list_strategy_rule_memberships(
        self,
        session: AsyncSession,
        *,
        strategy_version_id: UUID,
    ) -> list[StrategyRuleMembership]:
        result = await session.scalars(
            select(StrategyRuleMembership).where(StrategyRuleMembership.strategy_version_id == strategy_version_id)
        )
        return list(result.all())

    async def get_market_state(self, session: AsyncSession, *, market_state_id: UUID) -> MarketRegimeRecord | None:
        return await session.get(MarketRegimeRecord, market_state_id)

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
            )
        )
        return list(result.all())

    async def get_latest_selection(
        self,
        session: AsyncSession,
        *,
        strategy_version_id: UUID,
        market_state_id: UUID,
        trade_date: date,
    ) -> DailyRuleSelection | None:
        return await session.scalar(
            select(DailyRuleSelection)
            .where(
                DailyRuleSelection.strategy_version_id == strategy_version_id,
                DailyRuleSelection.market_state_id == market_state_id,
                DailyRuleSelection.trade_date == trade_date,
            )
            .order_by(DailyRuleSelection.revision_no.desc(), DailyRuleSelection.created_at.desc())
            .limit(1)
        )

    async def list_selection_items(
        self,
        session: AsyncSession,
        *,
        daily_rule_selection_id: UUID,
    ) -> list[DailyRuleSelectionItem]:
        result = await session.scalars(
            select(DailyRuleSelectionItem)
            .where(DailyRuleSelectionItem.daily_rule_selection_id == daily_rule_selection_id)
            .order_by(DailyRuleSelectionItem.created_at.asc(), DailyRuleSelectionItem.daily_rule_selection_item_id.asc())
        )
        return list(result.all())

    async def next_revision_no(
        self,
        session: AsyncSession,
        *,
        strategy_version_id: UUID,
        market_state_id: UUID,
        trade_date: date,
    ) -> int:
        value = await session.scalar(
            select(func.max(DailyRuleSelection.revision_no)).where(
                DailyRuleSelection.strategy_version_id == strategy_version_id,
                DailyRuleSelection.market_state_id == market_state_id,
                DailyRuleSelection.trade_date == trade_date,
            )
        )
        return int(value or 0) + 1

    async def create_selection(
        self,
        session: AsyncSession,
        *,
        selection: DailyRuleSelection,
        items: list[DailyRuleSelectionItem],
    ) -> tuple[DailyRuleSelection, list[DailyRuleSelectionItem]]:
        session.add(selection)
        await session.flush()
        for item in items:
            item.daily_rule_selection_id = selection.daily_rule_selection_id
            session.add(item)
        await session.flush()
        return selection, items
