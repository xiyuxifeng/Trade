from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import CanonicalObjectType
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    LifecycleEvent,
    PromptRun,
    RuleCandidate,
    RuleVersion,
    RuleVersionSourceLink,
)


@dataclass(frozen=True)
class RuleReviewBundle:
    article: BlogArticle
    revision: ArticleRevision
    prompt_run: PromptRun | None
    structure: ArticleStructure | None
    candidate: RuleCandidate
    rule_version: RuleVersion | None


class RuleReviewRepository:
    async def list_candidates(self, session: AsyncSession) -> list[RuleCandidate]:
        stmt = select(RuleCandidate).order_by(RuleCandidate.created_at.asc(), RuleCandidate.candidate_index.asc())
        return list((await session.execute(stmt)).scalars().all())

    async def get_candidate(self, session: AsyncSession, *, candidate_id: UUID) -> RuleCandidate | None:
        return await session.get(RuleCandidate, candidate_id)

    async def get_article(self, session: AsyncSession, *, article_id: UUID) -> BlogArticle | None:
        return await session.get(BlogArticle, article_id)

    async def get_structure(self, session: AsyncSession, *, structure_id: UUID) -> ArticleStructure | None:
        return await session.get(ArticleStructure, structure_id)

    async def get_revision(self, session: AsyncSession, *, revision_id: UUID) -> ArticleRevision | None:
        return await session.get(ArticleRevision, revision_id)

    async def get_prompt_run(self, session: AsyncSession, *, prompt_run_id: UUID | None) -> PromptRun | None:
        if prompt_run_id is None:
            return None
        return await session.get(PromptRun, prompt_run_id)

    async def get_linked_rule_version(self, session: AsyncSession, *, candidate_id: UUID) -> RuleVersion | None:
        stmt = (
            select(RuleVersion)
            .where(RuleVersion.source_candidate_id == candidate_id)
            .order_by(RuleVersion.created_at.desc(), RuleVersion.version_no.desc())
            .limit(1)
        )
        linked = (await session.execute(stmt)).scalars().first()
        if linked is not None:
            return linked

        stmt = (
            select(RuleVersion)
            .join(
                RuleVersionSourceLink,
                RuleVersionSourceLink.rule_version_id == RuleVersion.rule_version_id,
            )
            .where(RuleVersionSourceLink.rule_candidate_id == candidate_id)
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def build_bundle(self, session: AsyncSession, *, candidate_id: UUID, linked_rule_version: RuleVersion | None = None) -> RuleReviewBundle | None:
        candidate = await self.get_candidate(session, candidate_id=candidate_id)
        if candidate is None:
            return None
        article = await self.get_article(session, article_id=candidate.source_article_id)
        structure = await self.get_structure(session, structure_id=candidate.article_structure_id)
        revision = await self.get_revision(session, revision_id=structure.article_revision_id) if structure is not None else None
        if article is None or revision is None:
            return None
        prompt_run = await self.get_prompt_run(session, prompt_run_id=structure.prompt_run_id if structure is not None else None)
        return RuleReviewBundle(
            article=article,
            revision=revision,
            prompt_run=prompt_run,
            structure=structure,
            candidate=candidate,
            rule_version=linked_rule_version or await self.get_linked_rule_version(session, candidate_id=candidate_id),
        )

    async def list_candidate_events(self, session: AsyncSession, *, candidate_id: UUID) -> list[LifecycleEvent]:
        stmt = (
            select(LifecycleEvent)
            .where(LifecycleEvent.object_type == CanonicalObjectType.rule_candidate.value)
            .where(LifecycleEvent.object_id == candidate_id)
            .order_by(LifecycleEvent.occurred_at.asc(), LifecycleEvent.event_id.asc())
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_rule_version_events(self, session: AsyncSession, *, rule_version_id: UUID) -> list[LifecycleEvent]:
        stmt = (
            select(LifecycleEvent)
            .where(LifecycleEvent.object_type == CanonicalObjectType.rule_version.value)
            .where(LifecycleEvent.object_id == rule_version_id)
            .order_by(LifecycleEvent.occurred_at.asc(), LifecycleEvent.event_id.asc())
        )
        return list((await session.execute(stmt)).scalars().all())
