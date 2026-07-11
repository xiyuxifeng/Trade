from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.blog_article import BlogArticle
from src.models.extraction_taxonomy import ExtractionItem
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    PromptRun,
    RuleVersion,
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
    ) -> tuple[PromptRun | None, ArticleStructure | None, list[ExtractionItem]]:
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
        items_stmt = (
            select(ExtractionItem)
            .where(ExtractionItem.article_structure_id == structure.article_structure_id)
            .order_by(ExtractionItem.item_index.asc())
        )
        items = (await session.execute(items_stmt)).scalars().all()
        return prompt_run, structure, list(items)

    async def get_extraction_item(
        self,
        session: AsyncSession,
        *,
        item_id: UUID,
        article_structure_id: UUID,
    ) -> ExtractionItem | None:
        stmt = (
            select(ExtractionItem)
            .where(ExtractionItem.extraction_item_id == item_id)
            .where(ExtractionItem.article_structure_id == article_structure_id)
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def get_rule_version_by_source_item(
        self, session: AsyncSession, *, item_id: UUID
    ) -> RuleVersion | None:
        return (
            await session.execute(
                select(RuleVersion)
                .where(RuleVersion.source_extraction_item_id == item_id)
                .order_by(RuleVersion.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
