from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import require_canonical_write
from src.domain.enums import AuthorProfileKind, FormalLifecycleState
from src.models.market_data_snapshot import MarketSnapshot
from src.models.rule_applicability import RuleApplicabilityProfile
from src.models.stage2_canonical import (
    AuthorProfileVersion,
    DatasetLifecycleState,
    DatasetSnapshot,
    RuleVersion,
    Strategy,
    StrategyRuleMembership,
    StrategyVersion,
    StrategyVersionAudit,
)


class StrategyRepository:
    """Canonical strategy repository for Stage 8."""

    async def get_strategy(self, session: AsyncSession, strategy_id: str | UUID) -> Strategy | None:
        if not isinstance(strategy_id, UUID):
            strategy_id = UUID(str(strategy_id))
        return await session.get(Strategy, strategy_id)

    async def get_strategy_by_business_key(self, session: AsyncSession, *, business_key: str) -> Strategy | None:
        return await session.scalar(select(Strategy).where(Strategy.business_key == business_key))

    async def add_strategy(self, session: AsyncSession, strategy: Strategy) -> Strategy:
        require_canonical_write("strategy", "StrategyRepository.add_strategy")
        session.add(strategy)
        await session.flush()
        return strategy

    async def get_version(self, session: AsyncSession, version_id: str | UUID) -> StrategyVersion | None:
        if not isinstance(version_id, UUID):
            version_id = UUID(str(version_id))
        return await session.get(StrategyVersion, version_id)

    async def list_versions(self, session: AsyncSession, *, limit: int = 50) -> list[StrategyVersion]:
        result = await session.scalars(
            select(StrategyVersion).order_by(StrategyVersion.updated_at.desc(), StrategyVersion.version_no.desc()).limit(limit)
        )
        return list(result.all())

    async def next_version_no(self, session: AsyncSession, *, strategy_id: UUID) -> int:
        value = await session.scalar(select(func.max(StrategyVersion.version_no)).where(StrategyVersion.strategy_id == strategy_id))
        return int(value or 0) + 1

    async def add_version(self, session: AsyncSession, version: StrategyVersion) -> StrategyVersion:
        require_canonical_write("strategy", "StrategyRepository.add_version")
        session.add(version)
        await session.flush()
        return version

    async def replace_rule_memberships(
        self,
        session: AsyncSession,
        *,
        strategy_version_id: UUID,
        memberships: list[StrategyRuleMembership],
    ) -> None:
        require_canonical_write("strategy", "StrategyRepository.replace_rule_memberships")
        existing = await session.scalars(
            select(StrategyRuleMembership).where(StrategyRuleMembership.strategy_version_id == strategy_version_id)
        )
        for row in existing.all():
            await session.delete(row)
        for membership in memberships:
            session.add(membership)
        await session.flush()

    async def list_rule_memberships(self, session: AsyncSession, *, strategy_version_id: UUID) -> list[StrategyRuleMembership]:
        result = await session.scalars(
            select(StrategyRuleMembership).where(StrategyRuleMembership.strategy_version_id == strategy_version_id)
        )
        return list(result.all())

    async def set_current_published_version(
        self,
        session: AsyncSession,
        *,
        strategy: Strategy,
        version_id: UUID,
        actor_id: str,
        updated_at: datetime,
    ) -> None:
        require_canonical_write("strategy", "StrategyRepository.set_current_published_version")
        strategy.current_published_version_id = version_id
        strategy.updated_by = actor_id
        strategy.updated_at = updated_at
        await session.flush()

    async def record_audit(
        self,
        session: AsyncSession,
        *,
        version: StrategyVersion,
        transition: str,
        actor_id: str,
        actor_role: str,
        reason: str | None,
        source_surface: str,
        before_state: dict | None,
        after_state: dict | None,
    ) -> None:
        require_canonical_write("strategy", "StrategyRepository.record_audit")
        session.add(
            StrategyVersionAudit(
                audit_id=uuid4(),
                strategy_version_id=version.strategy_version_id,
                transition=transition,
                actor_id=actor_id,
                actor_role=actor_role,
                reason=reason,
                source_surface=source_surface,
                before_state_json=before_state,
                after_state_json=after_state,
            )
        )
        await session.flush()

    async def list_published_rule_versions(self, session: AsyncSession) -> list[RuleVersion]:
        result = await session.scalars(
            select(RuleVersion)
            .where(RuleVersion.lifecycle_state == FormalLifecycleState.published)
            .order_by(RuleVersion.published_at.desc(), RuleVersion.title.asc())
        )
        return list(result.all())

    async def list_published_author_profiles(self, session: AsyncSession, *, profile_kind: AuthorProfileKind) -> list[AuthorProfileVersion]:
        result = await session.scalars(
            select(AuthorProfileVersion)
            .where(
                AuthorProfileVersion.profile_kind == profile_kind,
                AuthorProfileVersion.lifecycle_state == FormalLifecycleState.published,
            )
            .order_by(AuthorProfileVersion.published_at.desc(), AuthorProfileVersion.version_no.desc())
        )
        return list(result.all())

    async def list_ready_dataset_snapshots(self, session: AsyncSession) -> list[DatasetSnapshot]:
        result = await session.scalars(
            select(DatasetSnapshot)
            .where(DatasetSnapshot.lifecycle_state == DatasetLifecycleState.ready)
            .order_by(DatasetSnapshot.trade_date.desc(), DatasetSnapshot.created_at.desc())
        )
        return list(result.all())

    async def list_market_snapshots(self, session: AsyncSession) -> list[MarketSnapshot]:
        result = await session.scalars(
            select(MarketSnapshot).order_by(MarketSnapshot.trade_date.desc(), MarketSnapshot.available_at.desc())
        )
        return list(result.all())

    async def list_published_rule_applicability_profiles(self, session: AsyncSession) -> list[RuleApplicabilityProfile]:
        result = await session.scalars(
            select(RuleApplicabilityProfile)
            .where(RuleApplicabilityProfile.lifecycle_state == FormalLifecycleState.published)
            .order_by(RuleApplicabilityProfile.reviewed_at.desc(), RuleApplicabilityProfile.sample_count.desc())
        )
        return list(result.all())
