from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from src.common.stage2_writer_routing import canonical_write_scope
from src.db.repositories.stage3_single_article_repository import Stage3SingleArticleRepository
from src.domain.enums import FormalLifecycleState
from src.llm.runtime import PromptRuntimeError
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import ArticleRevision, ArticleStructure, PromptRun, RuleCandidate, RuleVersion
from src.services.stage3_prompt_runtime_service import ArticlePromptInput, Stage3PromptRuntimeService


AutomaticReviewStatus = Literal["pending_backtest", "needs_human_review", "suggested_reject"]
JourneyStatus = Literal["ready", "partial", "empty"]
HumanReviewDecision = Literal["approve", "reject"]


@dataclass(frozen=True)
class AutomaticReviewResult:
    status: AutomaticReviewStatus
    reasons: list[str]
    risk_level: Literal["low", "medium", "high"]
    backtestability_status: str
    kaipan_dependency: bool
    market_state_status: str


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
    message: str | None = None


class Stage3SingleArticleError(RuntimeError):
    pass


def _contains_kaipan_dependency(values: Any) -> bool:
    if isinstance(values, str):
        return "kaipan" in values.lower()
    if isinstance(values, list):
        return any(_contains_kaipan_dependency(item) for item in values)
    if isinstance(values, dict):
        return any(_contains_kaipan_dependency(item) for item in values.values())
    return False


def determine_automatic_review(candidate: RuleCandidate) -> AutomaticReviewResult:
    payload = candidate.canonical_payload or {}
    quantification = payload.get("quantification") or {}
    condition = payload.get("condition") or {}
    action = payload.get("action") or {}
    evidence = payload.get("evidence") or []
    market_state = payload.get("market_state_applicability") or {}
    risk_controls = payload.get("risk_controls") or []
    data_dependencies = payload.get("data_dependencies") or []

    reasons: list[str] = []
    if not evidence:
        reasons.append("缺少原文证据")
    if not condition:
        reasons.append("缺少规则条件")
    if not action:
        reasons.append("缺少规则动作")

    if reasons:
        return AutomaticReviewResult(
            status="suggested_reject",
            reasons=reasons,
            risk_level="high",
            backtestability_status=candidate.backtestability_status,
            kaipan_dependency=_contains_kaipan_dependency(data_dependencies),
            market_state_status=str(market_state.get("status") or "not_declared"),
        )

    review_reasons: list[str] = []
    if quantification.get("manual_review_required"):
        review_reasons.append("量化条件仍需人工确认")
    if quantification.get("missing_fields"):
        review_reasons.append("仍有缺失字段")
    if quantification.get("ambiguous_terms"):
        review_reasons.append("存在模糊词")
    if risk_controls:
        review_reasons.append("包含风险控制条目")
    if _contains_kaipan_dependency(data_dependencies):
        review_reasons.append("依赖 Kaipan 数据")
    if candidate.backtestability_status != "executable":
        review_reasons.append("当前不满足直接回测条件")

    if review_reasons:
        return AutomaticReviewResult(
            status="needs_human_review",
            reasons=review_reasons,
            risk_level="medium",
            backtestability_status=candidate.backtestability_status,
            kaipan_dependency=_contains_kaipan_dependency(data_dependencies),
            market_state_status=str(market_state.get("status") or "not_declared"),
        )

    return AutomaticReviewResult(
        status="pending_backtest",
        reasons=["证据、条件和动作完整，可进入待回测"],
        risk_level="low",
        backtestability_status=candidate.backtestability_status,
        kaipan_dependency=False,
        market_state_status=str(market_state.get("status") or "not_declared"),
    )


class Stage3SingleArticleService:
    service_name = "stage3-single-article-service"

    def __init__(
        self,
        *,
        session_scope_factory,
        prompt_runtime_service: Stage3PromptRuntimeService | None = None,
        repository: Stage3SingleArticleRepository | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._prompt_runtime_service = prompt_runtime_service or Stage3PromptRuntimeService(
            session_scope_factory=session_scope_factory,
            model="gpt-5.4",
        )
        self._repository = repository or Stage3SingleArticleRepository()

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
                    message="该文章尚未完成结构化分析。",
                )

            automatic_reviews = {
                candidate.rule_candidate_id: determine_automatic_review(candidate)
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

            review = determine_automatic_review(candidate)
            before_state = str(candidate.review_state)
            after_snapshot = {
                "automatic_review_status": review.status,
                "reason": reason,
                "review_state": "approved" if decision == "approve" else "rejected",
            }

            with canonical_write_scope("rule_version", self.service_name):
                if decision == "approve":
                    payload = candidate.canonical_payload or {}
                    await self._repository.approve_candidate(
                        session,
                        candidate=candidate,
                        actor_id=actor_id,
                        reason=reason,
                        formal_lifecycle_state=FormalLifecycleState.draft,
                        quality_status="partial" if review.status != "pending_backtest" else "complete",
                        business_key=f"stage3:{candidate.candidate_fingerprint}",
                        title=str(payload.get("title") or f"candidate-{candidate.candidate_index}"),
                        description=str(payload.get("description")) if payload.get("description") is not None else None,
                        schema_version="rule_v1",
                        instrument_scope={"instrument_focus": payload.get("instrument_focus") or []},
                        condition_json=payload.get("condition") or {},
                        action_json=payload.get("action") or {},
                        parameter_json={
                            "timeframe": payload.get("timeframe"),
                            "holding_period": payload.get("holding_period"),
                            "risk_controls": payload.get("risk_controls") or [],
                        },
                        data_dependencies=candidate.data_dependencies or {},
                        evidence_json=candidate.evidence_json or {},
                        after_review_snapshot=after_snapshot,
                    )
                else:
                    await self._repository.reject_candidate(
                        session,
                        candidate=candidate,
                        actor_id=actor_id,
                        reason=reason,
                        before_state=before_state,
                        after_review_snapshot=after_snapshot,
                    )

        return await self.get_journey(
            article_id=article_id,
            article_revision_id=article_revision_id,
        )
