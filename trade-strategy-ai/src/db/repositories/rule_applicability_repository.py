from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.models.rule_applicability import RuleApplicabilityProfile
from src.common.stage2_writer_routing import require_canonical_write


class RuleApplicabilityRepository:
    """Rule 适用性画像仓储。"""

    async def upsert_profile(self, session: AsyncSession, profile: RuleApplicabilityProfile) -> RuleApplicabilityProfile:
        """按 rule_id + profile_version + source_backtest_id 写入或更新 profile。"""
        require_canonical_write(
            "rule_applicability",
            "RuleApplicabilityRepository.upsert_profile",
        )
        existing = await session.scalar(
            select(RuleApplicabilityProfile).where(
                RuleApplicabilityProfile.rule_id == profile.rule_id,
                RuleApplicabilityProfile.profile_version == profile.profile_version,
                RuleApplicabilityProfile.source_backtest_id == profile.source_backtest_id,
            )
        )
        if existing is None:
            session.add(profile)
            await session.flush()
            return profile

        for field in (
            "source_rule_version",
            "market_regime_version",
            "source_feature_version",
            "review_status",
            "min_sample_count",
            "confidence",
            "applicable_regimes_json",
            "blocked_regimes_json",
            "neutral_regimes_json",
            "best_market_conditions_json",
            "worst_market_conditions_json",
            "summary_json",
            "storage_ref",
            "reviewed_by",
            "reviewed_at",
        ):
            setattr(existing, field, getattr(profile, field))
        await session.flush()
        return existing

    async def get_by_id(self, session: AsyncSession, profile_id: str | UUID) -> RuleApplicabilityProfile | None:
        """按 profile_id 查询 profile。"""
        if not isinstance(profile_id, UUID):
            profile_id = UUID(str(profile_id))
        return await session.scalar(select(RuleApplicabilityProfile).where(RuleApplicabilityProfile.profile_id == profile_id))

    async def get_by_rule_version_source(
        self,
        session: AsyncSession,
        *,
        rule_id: str,
        profile_version: str,
        source_backtest_id: str,
    ) -> RuleApplicabilityProfile | None:
        """按规则、版本和回测来源查询 profile。"""
        return await session.scalar(
            select(RuleApplicabilityProfile).where(
                RuleApplicabilityProfile.rule_id == rule_id,
                RuleApplicabilityProfile.profile_version == profile_version,
                RuleApplicabilityProfile.source_backtest_id == source_backtest_id,
            )
        )

    async def list_profiles(
        self,
        session: AsyncSession,
        *,
        rule_id: str | None = None,
        review_status: str | None = None,
        profile_version: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RuleApplicabilityProfile]:
        """查询 profile 列表。"""
        stmt = select(RuleApplicabilityProfile)
        if rule_id:
            stmt = stmt.where(RuleApplicabilityProfile.rule_id == rule_id)
        if review_status:
            stmt = stmt.where(RuleApplicabilityProfile.review_status == review_status)
        if profile_version:
            stmt = stmt.where(RuleApplicabilityProfile.profile_version == profile_version)
        stmt = stmt.order_by(RuleApplicabilityProfile.created_at.desc(), RuleApplicabilityProfile.profile_id.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())

    async def count_profiles(
        self,
        session: AsyncSession,
        *,
        rule_id: str | None = None,
        review_status: str | None = None,
        profile_version: str | None = None,
    ) -> int:
        """统计 profile 数量。"""
        stmt = select(func.count()).select_from(RuleApplicabilityProfile)
        if rule_id:
            stmt = stmt.where(RuleApplicabilityProfile.rule_id == rule_id)
        if review_status:
            stmt = stmt.where(RuleApplicabilityProfile.review_status == review_status)
        if profile_version:
            stmt = stmt.where(RuleApplicabilityProfile.profile_version == profile_version)
        result = await session.scalar(stmt)
        return int(result or 0)
