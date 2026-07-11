from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal
from uuid import UUID

from src.db.repositories.stage3_single_article_repository import Stage3SingleArticleRepository
from src.llm.runtime import PromptRuntimeError
from src.models.blog_article import BlogArticle
from src.models.extraction_taxonomy import ExtractionItem
from src.models.stage2_canonical import ArticleRevision, ArticleStructure, PromptRun, RuleVersion
from src.services.extraction_taxonomy_service import (
    Eligibility,
    ExtractionTaxonomyError,
    ExtractionTaxonomyService,
    eligibility_for,
)
from src.services.stage3_prompt_runtime_service import ArticlePromptInput, Stage3PromptRuntimeService


JourneyStatus = Literal["ready", "partial", "empty"]
HumanReviewDecision = Literal["accept", "reject"]
SummarySource = Literal["article_revision_source_payload", "blog_article_current", "unavailable"]


@dataclass(frozen=True)
class SummaryProvenance:
    summary: str | None
    source: SummarySource
    article_revision_id: str
    content_hash: str
    available: bool
    aligned: bool
    reason: str | None = None


@dataclass(frozen=True)
class ArticleStructureProvenance:
    article_structure_id: str | None
    article_revision_id: str | None
    prompt_run_id: str | None
    prompt_name: str | None
    prompt_version: str | None
    schema_name: str | None
    schema_version: str | None
    available: bool


@dataclass(frozen=True)
class ArticleJourney:
    status: JourneyStatus
    article: BlogArticle
    revision: ArticleRevision
    prompt_run: PromptRun | None
    structure: ArticleStructure | None
    extraction_items: list[ExtractionItem]
    eligibilities: dict[UUID, Eligibility]
    rule_versions: dict[UUID, RuleVersion]
    summary_provenance: SummaryProvenance
    article_structure_provenance: ArticleStructureProvenance
    message: str | None = None


class Stage3SingleArticleError(RuntimeError):
    pass


def resolve_summary_provenance(*, article: BlogArticle, revision: ArticleRevision) -> SummaryProvenance:
    source_payload = revision.source_payload if isinstance(revision.source_payload, dict) else {}
    revision_summary = None
    for candidate in (
        source_payload.get("summary"),
        (source_payload.get("blog_article") or {}).get("summary") if isinstance(source_payload.get("blog_article"), dict) else None,
        (source_payload.get("raw_article") or {}).get("summary") if isinstance(source_payload.get("raw_article"), dict) else None,
    ):
        if isinstance(candidate, str) and candidate.strip():
            revision_summary = candidate.strip()
            break

    if revision_summary is not None:
        return SummaryProvenance(
            summary=revision_summary,
            source="article_revision_source_payload",
            article_revision_id=str(revision.article_revision_id),
            content_hash=revision.content_hash,
            available=True,
            aligned=True,
        )

    if article.content_hash == revision.content_hash and isinstance(article.summary, str) and article.summary.strip():
        return SummaryProvenance(
            summary=article.summary.strip(),
            source="blog_article_current",
            article_revision_id=str(revision.article_revision_id),
            content_hash=revision.content_hash,
            available=True,
            aligned=True,
        )

    return SummaryProvenance(
        summary=None,
        source="unavailable",
        article_revision_id=str(revision.article_revision_id),
        content_hash=revision.content_hash,
        available=False,
        aligned=False,
        reason="selected revision has no frozen summary",
    )


def build_article_structure_provenance(
    *,
    structure: ArticleStructure | None,
    prompt_run: PromptRun | None,
) -> ArticleStructureProvenance:
    if structure is None or prompt_run is None:
        return ArticleStructureProvenance(
            article_structure_id=None,
            article_revision_id=None,
            prompt_run_id=None,
            prompt_name=None,
            prompt_version=None,
            schema_name=None,
            schema_version=None,
            available=False,
        )
    return ArticleStructureProvenance(
        article_structure_id=str(structure.article_structure_id),
        article_revision_id=str(structure.article_revision_id) if structure.article_revision_id is not None else None,
        prompt_run_id=str(structure.prompt_run_id),
        prompt_name=prompt_run.prompt_name,
        prompt_version=prompt_run.prompt_version,
        schema_name=prompt_run.schema_name,
        schema_version=prompt_run.schema_version,
        available=True,
    )


class Stage3SingleArticleService:
    service_name = "stage3-single-article-service"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any],
        prompt_runtime_service: Stage3PromptRuntimeService | None = None,
        repository: Stage3SingleArticleRepository | None = None,
        regression_service: Any | None = None,
        governance_service: Any | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._prompt_runtime_service = prompt_runtime_service or Stage3PromptRuntimeService(
            session_scope_factory=session_scope_factory,
            model="gpt-5.4",
        )
        self._repository = repository or Stage3SingleArticleRepository()
        del regression_service, governance_service
        self._taxonomy_service = ExtractionTaxonomyService()

    async def get_journey(
        self,
        *,
        article_id: UUID,
        article_revision_id: UUID | None = None,
    ) -> ArticleJourney:
        async with self._session_scope_factory() as session:
            article = await self._repository.get_article(session, article_id=article_id)
            if article is None:
                raise Stage3SingleArticleError(f"article not found: {article_id}")

            revision = await self._repository.get_article_revision(
                session,
                article_id=article_id,
                article_revision_id=article_revision_id,
            )
            if revision is None:
                raise Stage3SingleArticleError("article revision not found")

            prompt_run, structure, candidates = await self._repository.get_prompt_run_bundle(
                session,
                article_id=article_id,
                article_revision_id=revision.article_revision_id,
            )

            if structure is None or prompt_run is None:
                return ArticleJourney(
                    status="partial",
                    article=article,
                    revision=revision,
                    prompt_run=None,
                    structure=None,
                    extraction_items=[],
                    eligibilities={},
                    rule_versions={},
                    summary_provenance=resolve_summary_provenance(article=article, revision=revision),
                    article_structure_provenance=build_article_structure_provenance(structure=None, prompt_run=None),
                    message="该文章尚未完成结构化分析。",
                )

            eligibilities = {item.extraction_item_id: eligibility_for(item) for item in candidates}
            rule_versions = {}
            for item in candidates:
                rule_version = await self._repository.get_rule_version_by_source_item(
                    session,
                    item_id=item.extraction_item_id,
                )
                if rule_version is not None:
                    rule_versions[item.extraction_item_id] = rule_version

            status: JourneyStatus = "ready" if candidates else "partial"
            message = None if candidates else "分析已完成，但当前没有可保留的分类抽取项。"
            return ArticleJourney(
                status=status,
                article=article,
                revision=revision,
                prompt_run=prompt_run,
                structure=structure,
                extraction_items=candidates,
                eligibilities=eligibilities,
                rule_versions=rule_versions,
                summary_provenance=resolve_summary_provenance(article=article, revision=revision),
                article_structure_provenance=build_article_structure_provenance(structure=structure, prompt_run=prompt_run),
                message=message,
            )

    async def run_analysis(
        self,
        *,
        article_id: UUID,
        article_revision_id: UUID | None = None,
    ) -> ArticleJourney:
        async with self._session_scope_factory() as session:
            article = await self._repository.get_article(session, article_id=article_id)
            if article is None:
                raise Stage3SingleArticleError(f"article not found: {article_id}")
            revision = await self._repository.get_article_revision(
                session,
                article_id=article_id,
                article_revision_id=article_revision_id,
            )
            if revision is None:
                raise Stage3SingleArticleError("article revision not found")

        try:
            await self._prompt_runtime_service.analyze_article(
                ArticlePromptInput(
                    article_id=article.id,
                    article_revision_id=revision.article_revision_id,
                    article_title=article.title,
                    article_content=revision.content_text,
                    article_content_hash=revision.content_hash,
                    source_url=article.source_url,
                    published_at=article.published_at,
                )
            )
        except PromptRuntimeError as exc:
            raise Stage3SingleArticleError(str(exc)) from exc

        return await self.get_journey(
            article_id=article_id,
            article_revision_id=revision.article_revision_id,
        )

    async def review_extraction_item(
        self,
        *,
        article_id: UUID,
        item_id: UUID,
        decision: HumanReviewDecision,
        actor_id: str,
        reason: str | None,
        article_revision_id: UUID | None = None,
    ) -> ArticleJourney:
        async with self._session_scope_factory() as session:
            article = await self._repository.get_article(session, article_id=article_id)
            if article is None:
                raise Stage3SingleArticleError(f"article not found: {article_id}")

            revision = await self._repository.get_article_revision(
                session,
                article_id=article_id,
                article_revision_id=article_revision_id,
            )
            if revision is None:
                raise Stage3SingleArticleError("article revision not found")

            prompt_run, structure, _ = await self._repository.get_prompt_run_bundle(
                session,
                article_id=article_id,
                article_revision_id=revision.article_revision_id,
            )
            if prompt_run is None or structure is None:
                raise Stage3SingleArticleError("analysis is not ready")

            item = await self._repository.get_extraction_item(
                session,
                item_id=item_id,
                article_structure_id=structure.article_structure_id,
            )
            if item is None:
                raise Stage3SingleArticleError("extraction item not found")

            if decision == "accept":
                try:
                    await self._taxonomy_service.accept_review(session, item=item, actor_id=actor_id)
                except ExtractionTaxonomyError as exc:
                    raise Stage3SingleArticleError(str(exc)) from exc
            else:
                await self._taxonomy_service.reject_review(session, item=item, actor_id=actor_id)

            if reason:
                provenance = dict(item.provenance or {})
                provenance["review_reason"] = reason
                item.provenance = provenance

        return await self.get_journey(
            article_id=article_id,
            article_revision_id=article_revision_id,
        )

    async def repair_rule_candidate(
        self,
        *,
        article_id: UUID,
        item_id: UUID,
        repaired_payload: dict[str, Any],
        source_quote: str,
        rationale: str,
        actor_id: str,
        article_revision_id: UUID | None = None,
    ) -> ArticleJourney:
        async with self._session_scope_factory() as session:
            revision = await self._repository.get_article_revision(
                session, article_id=article_id, article_revision_id=article_revision_id
            )
            if revision is None:
                raise Stage3SingleArticleError("article revision not found")
            _, structure, _ = await self._repository.get_prompt_run_bundle(
                session, article_id=article_id, article_revision_id=revision.article_revision_id
            )
            if structure is None:
                raise Stage3SingleArticleError("analysis is not ready")
            item = await self._repository.get_extraction_item(
                session, item_id=item_id, article_structure_id=structure.article_structure_id
            )
            if item is None:
                raise Stage3SingleArticleError("extraction item not found")
            try:
                await self._taxonomy_service.repair_candidate(
                    session,
                    item=item,
                    repaired_payload=repaired_payload,
                    source_quote=source_quote,
                    rationale=rationale,
                    actor_id=actor_id,
                )
            except (ExtractionTaxonomyError, ValueError) as exc:
                raise Stage3SingleArticleError(str(exc)) from exc
        return await self.get_journey(article_id=article_id, article_revision_id=revision.article_revision_id)

    async def promote_executable_item(
        self,
        *,
        article_id: UUID,
        item_id: UUID,
        actor_id: str,
        article_revision_id: UUID | None = None,
    ) -> ArticleJourney:
        async with self._session_scope_factory() as session:
            revision = await self._repository.get_article_revision(
                session, article_id=article_id, article_revision_id=article_revision_id
            )
            if revision is None:
                raise Stage3SingleArticleError("article revision not found")
            _, structure, _ = await self._repository.get_prompt_run_bundle(
                session, article_id=article_id, article_revision_id=revision.article_revision_id
            )
            if structure is None:
                raise Stage3SingleArticleError("analysis is not ready")
            item = await self._repository.get_extraction_item(
                session, item_id=item_id, article_structure_id=structure.article_structure_id
            )
            if item is None:
                raise Stage3SingleArticleError("extraction item not found")
            try:
                await self._taxonomy_service.promote_to_rule_version(
                    session, item=item, actor_id=actor_id
                )
            except ExtractionTaxonomyError as exc:
                raise Stage3SingleArticleError(str(exc)) from exc
        return await self.get_journey(article_id=article_id, article_revision_id=revision.article_revision_id)
