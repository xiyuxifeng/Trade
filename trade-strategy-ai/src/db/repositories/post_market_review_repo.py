from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import require_canonical_write
from src.models.stage2_canonical import (
    DailyRuleSelection,
    DailyRuleSelectionItem,
    DailyStrategyInstance,
    PostMarketReview,
    TradingDayPlan,
)


class PostMarketReviewRepository:
    """Canonical post-market review repository for daily runtime evidence."""

    async def get_plan(self, session: AsyncSession, trading_day_plan_id: UUID) -> TradingDayPlan | None:
        return await session.get(TradingDayPlan, trading_day_plan_id)

    async def get_daily_strategy_instance(
        self,
        session: AsyncSession,
        daily_strategy_instance_id: UUID,
    ) -> DailyStrategyInstance | None:
        return await session.get(DailyStrategyInstance, daily_strategy_instance_id)

    async def get_daily_rule_selection(
        self,
        session: AsyncSession,
        daily_rule_selection_id: UUID,
    ) -> DailyRuleSelection | None:
        return await session.get(DailyRuleSelection, daily_rule_selection_id)

    async def list_selection_items(
        self,
        session: AsyncSession,
        daily_rule_selection_id: UUID,
    ) -> list[DailyRuleSelectionItem]:
        result = await session.scalars(
            select(DailyRuleSelectionItem)
            .where(DailyRuleSelectionItem.daily_rule_selection_id == daily_rule_selection_id)
            .order_by(DailyRuleSelectionItem.created_at.asc(), DailyRuleSelectionItem.daily_rule_selection_item_id.asc())
        )
        return list(result.all())

    async def get_review(self, session: AsyncSession, post_market_review_id: UUID) -> PostMarketReview | None:
        return await session.get(PostMarketReview, post_market_review_id)

    async def list_reviews_for_plan(
        self,
        session: AsyncSession,
        trading_day_plan_id: UUID,
    ) -> list[PostMarketReview]:
        result = await session.scalars(
            select(PostMarketReview)
            .where(PostMarketReview.trading_day_plan_id == trading_day_plan_id)
            .order_by(PostMarketReview.revision_no.asc(), PostMarketReview.created_at.asc())
        )
        return list(result.all())

    async def next_revision_no(self, session: AsyncSession, trading_day_plan_id: UUID) -> int:
        value = await session.scalar(
            select(func.max(PostMarketReview.revision_no)).where(
                PostMarketReview.trading_day_plan_id == trading_day_plan_id
            )
        )
        return int(value or 0) + 1

    async def save_review(self, session: AsyncSession, review: PostMarketReview) -> PostMarketReview:
        require_canonical_write("post_market_review", "PostMarketReviewRepository.save_review")
        session.add(review)
        await session.flush()
        return review
