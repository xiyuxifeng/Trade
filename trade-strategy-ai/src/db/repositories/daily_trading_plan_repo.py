from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import require_canonical_write
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_data_snapshot_section import MarketSnapshotSection
from src.models.market_regime_record import MarketRegimeRecord
from src.models.rule_applicability import RuleApplicabilityProfile
from src.models.signal import Signal
from src.models.stage2_canonical import (
    AuthorProfileVersion,
    DailyRuleSelection,
    DailyRuleSelectionItem,
    DailyStrategyInstance,
    RuleVersion,
    StrategyVersion,
    TradingDayPlan,
)


class DailyTradingPlanRepository:
    async def get_strategy_version(self, session: AsyncSession, strategy_version_id: UUID) -> StrategyVersion | None:
        return await session.get(StrategyVersion, strategy_version_id)

    async def get_daily_rule_selection(self, session: AsyncSession, daily_rule_selection_id: UUID) -> DailyRuleSelection | None:
        return await session.get(DailyRuleSelection, daily_rule_selection_id)

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

    async def get_market_snapshot(self, session: AsyncSession, market_snapshot_id: UUID) -> MarketSnapshot | None:
        return await session.get(MarketSnapshot, market_snapshot_id)

    async def list_market_snapshot_sections(
        self,
        session: AsyncSession,
        *,
        snapshot_id: str,
    ) -> list[MarketSnapshotSection]:
        result = await session.scalars(
            select(MarketSnapshotSection)
            .where(MarketSnapshotSection.snapshot_id == snapshot_id)
            .order_by(MarketSnapshotSection.section_id.asc(), MarketSnapshotSection.created_at.asc())
        )
        return list(result.all())

    async def get_market_state(self, session: AsyncSession, market_state_id: UUID) -> MarketRegimeRecord | None:
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

    async def list_rule_versions(
        self,
        session: AsyncSession,
        *,
        rule_version_ids: list[UUID],
    ) -> list[RuleVersion]:
        if not rule_version_ids:
            return []
        result = await session.scalars(select(RuleVersion).where(RuleVersion.rule_version_id.in_(rule_version_ids)))
        return list(result.all())

    async def list_rule_applicability_profiles(
        self,
        session: AsyncSession,
        *,
        applicability_profile_ids: list[UUID],
    ) -> list[RuleApplicabilityProfile]:
        if not applicability_profile_ids:
            return []
        result = await session.scalars(
            select(RuleApplicabilityProfile).where(RuleApplicabilityProfile.applicability_profile_id.in_(applicability_profile_ids))
        )
        return list(result.all())

    async def get_latest_instance(
        self,
        session: AsyncSession,
        *,
        strategy_version_id: UUID,
        trade_date: date,
    ) -> DailyStrategyInstance | None:
        return await session.scalar(
            select(DailyStrategyInstance)
            .where(
                DailyStrategyInstance.strategy_version_id == strategy_version_id,
                DailyStrategyInstance.trade_date == trade_date,
            )
            .order_by(DailyStrategyInstance.revision_no.desc(), DailyStrategyInstance.created_at.desc())
            .limit(1)
        )

    async def get_plan_for_instance(
        self,
        session: AsyncSession,
        *,
        daily_strategy_instance_id: UUID,
    ) -> TradingDayPlan | None:
        return await session.scalar(
            select(TradingDayPlan)
            .where(TradingDayPlan.daily_strategy_instance_id == daily_strategy_instance_id)
            .order_by(TradingDayPlan.revision_no.desc(), TradingDayPlan.created_at.desc())
            .limit(1)
        )

    async def next_instance_revision_no(
        self,
        session: AsyncSession,
        *,
        strategy_version_id: UUID,
        trade_date: date,
    ) -> int:
        value = await session.scalar(
            select(func.max(DailyStrategyInstance.revision_no)).where(
                DailyStrategyInstance.strategy_version_id == strategy_version_id,
                DailyStrategyInstance.trade_date == trade_date,
            )
        )
        return int(value or 0) + 1

    async def create_instance(self, session: AsyncSession, *, instance: DailyStrategyInstance) -> DailyStrategyInstance:
        require_canonical_write("daily_strategy_instance", "DailyTradingPlanRepository.create_instance")
        session.add(instance)
        await session.flush()
        return instance

    async def create_plan(self, session: AsyncSession, *, plan: TradingDayPlan) -> TradingDayPlan:
        require_canonical_write("trading_day_plan", "DailyTradingPlanRepository.create_plan")
        session.add(plan)
        await session.flush()
        return plan

    async def update_instance(self, session: AsyncSession, *, instance: DailyStrategyInstance) -> DailyStrategyInstance:
        require_canonical_write("daily_strategy_instance", "DailyTradingPlanRepository.update_instance")
        session.add(instance)
        await session.flush()
        return instance

    async def update_plan(self, session: AsyncSession, *, plan: TradingDayPlan) -> TradingDayPlan:
        require_canonical_write("trading_day_plan", "DailyTradingPlanRepository.update_plan")
        session.add(plan)
        await session.flush()
        return plan

    async def list_signals_for_plan(
        self,
        session: AsyncSession,
        *,
        trading_day_plan_id: UUID,
    ) -> list[Signal]:
        result = await session.scalars(
            select(Signal)
            .where(Signal.trading_day_plan_id == trading_day_plan_id)
            .order_by(Signal.created_at.asc(), Signal.id.asc())
        )
        return list(result.all())

    async def replace_signals_for_plan(
        self,
        session: AsyncSession,
        *,
        trading_day_plan_id: UUID,
        daily_strategy_instance_id: UUID,
        signals: list[Signal],
    ) -> list[Signal]:
        require_canonical_write("signal", "DailyTradingPlanRepository.replace_signals_for_plan")
        existing = await self.list_signals_for_plan(session, trading_day_plan_id=trading_day_plan_id)
        for item in existing:
            await session.delete(item)
        await session.flush()
        for item in signals:
            item.trading_day_plan_id = trading_day_plan_id
            item.daily_strategy_instance_id = daily_strategy_instance_id
            session.add(item)
        await session.flush()
        return signals

    async def update_signals(self, session: AsyncSession, *, signals: list[Signal]) -> list[Signal]:
        require_canonical_write("signal", "DailyTradingPlanRepository.update_signals")
        for item in signals:
            session.add(item)
        await session.flush()
        return signals
