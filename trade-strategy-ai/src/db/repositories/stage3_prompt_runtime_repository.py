from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import require_canonical_write
from src.models.stage2_canonical import ArticleStructure, PromptRun, PromptValidationState, RuleCandidate


class Stage3PromptRunRepository:
    async def get_cached_result(
        self,
        session: AsyncSession,
        *,
        prompt_name: str,
        prompt_version: str,
        schema_version: str,
        model: str,
        input_hash: str,
    ) -> tuple[PromptRun, ArticleStructure, list[RuleCandidate]] | None:
        stmt = (
            select(PromptRun)
            .where(PromptRun.prompt_name == prompt_name)
            .where(PromptRun.prompt_version == prompt_version)
            .where(PromptRun.schema_version == schema_version)
            .where(PromptRun.model == model)
            .where(PromptRun.input_hash == input_hash)
            .where(PromptRun.validation_state.in_([PromptValidationState.valid, PromptValidationState.repaired]))
            .order_by(PromptRun.completed_at.desc().nullslast(), PromptRun.created_at.desc())
        )
        prompt_run = (await session.execute(stmt)).scalars().first()
        if prompt_run is None:
            return None
        structure = (
            await session.execute(
                select(ArticleStructure).where(ArticleStructure.prompt_run_id == prompt_run.prompt_run_id)
            )
        ).scalars().first()
        if structure is None:
            return None
        candidates = (
            await session.execute(
                select(RuleCandidate)
                .where(RuleCandidate.article_structure_id == structure.article_structure_id)
                .order_by(RuleCandidate.candidate_index.asc())
            )
        ).scalars().all()
        return prompt_run, structure, list(candidates)

    async def save_run(self, session: AsyncSession, run: PromptRun) -> PromptRun:
        require_canonical_write("article_analysis", "Stage3PromptRunRepository.save_run")
        existing = (
            await session.execute(
                select(PromptRun)
                .where(PromptRun.prompt_name == run.prompt_name)
                .where(PromptRun.prompt_version == run.prompt_version)
                .where(PromptRun.schema_version == run.schema_version)
                .where(PromptRun.model == run.model)
                .where(PromptRun.input_hash == run.input_hash)
                .where(PromptRun.retry_count == run.retry_count)
            )
        ).scalars().first()
        if existing is not None:
            for field in (
                "run_id",
                "article_id",
                "schema_name",
                "provider",
                "input_object_type",
                "input_object_id",
                "input_version_id",
                "request_json",
                "raw_output",
                "raw_output_text",
                "validation_state",
                "validation_errors",
                "token_usage",
                "cost_amount",
                "cost_currency",
                "started_at",
                "completed_at",
            ):
                setattr(existing, field, getattr(run, field))
            await session.flush()
            return existing
        session.add(run)
        await session.flush()
        return run


class Stage3ArticleAnalysisRepository:
    async def save_structure_with_candidates(
        self,
        session: AsyncSession,
        *,
        structure: ArticleStructure,
        candidates: list[RuleCandidate],
    ) -> tuple[ArticleStructure, list[RuleCandidate]]:
        require_canonical_write("article_analysis", "Stage3ArticleAnalysisRepository.save_structure_with_candidates")
        existing_structure = (
            await session.execute(
                select(ArticleStructure).where(ArticleStructure.prompt_run_id == structure.prompt_run_id)
            )
        ).scalars().first()
        if existing_structure is None:
            session.add(structure)
            await session.flush()
            existing_structure = structure
        else:
            for field in (
                "article_revision_id",
                "schema_version",
                "payload",
                "evidence_json",
                "missing_fields",
                "inference_fields",
                "lifecycle_state",
                "quality_status",
                "created_by",
                "updated_by",
            ):
                setattr(existing_structure, field, getattr(structure, field))
            await session.flush()

        saved_candidates: list[RuleCandidate] = []
        for candidate in candidates:
            candidate.article_structure_id = existing_structure.article_structure_id
            existing_candidate = (
                await session.execute(
                    select(RuleCandidate)
                    .where(RuleCandidate.article_structure_id == existing_structure.article_structure_id)
                    .where(RuleCandidate.candidate_index == candidate.candidate_index)
                )
            ).scalars().first()
            if existing_candidate is None:
                session.add(candidate)
                await session.flush()
                saved_candidates.append(candidate)
                continue
            for field in (
                "candidate_fingerprint",
                "rule_type",
                "canonical_payload",
                "evidence_json",
                "explicit_fields",
                "inferred_fields",
                "missing_fields",
                "data_dependencies",
                "backtestability_status",
                "review_state",
                "quality_status",
                "created_by",
                "updated_by",
            ):
                setattr(existing_candidate, field, getattr(candidate, field))
            await session.flush()
            saved_candidates.append(existing_candidate)
        return existing_structure, saved_candidates
