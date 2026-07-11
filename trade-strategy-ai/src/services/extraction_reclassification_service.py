from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.extraction_taxonomy_repository import ExtractionTaxonomyRepository
from src.models.extraction_taxonomy import (
    ExtractionReclassificationItem,
    ExtractionReclassificationRun,
    ReclassificationReviewState,
    ReclassificationRunStatus,
)
from src.models.stage2_canonical import ArticleStructure, PromptRun, PromptValidationState, RuleCandidate
from src.schemas.extraction_taxonomy import SCHEMA_VERSION, TAXONOMY_VERSION, ExtractionItemDraft
from src.services.extraction_taxonomy_service import build_extraction_item, stable_fingerprint


class ExtractionReclassificationError(RuntimeError):
    pass


class ExtractionReclassificationService:
    """Append-only bounded reclassification; old RuleCandidate rows are never updated."""

    def __init__(self, repository: ExtractionTaxonomyRepository | None = None) -> None:
        self._repository = repository or ExtractionTaxonomyRepository()

    async def run_bounded_subset(
        self,
        session: AsyncSession,
        *,
        labels: list[dict[str, Any]],
        classifier: str,
        created_by: str,
    ) -> ExtractionReclassificationRun:
        if not labels:
            raise ExtractionReclassificationError("bounded reclassification requires at least one label")
        normalized = [
            {
                "old_rule_candidate_id": str(label["old_rule_candidate_id"]),
                "draft": ExtractionItemDraft.model_validate(label["draft"]).model_dump(mode="json"),
                "rationale": str(label["rationale"]),
                "accepted": bool(label.get("accepted", True)),
            }
            for label in labels
        ]
        identity = stable_fingerprint({"labels": normalized, "classifier": classifier})
        existing = await self._repository.get_reclassification_run(
            session,
            taxonomy_version=TAXONOMY_VERSION,
            schema_version=SCHEMA_VERSION,
            input_query_fingerprint=identity,
            classifier=classifier,
        )
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        run = ExtractionReclassificationRun(
            reclassification_run_id=uuid4(),
            taxonomy_version=TAXONOMY_VERSION,
            schema_version=SCHEMA_VERSION,
            source_population=f"bounded subset of {len(labels)} old rule_candidates",
            input_query_fingerprint=identity,
            classifier=classifier,
            started_at=now,
            completed_at=None,
            status=ReclassificationRunStatus.running,
            created_by=created_by,
        )
        await self._repository.save_reclassification_run(session, run=run)
        prompt_run = PromptRun(
            prompt_run_id=uuid4(),
            run_id=str(run.reclassification_run_id),
            article_id=None,
            prompt_name="old_candidate_taxonomy_reclassification_v1",
            prompt_version="old_candidate_taxonomy_reclassification_v1",
            schema_name=SCHEMA_VERSION,
            schema_version=SCHEMA_VERSION,
            provider="fixture_or_model_assisted",
            model=classifier,
            input_object_type="rule_candidate_subset",
            input_object_id=str(run.reclassification_run_id),
            input_version_id=identity,
            input_hash=identity,
            request_json={"candidate_ids": [row["old_rule_candidate_id"] for row in normalized]},
            raw_output={"labels": normalized},
            raw_output_text=None,
            validation_state=PromptValidationState.valid,
            validation_errors={},
            retry_count=0,
            token_usage={},
            cost_amount=None,
            cost_currency=None,
            started_at=now,
            completed_at=now,
        )
        session.add(prompt_run)
        await session.flush()

        for index, row in enumerate(normalized):
            candidate_id = UUID(row["old_rule_candidate_id"])
            candidate = await session.get(RuleCandidate, candidate_id)
            if candidate is None:
                raise ExtractionReclassificationError(f"old candidate not found: {candidate_id}")
            structure = await session.get(ArticleStructure, candidate.article_structure_id)
            if structure is None:
                raise ExtractionReclassificationError(f"article structure not found for {candidate_id}")
            draft = ExtractionItemDraft.model_validate(row["draft"])
            snapshot = {
                "rule_candidate_id": str(candidate.rule_candidate_id),
                "article_structure_id": str(candidate.article_structure_id),
                "source_article_id": str(candidate.source_article_id),
                "candidate_index": candidate.candidate_index,
                "candidate_fingerprint": candidate.candidate_fingerprint,
                "rule_type": candidate.rule_type,
                "canonical_payload": candidate.canonical_payload,
                "evidence_json": candidate.evidence_json,
                "explicit_fields": candidate.explicit_fields,
                "inferred_fields": candidate.inferred_fields,
                "missing_fields": candidate.missing_fields,
                "data_dependencies": candidate.data_dependencies,
                "backtestability_status": candidate.backtestability_status,
                "review_state": str(candidate.review_state),
                "quality_status": str(candidate.quality_status),
                "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
            }
            extraction_item_id = None
            if row["accepted"]:
                item = build_extraction_item(
                    draft=draft,
                    article_id=candidate.source_article_id,
                    article_revision_id=structure.article_revision_id,
                    article_structure_id=structure.article_structure_id,
                    prompt_run=prompt_run,
                    item_index=index,
                    source_url=None,
                    origin="old_candidate_reclassification",
                    source_object_type="rule_candidate",
                    source_object_id=str(candidate.rule_candidate_id),
                    lineage=[str(candidate.rule_candidate_id)],
                    created_by=created_by,
                )
                await self._repository.save_items(session, items=[item])
                extraction_item_id = item.extraction_item_id
            reclassification_item = ExtractionReclassificationItem(
                reclassification_item_id=uuid4(),
                reclassification_run_id=run.reclassification_run_id,
                old_rule_candidate_id=candidate.rule_candidate_id,
                extraction_item_id=extraction_item_id,
                proposed_primary_type=draft.primary_type,
                proposed_secondary_tags=draft.secondary_tags,
                proposed_taxonomy_payload=draft.taxonomy_payload.model_dump(mode="json"),
                confidence=draft.confidence.model_dump(mode="json"),
                rationale=row["rationale"],
                review_state=(
                    ReclassificationReviewState.accepted
                    if row["accepted"]
                    else ReclassificationReviewState.unreviewed
                ),
                evidence_snapshot=snapshot,
            )
            await self._repository.save_reclassification_item(session, item=reclassification_item)

        run.status = ReclassificationRunStatus.completed
        run.completed_at = datetime.now(UTC)
        await session.flush()
        return run

    async def list_run_items(
        self, session: AsyncSession, *, run_id: UUID
    ) -> list[ExtractionReclassificationItem]:
        return list(
            (
                await session.execute(
                    select(ExtractionReclassificationItem)
                    .where(ExtractionReclassificationItem.reclassification_run_id == run_id)
                    .order_by(ExtractionReclassificationItem.created_at.asc())
                )
            ).scalars().all()
        )
