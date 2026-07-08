from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal, TYPE_CHECKING
from uuid import UUID

from src.common.stage2_writer_routing import canonical_write_scope
from src.db.repositories.stage3_single_article_repository import Stage3SingleArticleRepository
from src.domain.enums import FormalLifecycleState
from src.llm.runtime import PromptRuntimeError
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import ArticleRevision, ArticleStructure, PromptRun, RuleCandidate, RuleVersion
from src.services.rule_governance_service import CandidateGovernanceAssessment, RuleGovernanceService
from src.services.rule_lifecycle_service import RuleLifecycleService, RuleLifecycleTransitionBlockedError
from src.services.stage3_prompt_runtime_service import ArticlePromptInput, Stage3PromptRuntimeService

if TYPE_CHECKING:
    from src.services.stage3_regression_service import Stage3RegressionService


AutomaticReviewStatus = Literal["pending_backtest", "needs_human_review", "suggested_reject"]
JourneyStatus = Literal["ready", "partial", "empty"]
HumanReviewDecision = Literal["approve", "reject"]


SummarySource = Literal["article_revision_source_payload", "blog_article_current", "unavailable"]


@dataclass(frozen=True)
class AutomaticReviewResult:
    status: AutomaticReviewStatus
    reasons: list[str]
    risk_level: Literal["low", "medium", "high"]
    backtestability_status: str
    kaipan_dependency: bool
    market_state_status: str


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
    candidates: list[RuleCandidate]
    automatic_reviews: dict[UUID, AutomaticReviewResult]
    rule_versions: dict[UUID, RuleVersion]
    governance_assessments: dict[UUID, CandidateGovernanceAssessment]
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


def _contains_kaipan_dependency(values: Any) -> bool:
    if isinstance(values, str):
        return "kaipan" in values.lower()
    if isinstance(values, list):
        return any(_contains_kaipan_dependency(item) for item in values)
    if isinstance(values, dict):
        return any(_contains_kaipan_dependency(item) for item in values.values())
    return False


LIGHT_AMBIGUOUS_TERM_MARKERS = (
    "强势",
    "明显放量",
    "放量",
    "企稳",
    "附近",
    "偏强",
    "博弈",
)

HEAVY_AMBIGUOUS_TERM_MARKERS = (
    "止损",
    "stop_loss",
    "stop loss",
    "止盈",
    "take_profit",
    "take profit",
    "仓位",
    "position",
    "sizing",
    "市场状态",
    "market_state",
    "market regime",
    "主观判断",
    "人工判断",
    "看情况",
)

CORE_MISSING_FIELD_MARKERS = (
    "止损",
    "stop_loss",
    "stop loss",
    "止盈",
    "take_profit",
    "take profit",
    "仓位",
    "position",
    "sizing",
    "阈值",
    "threshold",
    "明确阈值",
    "entry",
    "exit",
    "买入",
    "卖出",
    "触发条件",
    "核心参数",
)


def _normalize_string_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        value = values.strip()
        return [value] if value else []
    if isinstance(values, dict):
        return [
            str(key)
            for key, value in values.items()
            if value not in (None, False, "", [], {})
        ]
    if isinstance(values, list):
        normalized: list[str] = []
        for value in values:
            if isinstance(value, str):
                text = value.strip()
            else:
                text = str(value).strip()
            if text:
                normalized.append(text)
        return normalized
    text = str(values).strip()
    return [text] if text else []


def _matches_marker(value: str, markers: tuple[str, ...]) -> bool:
    normalized = value.strip().lower()
    return any(marker.lower() in normalized for marker in markers)


def _split_ambiguous_terms(values: Any) -> tuple[list[str], list[str]]:
    light_terms: list[str] = []
    heavy_terms: list[str] = []
    for term in _normalize_string_list(values):
        if _matches_marker(term, HEAVY_AMBIGUOUS_TERM_MARKERS):
            heavy_terms.append(term)
        elif _matches_marker(term, LIGHT_AMBIGUOUS_TERM_MARKERS):
            light_terms.append(term)
        else:
            heavy_terms.append(term)
    return light_terms, heavy_terms


def _split_missing_fields(values: Any) -> tuple[list[str], list[str]]:
    core_fields: list[str] = []
    non_core_fields: list[str] = []
    for field in _normalize_string_list(values):
        if _matches_marker(field, CORE_MISSING_FIELD_MARKERS):
            core_fields.append(field)
        else:
            non_core_fields.append(field)
    return core_fields, non_core_fields


def determine_automatic_review(candidate: RuleCandidate) -> AutomaticReviewResult:
    payload = candidate.canonical_payload or {}
    quantification = payload.get("quantification") or {}
    condition = payload.get("condition") or {}
    action = payload.get("action") or {}
    evidence = payload.get("evidence") or []
    market_state = payload.get("market_state_applicability") or {}
    risk_controls = payload.get("risk_controls") or []
    data_dependencies = payload.get("data_dependencies") or []

    kaipan_dependency = _contains_kaipan_dependency(data_dependencies)
    market_state_status = str(market_state.get("status") or "not_declared")
    backtestability_status = str(candidate.backtestability_status)

    reject_reasons: list[str] = []
    if not evidence:
        reject_reasons.append("缺少原文证据")
    if not condition:
        reject_reasons.append("缺少规则条件")
    if not action:
        reject_reasons.append("缺少规则动作")
    if backtestability_status == "not_executable":
        reject_reasons.append("当前不可回测")

    if reject_reasons:
        return AutomaticReviewResult(
            status="suggested_reject",
            reasons=reject_reasons,
            risk_level="high",
            backtestability_status=backtestability_status,
            kaipan_dependency=kaipan_dependency,
            market_state_status=market_state_status,
        )

    light_ambiguous_terms, heavy_ambiguous_terms = _split_ambiguous_terms(quantification.get("ambiguous_terms"))
    core_missing_fields, non_core_missing_fields = _split_missing_fields(quantification.get("missing_fields"))
    manual_review_required = bool(quantification.get("manual_review_required"))

    review_reasons: list[str] = []
    if heavy_ambiguous_terms:
        review_reasons.append(f"存在重度模糊词：{', '.join(heavy_ambiguous_terms)}")
    if core_missing_fields:
        review_reasons.append(f"仍有核心缺失字段：{', '.join(core_missing_fields)}")
    if kaipan_dependency:
        review_reasons.append("依赖 Kaipan 数据")
    if backtestability_status not in {"executable", "partially_executable"}:
        review_reasons.append("当前不满足直接回测条件")

    has_relaxable_uncertainty = bool(light_ambiguous_terms or non_core_missing_fields or risk_controls)
    if manual_review_required and not has_relaxable_uncertainty:
        review_reasons.append("量化条件仍需人工确认")
    elif manual_review_required:
        review_reasons.append("抽取层标记需人工复核，但未命中强风险门禁，保留追踪")

    if review_reasons:
        return AutomaticReviewResult(
            status="needs_human_review",
            reasons=review_reasons,
            risk_level="medium",
            backtestability_status=backtestability_status,
            kaipan_dependency=kaipan_dependency,
            market_state_status=market_state_status,
        )

    reasons = ["证据、条件和动作完整，可进入待回测"]
    if light_ambiguous_terms:
        reasons.append(f"含轻度模糊词：{', '.join(light_ambiguous_terms)}；保留追踪但不单独触发人工")
    if non_core_missing_fields:
        reasons.append(f"含非核心缺失字段：{', '.join(non_core_missing_fields)}；保留追踪但不单独触发人工")
    if risk_controls:
        reasons.append("包含风险控制条目；未发现缺失核心参数，保留追踪")
    if manual_review_required:
        reasons.append("抽取层标记需人工复核，但仅命中可放行不确定性")
    if backtestability_status == "partially_executable":
        reasons.append("当前为 partially_executable；强风险门禁未命中，允许进入待回测队列")

    return AutomaticReviewResult(
        status="pending_backtest",
        reasons=reasons,
        risk_level="low",
        backtestability_status=backtestability_status,
        kaipan_dependency=kaipan_dependency,
        market_state_status=market_state_status,
    )


class Stage3SingleArticleService:
    service_name = "stage3-single-article-service"

    def __init__(
        self,
        *,
        session_scope_factory,
        prompt_runtime_service: Stage3PromptRuntimeService | None = None,
        repository: Stage3SingleArticleRepository | None = None,
        regression_service: Any | None = None,
        governance_service: RuleGovernanceService | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._prompt_runtime_service = prompt_runtime_service or Stage3PromptRuntimeService(
            session_scope_factory=session_scope_factory,
            model="gpt-5.4",
        )
        self._repository = repository or Stage3SingleArticleRepository()
        self._governance_service = governance_service or RuleGovernanceService(
            regression_service=regression_service,
        )
        self._lifecycle_service = RuleLifecycleService(
            session_scope_factory=session_scope_factory,
            regression_service=regression_service,
            governance_service=self._governance_service,
        )

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
                    candidates=[],
                    automatic_reviews={},
                    rule_versions={},
                    governance_assessments={},
                    summary_provenance=resolve_summary_provenance(article=article, revision=revision),
                    article_structure_provenance=build_article_structure_provenance(structure=None, prompt_run=None),
                    message="该文章尚未完成结构化分析。",
                )

            automatic_reviews = {
                candidate.rule_candidate_id: determine_automatic_review(candidate)
                for candidate in candidates
            }
            governance_assessments = {
                candidate.rule_candidate_id: await self._governance_service.assess_candidate(session, candidate=candidate)
                for candidate in candidates
            }
            rule_versions = {}
            for candidate in candidates:
                rule_version = await self._repository.get_rule_version_by_source_candidate(
                    session,
                    candidate_id=candidate.rule_candidate_id,
                )
                if rule_version is not None:
                    rule_versions[candidate.rule_candidate_id] = rule_version

            status: JourneyStatus = "ready" if candidates else "partial"
            message = None if candidates else "分析已完成，但当前没有候选规则。"
            return ArticleJourney(
                status=status,
                article=article,
                revision=revision,
                prompt_run=prompt_run,
                structure=structure,
                candidates=candidates,
                automatic_reviews=automatic_reviews,
                rule_versions=rule_versions,
                governance_assessments=governance_assessments,
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

    async def review_candidate(
        self,
        *,
        article_id: UUID,
        candidate_id: UUID,
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

            candidate = await self._repository.get_rule_candidate(
                session,
                candidate_id=candidate_id,
                article_structure_id=structure.article_structure_id,
            )
            if candidate is None:
                raise Stage3SingleArticleError("rule candidate not found")

            if decision == "approve":
                try:
                    await self._lifecycle_service.approve_candidate(
                        candidate_id=candidate.rule_candidate_id,
                        actor_id=actor_id,
                        reason=reason,
                        correlation_id=str(candidate.rule_candidate_id),
                    )
                except RuleLifecycleTransitionBlockedError as exc:
                    raise Stage3SingleArticleError(str(exc)) from exc
            else:
                try:
                    await self._lifecycle_service.reject_candidate(
                        candidate_id=candidate.rule_candidate_id,
                        actor_type="human",
                        actor_id=actor_id,
                        reason=reason,
                        correlation_id=str(candidate.rule_candidate_id),
                    )
                except RuleLifecycleTransitionBlockedError as exc:
                    raise Stage3SingleArticleError(str(exc)) from exc

        return await self.get_journey(
            article_id=article_id,
            article_revision_id=article_revision_id,
        )
