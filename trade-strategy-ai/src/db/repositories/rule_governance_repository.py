from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import require_canonical_write
from src.domain.enums import CanonicalObjectType, FormalLifecycleState
from src.models.stage2_canonical import (
    ArticleStructure,
    LifecycleEvent,
    Rule,
    RuleCandidate,
    RuleFamily,
    RuleFamilyMembership,
    RuleVersion,
    RuleVersionSourceLink,
)


class RuleGovernanceRepository:
    async def list_rule_versions(self, session: AsyncSession) -> list[RuleVersion]:
        stmt = select(RuleVersion).order_by(RuleVersion.created_at.asc(), RuleVersion.version_no.asc())
        return list((await session.execute(stmt)).scalars().all())

    async def get_rule_family_by_fingerprint(
        self,
        session: AsyncSession,
        *,
        family_fingerprint: str,
    ) -> RuleFamily | None:
        stmt = (
            select(RuleFamily)
            .where(RuleFamily.canonical_fingerprint == family_fingerprint)
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def get_rule_by_business_key(self, session: AsyncSession, *, business_key: str) -> Rule | None:
        stmt = select(Rule).where(Rule.business_key == business_key).limit(1)
        return (await session.execute(stmt)).scalars().first()

    async def get_rule_version(self, session: AsyncSession, *, rule_version_id: UUID) -> RuleVersion | None:
        return await session.get(RuleVersion, rule_version_id)

    async def get_linked_rule_version_by_candidate(
        self,
        session: AsyncSession,
        *,
        candidate_id: UUID,
    ) -> RuleVersion | None:
        stmt = (
            select(RuleVersion)
            .join(
                RuleVersionSourceLink,
                RuleVersionSourceLink.rule_version_id == RuleVersion.rule_version_id,
            )
            .where(RuleVersionSourceLink.rule_candidate_id == candidate_id)
            .order_by(RuleVersion.created_at.desc(), RuleVersion.version_no.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def ensure_family(
        self,
        session: AsyncSession,
        *,
        family_fingerprint: str,
        family_key: str,
        name: str | None,
        actor_id: str,
    ) -> RuleFamily:
        require_canonical_write("rule_version", "RuleGovernanceRepository.ensure_family")
        existing = await self.get_rule_family_by_fingerprint(
            session,
            family_fingerprint=family_fingerprint,
        )
        if existing is not None:
            return existing

        family = RuleFamily(
            rule_family_id=uuid4(),
            family_key=family_key,
            canonical_fingerprint=family_fingerprint,
            name=name,
            lifecycle_state=FormalLifecycleState.draft,
            quality_status="complete",
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(family)
        await session.flush()
        return family

    async def ensure_family_membership(
        self,
        session: AsyncSession,
        *,
        family: RuleFamily,
        rule_version: RuleVersion,
        member_role: str,
        parameter_distance: dict[str, Any] | None,
        actor_id: str,
    ) -> RuleFamilyMembership:
        require_canonical_write("rule_version", "RuleGovernanceRepository.ensure_family_membership")
        stmt = (
            select(RuleFamilyMembership)
            .where(RuleFamilyMembership.rule_family_id == family.rule_family_id)
            .where(RuleFamilyMembership.rule_version_id == rule_version.rule_version_id)
            .limit(1)
        )
        existing = (await session.execute(stmt)).scalars().first()
        if existing is not None:
            return existing

        membership = RuleFamilyMembership(
            membership_id=uuid4(),
            rule_family_id=family.rule_family_id,
            rule_version_id=rule_version.rule_version_id,
            member_role=member_role,
            parameter_distance=parameter_distance,
            approved_by=actor_id,
            approved_at=datetime.now(UTC),
        )
        session.add(membership)
        await session.flush()
        return membership

    async def ensure_source_link(
        self,
        session: AsyncSession,
        *,
        rule_version: RuleVersion,
        candidate: RuleCandidate,
        actor_id: str,
        link_reason: str,
    ) -> RuleVersionSourceLink:
        require_canonical_write("rule_version", "RuleGovernanceRepository.ensure_source_link")
        stmt = (
            select(RuleVersionSourceLink)
            .where(RuleVersionSourceLink.rule_version_id == rule_version.rule_version_id)
            .where(RuleVersionSourceLink.rule_candidate_id == candidate.rule_candidate_id)
            .limit(1)
        )
        existing = (await session.execute(stmt)).scalars().first()
        if existing is not None:
            return existing

        link = RuleVersionSourceLink(
            rule_version_source_link_id=uuid4(),
            rule_version_id=rule_version.rule_version_id,
            rule_candidate_id=candidate.rule_candidate_id,
            link_reason=link_reason,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(link)
        await session.flush()
        return link

    async def create_formal_rule(
        self,
        session: AsyncSession,
        *,
        candidate: RuleCandidate,
        actor_id: str,
        reason: str | None,
        exact_fingerprint: str,
        business_key: str,
        title: str,
        description: str | None,
        schema_version: str,
        instrument_scope: dict[str, Any],
        condition_json: dict[str, Any],
        action_json: dict[str, Any],
        parameter_json: dict[str, Any],
        data_dependencies: dict[str, Any],
        evidence_json: dict[str, Any],
        after_review_snapshot: dict[str, Any],
    ) -> RuleVersion:
        require_canonical_write("rule_version", "RuleGovernanceRepository.create_formal_rule")
        now = datetime.now(UTC)
        rule = await self.get_rule_by_business_key(session, business_key=business_key)
        if rule is None:
            rule = Rule(
                rule_id=uuid4(),
                business_key=business_key,
                current_published_version_id=None,
                created_at=now,
                created_by=actor_id,
                updated_at=now,
                updated_by=actor_id,
            )
            session.add(rule)
            await session.flush()

        stmt = (
            select(RuleVersion)
            .where(RuleVersion.rule_id == rule.rule_id)
            .where(RuleVersion.canonical_fingerprint == exact_fingerprint)
            .limit(1)
        )
        existing = (await session.execute(stmt)).scalars().first()
        if existing is not None:
            await self.ensure_source_link(
                session,
                rule_version=existing,
                candidate=candidate,
                actor_id=actor_id,
                link_reason="exact_duplicate",
            )
            return existing

        candidate.review_state = "approved"
        candidate.candidate_fingerprint = exact_fingerprint
        candidate.updated_by = actor_id
        await session.flush()

        rule_version = RuleVersion(
            rule_version_id=uuid4(),
            rule_id=rule.rule_id,
            version_no=1,
            source_candidate_id=candidate.rule_candidate_id,
            canonical_fingerprint=exact_fingerprint,
            schema_version=schema_version,
            lifecycle_state=FormalLifecycleState.draft,
            title=title,
            description=description,
            rule_type=candidate.rule_type,
            instrument_scope=instrument_scope,
            condition_json=condition_json,
            action_json=action_json,
            parameter_json=parameter_json,
            data_dependencies=data_dependencies,
            evidence_json=evidence_json,
            quality_status="complete",
            parent_version_id=None,
            published_at=None,
            published_by=None,
            superseded_at=None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(rule_version)
        await session.flush()

        await self.ensure_source_link(
            session,
            rule_version=rule_version,
            candidate=candidate,
            actor_id=actor_id,
            link_reason="formal_source",
        )

        session.add(
            LifecycleEvent(
                event_id=uuid4(),
                object_type=CanonicalObjectType.rule_candidate.value,
                object_id=candidate.rule_candidate_id,
                from_state="manual_review",
                to_state="approved",
                actor_type="human",
                actor_id=actor_id,
                reason_code="human_approved",
                reason_text=reason,
                before_json={"review_state": "manual_review"},
                after_json=after_review_snapshot,
                occurred_at=now,
                correlation_id=str(rule_version.rule_version_id),
            )
        )
        session.add(
            LifecycleEvent(
                event_id=uuid4(),
                object_type=CanonicalObjectType.rule_version.value,
                object_id=rule_version.rule_version_id,
                from_state=None,
                to_state=FormalLifecycleState.draft.value,
                actor_type="human",
                actor_id=actor_id,
                reason_code="created_from_article_review",
                reason_text=reason,
                before_json=None,
                after_json={
                    "rule_id": str(rule.rule_id),
                    "rule_version_id": str(rule_version.rule_version_id),
                    "source_candidate_id": str(candidate.rule_candidate_id),
                    "lifecycle_state": FormalLifecycleState.draft.value,
                },
                occurred_at=now,
                correlation_id=str(rule_version.rule_version_id),
            )
        )
        await session.flush()
        return rule_version

    async def link_candidate_to_existing_rule_version(
        self,
        session: AsyncSession,
        *,
        candidate: RuleCandidate,
        rule_version: RuleVersion,
        actor_id: str,
        reason: str | None,
        after_review_snapshot: dict[str, Any],
    ) -> RuleVersion:
        require_canonical_write("rule_version", "RuleGovernanceRepository.link_candidate_to_existing_rule_version")
        now = datetime.now(UTC)
        candidate.review_state = "approved"
        candidate.candidate_fingerprint = rule_version.canonical_fingerprint
        candidate.updated_by = actor_id
        await session.flush()
        await self.ensure_source_link(
            session,
            rule_version=rule_version,
            candidate=candidate,
            actor_id=actor_id,
            link_reason="exact_duplicate",
        )
        session.add(
            LifecycleEvent(
                event_id=uuid4(),
                object_type=CanonicalObjectType.rule_candidate.value,
                object_id=candidate.rule_candidate_id,
                from_state="manual_review",
                to_state="approved",
                actor_type="human",
                actor_id=actor_id,
                reason_code="linked_exact_duplicate",
                reason_text=reason,
                before_json={"review_state": "manual_review"},
                after_json=after_review_snapshot,
                occurred_at=now,
                correlation_id=str(rule_version.rule_version_id),
            )
        )
        await session.flush()
        return rule_version

    async def get_candidate_structure(
        self,
        session: AsyncSession,
        *,
        candidate: RuleCandidate,
    ) -> ArticleStructure | None:
        return await session.get(ArticleStructure, candidate.article_structure_id)
