from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.domain.enums import FormalLifecycleState
from src.models.rule_applicability import RuleApplicabilityProfile, RuleApplicabilityProfileAudit
from src.models.stage2_canonical import BacktestResult, BacktestRun
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

    async def get_formal_backtest_run(self, session: AsyncSession, *, run_id: UUID) -> BacktestRun | None:
        return await session.get(BacktestRun, run_id)

    async def get_formal_backtest_result(
        self,
        session: AsyncSession,
        *,
        result_id: UUID | None = None,
        run_id: UUID | None = None,
    ) -> BacktestResult | None:
        if result_id is not None:
            return await session.get(BacktestResult, result_id)
        if run_id is None:
            return None
        return await session.scalar(select(BacktestResult).where(BacktestResult.run_id == run_id))

    async def next_formal_version_no(self, session: AsyncSession, *, applicability_profile_id: UUID) -> int:
        value = await session.scalar(
            select(func.max(RuleApplicabilityProfile.profile_version_no)).where(
                RuleApplicabilityProfile.applicability_profile_id == applicability_profile_id
            )
        )
        return int(value or 0) + 1

    async def find_current_formal_profile(self, session: AsyncSession, *, run: BacktestRun) -> RuleApplicabilityProfile | None:
        stmt = select(RuleApplicabilityProfile).where(
            RuleApplicabilityProfile.review_status.in_(["draft", "pending_review", "approved"]),
        )
        if run.rule_version_id is not None:
            stmt = stmt.where(RuleApplicabilityProfile.rule_version_id == run.rule_version_id)
        elif run.rule_family_id is not None:
            stmt = stmt.where(RuleApplicabilityProfile.rule_family_id == run.rule_family_id)
        else:
            return None
        stmt = stmt.order_by(RuleApplicabilityProfile.profile_version_no.desc(), RuleApplicabilityProfile.created_at.desc())
        return await session.scalar(stmt.limit(1))

    async def create_formal_profile(self, session: AsyncSession, profile: RuleApplicabilityProfile) -> RuleApplicabilityProfile:
        require_canonical_write(
            "rule_applicability",
            "RuleApplicabilityRepository.create_formal_profile",
        )
        session.add(profile)
        await session.flush()
        return profile

    async def supersede_profile(
        self,
        session: AsyncSession,
        *,
        profile: RuleApplicabilityProfile,
        superseded_by: UUID,
        actor_id: str,
        reason: str | None,
    ) -> None:
        require_canonical_write(
            "rule_applicability",
            "RuleApplicabilityRepository.supersede_profile",
        )
        profile.review_status = "superseded"
        profile.lifecycle_state = FormalLifecycleState.superseded
        profile.superseded_by_profile_id = superseded_by
        await self.record_audit_event(
            session,
            profile=profile,
            event={
                "transition": "superseded",
                "actor_id": actor_id,
                "actor_role": "operator",
                "reason": reason,
                "source_surface": "/rules/backtests",
                "before_state": {"review_status": "draft"},
                "after_state": {"review_status": "superseded", "superseded_by_profile_id": str(superseded_by)},
            },
        )

    async def record_audit_event(self, session: AsyncSession, *, profile: RuleApplicabilityProfile, event: dict) -> None:
        require_canonical_write(
            "rule_applicability",
            "RuleApplicabilityRepository.record_audit_event",
        )
        session.add(
            RuleApplicabilityProfileAudit(
                profile_id=profile.profile_id,
                transition=str(event.get("transition")),
                actor_id=str(event.get("actor_id") or "unknown"),
                actor_role=str(event.get("actor_role") or "unknown"),
                reason=event.get("reason"),
                source_surface=str(event.get("source_surface") or "/rules/backtests"),
                before_state_json=event.get("before_state"),
                after_state_json=event.get("after_state"),
            )
        )
        await session.flush()
