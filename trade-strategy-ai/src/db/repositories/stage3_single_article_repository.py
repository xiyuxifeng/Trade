from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import require_canonical_write
from src.domain.enums import CanonicalObjectType, FormalLifecycleState
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    LifecycleEvent,
    PromptRun,
    Rule,
    RuleCandidate,
    RuleVersion,
    RuleVersionSourceLink,
)


class Stage3SingleArticleRepository:
    async def get_article(self, session: AsyncSession, *, article_id: UUID) -> BlogArticle | None:
        return await session.get(BlogArticle, article_id)

    async def get_article_revision(
        self,
        session: AsyncSession,
        *,
        article_id: UUID,
        article_revision_id: UUID | None,
    ) -> ArticleRevision | None:
        if article_revision_id is not None:
            revision = await session.get(ArticleRevision, article_revision_id)
            if revision is None or revision.article_id != article_id:
                return None
            return revision

        stmt = (
            select(ArticleRevision)
            .where(ArticleRevision.article_id == article_id)
            .order_by(ArticleRevision.revision_no.desc(), ArticleRevision.captured_at.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def get_prompt_run_bundle(
        self,
        session: AsyncSession,
        *,
        article_id: UUID,
        article_revision_id: UUID,
    ) -> tuple[PromptRun | None, ArticleStructure | None, list[RuleCandidate]]:
        structure_stmt = (
            select(ArticleStructure)
            .where(ArticleStructure.article_id == article_id)
            .where(ArticleStructure.article_revision_id == article_revision_id)
            .order_by(ArticleStructure.updated_at.desc(), ArticleStructure.created_at.desc())
            .limit(1)
        )
        structure = (await session.execute(structure_stmt)).scalars().first()
        if structure is None:
            return None, None, []

        prompt_run = await session.get(PromptRun, structure.prompt_run_id)
        candidates_stmt = (
            select(RuleCandidate)
            .where(RuleCandidate.article_structure_id == structure.article_structure_id)
            .order_by(RuleCandidate.candidate_index.asc())
        )
        candidates = (await session.execute(candidates_stmt)).scalars().all()
        return prompt_run, structure, list(candidates)

    async def get_rule_candidate(
        self,
        session: AsyncSession,
        *,
        candidate_id: UUID,
        article_structure_id: UUID,
    ) -> RuleCandidate | None:
        stmt = (
            select(RuleCandidate)
            .where(RuleCandidate.rule_candidate_id == candidate_id)
            .where(RuleCandidate.article_structure_id == article_structure_id)
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def get_rule_version_by_source_candidate(
        self,
        session: AsyncSession,
        *,
        candidate_id: UUID,
    ) -> RuleVersion | None:
        stmt = (
            select(RuleVersion)
            .where(RuleVersion.source_candidate_id == candidate_id)
            .order_by(RuleVersion.version_no.desc(), RuleVersion.created_at.desc())
            .limit(1)
        )
        direct = (await session.execute(stmt)).scalars().first()
        if direct is not None:
            return direct
        if not await self._table_exists(session, "rule_version_source_links"):
            return None
        link_stmt = (
            select(RuleVersion)
            .join(
                RuleVersionSourceLink,
                RuleVersionSourceLink.rule_version_id == RuleVersion.rule_version_id,
            )
            .where(RuleVersionSourceLink.rule_candidate_id == candidate_id)
            .order_by(RuleVersion.created_at.desc(), RuleVersion.version_no.desc())
            .limit(1)
        )
        return (await session.execute(link_stmt)).scalars().first()

    async def _table_exists(self, session: AsyncSession, table_name: str) -> bool:
        return await session.run_sync(lambda sync_session: inspect(sync_session.get_bind()).has_table(table_name))

    async def approve_candidate(
        self,
        session: AsyncSession,
        *,
        candidate: RuleCandidate,
        actor_id: str,
        reason: str | None,
        formal_lifecycle_state: FormalLifecycleState,
        quality_status: str,
        business_key: str,
        title: str,
        description: str | None,
        schema_version: str,
        instrument_scope: dict,
        condition_json: dict,
        action_json: dict,
        parameter_json: dict,
        data_dependencies: dict,
        evidence_json: dict,
        after_review_snapshot: dict,
    ) -> RuleVersion:
        require_canonical_write("rule_version", "Stage3SingleArticleRepository.approve_candidate")
        existing = await self.get_rule_version_by_source_candidate(
            session,
            candidate_id=candidate.rule_candidate_id,
        )
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        candidate.review_state = "approved"
        candidate.updated_by = actor_id
        await session.flush()

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

        rule_version = RuleVersion(
            rule_version_id=uuid4(),
            rule_id=rule.rule_id,
            version_no=1,
            source_candidate_id=candidate.rule_candidate_id,
            canonical_fingerprint=candidate.candidate_fingerprint,
            schema_version=schema_version,
            lifecycle_state=formal_lifecycle_state,
            title=title,
            description=description,
            rule_type=candidate.rule_type,
            instrument_scope=instrument_scope,
            condition_json=condition_json,
            action_json=action_json,
            parameter_json=parameter_json,
            data_dependencies=data_dependencies,
            evidence_json=evidence_json,
            quality_status=quality_status,
            parent_version_id=None,
            published_at=None,
            published_by=None,
            superseded_at=None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(rule_version)
        await session.flush()

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
                to_state=formal_lifecycle_state.value,
                actor_type="human",
                actor_id=actor_id,
                reason_code="created_from_article_review",
                reason_text=reason,
                before_json=None,
                after_json={
                    "rule_id": str(rule.rule_id),
                    "rule_version_id": str(rule_version.rule_version_id),
                    "source_candidate_id": str(candidate.rule_candidate_id),
                    "lifecycle_state": formal_lifecycle_state.value,
                },
                occurred_at=now,
                correlation_id=str(rule_version.rule_version_id),
            )
        )
        await session.flush()
        return rule_version

    async def reject_candidate(
        self,
        session: AsyncSession,
        *,
        candidate: RuleCandidate,
        actor_id: str,
        reason: str | None,
        before_state: str,
        after_review_snapshot: dict,
    ) -> None:
        require_canonical_write("rule_version", "Stage3SingleArticleRepository.reject_candidate")
        now = datetime.now(UTC)
        candidate.review_state = "rejected"
        candidate.updated_by = actor_id
        session.add(
            LifecycleEvent(
                event_id=uuid4(),
                object_type=CanonicalObjectType.rule_candidate.value,
                object_id=candidate.rule_candidate_id,
                from_state=before_state,
                to_state="rejected",
                actor_type="human",
                actor_id=actor_id,
                reason_code="human_rejected",
                reason_text=reason,
                before_json={"review_state": before_state},
                after_json=after_review_snapshot,
                occurred_at=now,
                correlation_id=str(candidate.rule_candidate_id),
            )
        )
        await session.flush()
