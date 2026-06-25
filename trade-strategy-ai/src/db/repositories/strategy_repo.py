from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import require_canonical_write
from src.domain.enums import AuthorProfileKind, CanonicalObjectType, FormalLifecycleState, ProposalType
from src.models.market_data_snapshot import MarketSnapshot
from src.models.rule_applicability import RuleApplicabilityProfile
from src.models.stage2_canonical import (
    AuthorProfileVersion,
    BacktestResult,
    BacktestRun,
    DatasetLifecycleState,
    DatasetSnapshot,
    LifecycleEvent,
    OptimizationProposal,
    PostMarketReview,
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

    async def get_rule_version(self, session: AsyncSession, rule_version_id: str | UUID) -> RuleVersion | None:
        if not isinstance(rule_version_id, UUID):
            rule_version_id = UUID(str(rule_version_id))
        return await session.get(RuleVersion, rule_version_id)

    async def get_author_profile_version(self, session: AsyncSession, version_id: str | UUID) -> AuthorProfileVersion | None:
        if not isinstance(version_id, UUID):
            version_id = UUID(str(version_id))
        return await session.get(AuthorProfileVersion, version_id)

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

    async def list_versions_for_strategy(self, session: AsyncSession, *, strategy_id: UUID) -> list[StrategyVersion]:
        result = await session.scalars(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.version_no.asc(), StrategyVersion.updated_at.asc())
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
        now = datetime.now(UTC)
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
                created_at=now,
                updated_at=now,
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

    async def list_rule_versions_by_ids(self, session: AsyncSession, *, rule_version_ids: list[UUID]) -> list[RuleVersion]:
        if not rule_version_ids:
            return []
        result = await session.scalars(select(RuleVersion).where(RuleVersion.rule_version_id.in_(rule_version_ids)))
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

    async def list_market_snapshots_by_ids(self, session: AsyncSession, *, market_snapshot_ids: list[UUID]) -> list[MarketSnapshot]:
        if not market_snapshot_ids:
            return []
        result = await session.scalars(select(MarketSnapshot).where(MarketSnapshot.id.in_(market_snapshot_ids)))
        return list(result.all())

    async def list_published_rule_applicability_profiles(self, session: AsyncSession) -> list[RuleApplicabilityProfile]:
        result = await session.scalars(
            select(RuleApplicabilityProfile)
            .where(RuleApplicabilityProfile.lifecycle_state == FormalLifecycleState.published)
            .order_by(RuleApplicabilityProfile.reviewed_at.desc(), RuleApplicabilityProfile.sample_count.desc())
        )
        return list(result.all())

    async def list_rule_applicability_profiles_by_ids(
        self,
        session: AsyncSession,
        *,
        applicability_profile_ids: list[UUID],
    ) -> list[RuleApplicabilityProfile]:
        if not applicability_profile_ids:
            return []
        result = await session.scalars(
            select(RuleApplicabilityProfile).where(
                RuleApplicabilityProfile.applicability_profile_id.in_(applicability_profile_ids)
            )
        )
        return list(result.all())

    async def list_backtest_runs_by_ids(self, session: AsyncSession, *, run_ids: list[UUID]) -> list[BacktestRun]:
        if not run_ids:
            return []
        result = await session.scalars(select(BacktestRun).where(BacktestRun.run_id.in_(run_ids)))
        return list(result.all())

    async def list_backtest_results_by_ids(self, session: AsyncSession, *, result_ids: list[UUID]) -> list[BacktestResult]:
        if not result_ids:
            return []
        result = await session.scalars(select(BacktestResult).where(BacktestResult.result_id.in_(result_ids)))
        return list(result.all())

    async def get_post_market_review(self, session: AsyncSession, review_id: str | UUID) -> PostMarketReview | None:
        if not isinstance(review_id, UUID):
            review_id = UUID(str(review_id))
        return await session.get(PostMarketReview, review_id)

    async def next_proposal_revision_no(
        self,
        session: AsyncSession,
        *,
        post_market_review_id: UUID,
        target_asset_id: UUID,
        proposal_type: ProposalType,
    ) -> int:
        value = await session.scalar(
            select(func.max(OptimizationProposal.revision_no)).where(
                OptimizationProposal.post_market_review_id == post_market_review_id,
                OptimizationProposal.target_asset_id == target_asset_id,
                OptimizationProposal.proposal_type == proposal_type,
            )
        )
        return int(value or 0) + 1

    async def add_proposal(self, session: AsyncSession, proposal: OptimizationProposal) -> OptimizationProposal:
        require_canonical_write("strategy", "StrategyRepository.add_proposal")
        session.add(proposal)
        await session.flush()
        return proposal

    async def get_proposal(self, session: AsyncSession, proposal_id: str | UUID) -> OptimizationProposal | None:
        if not isinstance(proposal_id, UUID):
            proposal_id = UUID(str(proposal_id))
        return await session.get(OptimizationProposal, proposal_id)

    async def list_proposals_for_review(
        self,
        session: AsyncSession,
        *,
        post_market_review_id: UUID,
        proposal_type: ProposalType | None = None,
        limit: int = 200,
    ) -> list[OptimizationProposal]:
        stmt = (
            select(OptimizationProposal)
            .where(OptimizationProposal.post_market_review_id == post_market_review_id)
            .order_by(OptimizationProposal.updated_at.desc(), OptimizationProposal.revision_no.desc())
            .limit(limit)
        )
        if proposal_type is not None:
            stmt = stmt.where(OptimizationProposal.proposal_type == proposal_type)
        result = await session.scalars(stmt)
        return list(result.all())

    async def list_proposals(
        self,
        session: AsyncSession,
        *,
        proposal_type: ProposalType | None = None,
        limit: int = 50,
    ) -> list[OptimizationProposal]:
        stmt = (
            select(OptimizationProposal)
            .order_by(OptimizationProposal.updated_at.desc(), OptimizationProposal.revision_no.desc())
            .limit(limit)
        )
        if proposal_type is not None:
            stmt = stmt.where(OptimizationProposal.proposal_type == proposal_type)
        result = await session.scalars(stmt)
        return list(result.all())

    async def list_strategy_revision_proposals(self, session: AsyncSession, *, limit: int = 50) -> list[OptimizationProposal]:
        result = await session.scalars(
            select(OptimizationProposal)
            .where(OptimizationProposal.proposal_type == ProposalType.strategy_revision)
            .order_by(OptimizationProposal.updated_at.desc(), OptimizationProposal.revision_no.desc())
            .limit(limit)
        )
        return list(result.all())

    async def record_lifecycle_event(
        self,
        session: AsyncSession,
        *,
        object_id: UUID,
        from_state: str | None,
        to_state: str,
        actor_id: str,
        actor_role: str,
        reason: str | None,
        before_state: dict | None,
        after_state: dict | None,
        correlation_id: str | None = None,
    ) -> None:
        require_canonical_write("strategy", "StrategyRepository.record_lifecycle_event")
        session.add(
            LifecycleEvent(
                event_id=uuid4(),
                object_type=CanonicalObjectType.optimization_proposal.value,
                object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                actor_type=actor_role,
                actor_id=actor_id,
                reason_text=reason,
                before_json=before_state,
                after_json=after_state,
                occurred_at=datetime.now(UTC),
                correlation_id=correlation_id,
            )
        )
        await session.flush()
