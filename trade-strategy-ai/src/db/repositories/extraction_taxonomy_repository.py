from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.extraction_taxonomy import (
    ExtractionItem,
    ExtractionReclassificationItem,
    ExtractionReclassificationRun,
)
from src.models.stage2_canonical import RuleCandidate, RuleVersion


class ExtractionTaxonomyRepository:
    async def list_for_structure(
        self, session: AsyncSession, *, article_structure_id: UUID
    ) -> list[ExtractionItem]:
        result = await session.execute(
            select(ExtractionItem)
            .where(ExtractionItem.article_structure_id == article_structure_id)
            .order_by(ExtractionItem.item_index.asc(), ExtractionItem.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_item(self, session: AsyncSession, *, item_id: UUID) -> ExtractionItem | None:
        return await session.get(ExtractionItem, item_id)

    async def save_items(
        self, session: AsyncSession, *, items: list[ExtractionItem]
    ) -> list[ExtractionItem]:
        saved: list[ExtractionItem] = []
        for item in items:
            existing = (
                await session.execute(
                    select(ExtractionItem)
                    .where(ExtractionItem.prompt_run_id == item.prompt_run_id)
                    .where(ExtractionItem.item_index == item.item_index)
                )
            ).scalars().first()
            if existing is not None:
                if existing.item_fingerprint != item.item_fingerprint:
                    raise ValueError("append-only extraction identity conflicts with existing content")
                saved.append(existing)
                continue
            session.add(item)
            await session.flush()
            saved.append(item)
        return saved

    async def next_item_index(self, session: AsyncSession, *, prompt_run_id: UUID) -> int:
        value = await session.scalar(
            select(func.max(ExtractionItem.item_index)).where(ExtractionItem.prompt_run_id == prompt_run_id)
        )
        return int(value) + 1 if value is not None else 0

    async def get_rule_version_for_item(
        self, session: AsyncSession, *, item_id: UUID
    ) -> RuleVersion | None:
        return (
            await session.execute(
                select(RuleVersion)
                .where(RuleVersion.source_extraction_item_id == item_id)
                .order_by(RuleVersion.created_at.desc())
            )
        ).scalars().first()

    async def get_rule_version_by_fingerprint(
        self, session: AsyncSession, *, fingerprint: str
    ) -> RuleVersion | None:
        return (
            await session.execute(
                select(RuleVersion).where(RuleVersion.canonical_fingerprint == fingerprint).limit(1)
            )
        ).scalars().first()

    async def get_old_candidate(
        self, session: AsyncSession, *, candidate_id: UUID
    ) -> RuleCandidate | None:
        return await session.get(RuleCandidate, candidate_id)

    async def get_reclassification_run(
        self,
        session: AsyncSession,
        *,
        taxonomy_version: str,
        schema_version: str,
        input_query_fingerprint: str,
        classifier: str,
    ) -> ExtractionReclassificationRun | None:
        return (
            await session.execute(
                select(ExtractionReclassificationRun)
                .where(ExtractionReclassificationRun.taxonomy_version == taxonomy_version)
                .where(ExtractionReclassificationRun.schema_version == schema_version)
                .where(ExtractionReclassificationRun.input_query_fingerprint == input_query_fingerprint)
                .where(ExtractionReclassificationRun.classifier == classifier)
            )
        ).scalars().first()

    async def save_reclassification_run(
        self, session: AsyncSession, *, run: ExtractionReclassificationRun
    ) -> ExtractionReclassificationRun:
        existing = await self.get_reclassification_run(
            session,
            taxonomy_version=run.taxonomy_version,
            schema_version=run.schema_version,
            input_query_fingerprint=run.input_query_fingerprint,
            classifier=run.classifier,
        )
        if existing is not None:
            return existing
        session.add(run)
        await session.flush()
        return run

    async def save_reclassification_item(
        self, session: AsyncSession, *, item: ExtractionReclassificationItem
    ) -> ExtractionReclassificationItem:
        existing = (
            await session.execute(
                select(ExtractionReclassificationItem)
                .where(
                    ExtractionReclassificationItem.reclassification_run_id
                    == item.reclassification_run_id
                )
                .where(
                    ExtractionReclassificationItem.old_rule_candidate_id
                    == item.old_rule_candidate_id
                )
            )
        ).scalars().first()
        if existing is not None:
            if (
                existing.proposed_primary_type != item.proposed_primary_type
                or existing.proposed_taxonomy_payload != item.proposed_taxonomy_payload
            ):
                raise ValueError("append-only reclassification identity conflicts with existing label")
            return existing
        session.add(item)
        await session.flush()
        return item
