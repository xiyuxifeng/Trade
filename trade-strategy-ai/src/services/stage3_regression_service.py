from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import UUID

from src.llm.client import LLMError
from src.llm.runtime import LLMInvocationTrace
from src.models.stage2_canonical import PromptRun, RuleCandidate
from src.services.stage3_prompt_runtime_service import ArticlePromptInput, Stage3PromptRuntimeService
from src.services.stage3_regression_fixtures import (
    STAGE3_FIXED_SET_GATE_VERSION,
    STAGE3_FIXED_SET_MODEL,
    RegressionArticleFixture,
    get_stage3_fixed_regression_set,
)
from src.services.stage3_single_article_service import Stage3SingleArticleService


@dataclass(slots=True)
class RegressionArticleResult:
    article_id: str
    article_revision_id: str
    content_hash: str
    status: str
    cache_hit: bool
    repair_count: int
    automatic_review_statuses: list[str]
    summary_available: bool
    summary_source: str
    summary_aligned: bool
    failure_reason: str | None = None


@dataclass(slots=True)
class RegressionRunResult:
    status: str
    gate_version: str
    manifest: list[RegressionArticleFixture]
    article_results: list[RegressionArticleResult] = field(default_factory=list)
    semantic_failures: list[str] = field(default_factory=list)
    validation_failures: list[str] = field(default_factory=list)
    provider_failures: list[str] = field(default_factory=list)
    persistence_failures: list[str] = field(default_factory=list)
    processed_count: int = 0
    cached_count: int = 0
    repaired_count: int = 0
    human_attention_count: int = 0

    @classmethod
    def failed(
        cls,
        *,
        manifest: list[RegressionArticleFixture],
        gate_version: str,
        semantic_failures: list[str],
    ) -> "RegressionRunResult":
        return cls(
            status="failed",
            gate_version=gate_version,
            manifest=manifest,
            semantic_failures=semantic_failures,
        )


class FixedFixtureGateway:
    def __init__(self, fixtures: dict[UUID, RegressionArticleFixture]) -> None:
        self.fixtures = fixtures
        self.calls: list[tuple[str, UUID]] = []
        self.active_calls = 0
        self.max_active_calls = 0
        self._attempts: dict[tuple[str, UUID], int] = {}

    async def invoke_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str, model: str):  # noqa: ANN001
        del system_prompt
        payload = json.loads(user_prompt)
        revision_id = UUID(payload.get("article_revision_id") or payload.get("article", {}).get("article_revision_id"))
        fixture = self.fixtures[revision_id]
        key = (prompt_name, revision_id)
        attempt = self._attempts.get(key, 0)
        self._attempts[key] = attempt + 1
        self.calls.append((prompt_name, revision_id))

        if prompt_name == "article_analysis_v1" and fixture.provider_failures_before_success > attempt:
            raise LLMError("retry please", retryable=True, code="network")

        self.active_calls += 1
        self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            if prompt_name == "article_analysis_repair_v1":
                data = fixture.build_repair_payload()
            else:
                data = fixture.build_payload(valid=not fixture.exercise_repair)
        finally:
            self.active_calls -= 1

        return LLMInvocationTrace(
            provider="fixture-provider",
            model=model,
            data=data,
            raw_output=data,
            raw_output_text=json.dumps(data, ensure_ascii=False, sort_keys=True),
            token_usage={"prompt_tokens": 11, "completion_tokens": 29, "total_tokens": 40},
            cost_amount=None,
            cost_currency=None,
        )


class Stage3RegressionService:
    service_name = "stage3-regression-service"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any],
        manifest: list[RegressionArticleFixture] | None = None,
        gateway: FixedFixtureGateway | None = None,
        model: str = STAGE3_FIXED_SET_MODEL,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._manifest = manifest or get_stage3_fixed_regression_set()
        self._gateway = gateway or FixedFixtureGateway({item.article_revision_id: item for item in self._manifest})
        self._model = model
        self._runtime_service = Stage3PromptRuntimeService(
            session_scope_factory=session_scope_factory,
            gateway=self._gateway,
            model=model,
        )
        self._single_article_service = Stage3SingleArticleService(
            session_scope_factory=session_scope_factory,
            prompt_runtime_service=self._runtime_service,
        )

    async def run_fixed_set(self) -> RegressionRunResult:
        result = RegressionRunResult(status="passed", gate_version=STAGE3_FIXED_SET_GATE_VERSION, manifest=self._manifest)
        for fixture in self._manifest:
            try:
                journey_result = await self._run_fixture(fixture)
                result.article_results.append(journey_result)
                result.processed_count += 1
                result.cached_count += int(journey_result.cache_hit)
                result.repaired_count += journey_result.repair_count
                result.human_attention_count += int("needs_human_review" in journey_result.automatic_review_statuses)
            except AssertionError as exc:
                result.semantic_failures.append(f"{fixture.article_revision_id}: {exc}")
            except LLMError as exc:
                result.provider_failures.append(f"{fixture.article_revision_id}: {exc}")
            except Exception as exc:  # pragma: no cover - surfaced in tests as persistence/runtime failure
                result.persistence_failures.append(f"{fixture.article_revision_id}: {exc}")

        if result.semantic_failures or result.validation_failures or result.provider_failures or result.persistence_failures:
            result.status = "failed"
        return result

    async def _run_fixture(self, fixture: RegressionArticleFixture) -> RegressionArticleResult:
        async with self._session_scope_factory() as session:
            article = await self._single_article_service._repository.get_article(session, article_id=fixture.article_id)  # noqa: SLF001
            revision = await self._single_article_service._repository.get_article_revision(  # noqa: SLF001
                session,
                article_id=fixture.article_id,
                article_revision_id=fixture.article_revision_id,
            )
            assert article is not None, "article record missing"
            assert revision is not None, "article revision missing"
            assert revision.content_hash == fixture.content_hash, "content hash mismatch"

        runtime_result = await self._runtime_service.analyze_article(
            ArticlePromptInput(
                article_id=fixture.article_id,
                article_revision_id=fixture.article_revision_id,
                article_title=article.title,
                article_content=revision.content_text,
                article_content_hash=revision.content_hash,
                source_url=article.source_url,
                published_at=article.published_at,
            )
        )
        journey = await self._single_article_service.get_journey(
            article_id=fixture.article_id,
            article_revision_id=fixture.article_revision_id,
        )
        self._assert_semantics(fixture, journey)
        return RegressionArticleResult(
            article_id=str(fixture.article_id),
            article_revision_id=str(fixture.article_revision_id),
            content_hash=fixture.content_hash,
            status="passed",
            cache_hit=runtime_result.cache_hit,
            repair_count=runtime_result.repair_count,
            automatic_review_statuses=sorted({item.status for item in journey.automatic_reviews.values()}),
            summary_available=journey.summary_provenance.available,
            summary_source=journey.summary_provenance.source,
            summary_aligned=journey.summary_provenance.aligned,
        )

    def _assert_semantics(self, fixture: RegressionArticleFixture, journey) -> None:  # noqa: ANN001
        assert str(journey.revision.article_revision_id) == str(fixture.article_revision_id), "revision mismatch"
        assert journey.revision.content_hash == fixture.content_hash, "content hash provenance mismatch"

        summary = journey.summary_provenance
        expected_summary = fixture.summary_expectation
        assert summary.available == expected_summary.available, "summary availability mismatch"
        assert summary.source == expected_summary.source, "summary source mismatch"
        assert summary.aligned == expected_summary.aligned, "summary alignment mismatch"
        assert summary.article_revision_id == str(fixture.article_revision_id), "summary revision provenance mismatch"
        assert summary.content_hash == fixture.content_hash, "summary content hash provenance mismatch"
        if expected_summary.available and expected_summary.contains:
            assert summary.summary is not None and expected_summary.contains in summary.summary, "summary text mismatch"

        assertions = fixture.semantic_assertions
        if assertions.article_structure_provenance_required:
            assert journey.article_structure_provenance.available is True, "article structure provenance missing"
            assert journey.article_structure_provenance.article_revision_id == str(fixture.article_revision_id), "structure provenance revision mismatch"
            assert journey.article_structure_provenance.prompt_name == fixture.prompt_name, "prompt name mismatch"
            assert journey.article_structure_provenance.prompt_version == fixture.prompt_version, "prompt version mismatch"
            assert journey.article_structure_provenance.schema_name == fixture.schema_name, "schema name mismatch"
            assert journey.article_structure_provenance.schema_version == fixture.schema_version, "schema version mismatch"

        assert journey.structure is not None, "article structure missing"
        structure_payload = journey.structure.payload or {}
        method_tags = structure_payload.get("method_tags", [])
        for tag in assertions.method_tags:
            assert tag in method_tags, f"missing method tag: {tag}"

        key_claims = [item.get("claim", "") for item in structure_payload.get("key_claims", [])]
        for fact in assertions.explicit_facts_contains:
            assert any(fact in claim for claim in key_claims), f"missing explicit fact: {fact}"

        article_hypotheses = [
            item.get("hypothesis", "")
            for item in (structure_payload.get("market_state", {}) or {}).get("inferred_hypotheses", [])
        ]
        for hypothesis in assertions.hypotheses_contains:
            assert any(hypothesis in item for item in article_hypotheses), f"missing hypothesis: {hypothesis}"

        missing_blob = json.dumps(journey.structure.missing_fields or {}, ensure_ascii=False)
        for missing in assertions.missing_fields_contains:
            assert missing in missing_blob, f"missing missing-field marker: {missing}"

        assert assertions.candidate_rule_count_range[0] <= len(journey.candidates) <= assertions.candidate_rule_count_range[1], "candidate count mismatch"

        dependency_blob = json.dumps(structure_payload.get("data_dependencies", []), ensure_ascii=False)
        dependency_blob += json.dumps([candidate.data_dependencies for candidate in journey.candidates], ensure_ascii=False)
        for dependency in assertions.data_dependencies_contains:
            assert dependency in dependency_blob, f"missing dependency: {dependency}"

        backtestability_statuses = [candidate.backtestability_status for candidate in journey.candidates]
        for status in assertions.backtestability_statuses:
            assert status in backtestability_statuses, f"missing backtestability status: {status}"

        automatic_review_statuses = {review.status for review in journey.automatic_reviews.values()}
        for status in assertions.automatic_review_statuses:
            assert status in automatic_review_statuses, f"missing automatic review status: {status}"

        if assertions.evidence_required:
            for candidate in journey.candidates:
                evidence = (candidate.evidence_json or {}).get("evidence", [])
                assert evidence, "candidate evidence missing"

        market_state_status = (structure_payload.get("market_state") or {}).get("status")
        assert market_state_status == assertions.market_state_status, "market state status mismatch"

        if assertions.kaipan_dependency:
            assert "kaipan" in dependency_blob.lower(), "expected Kaipan dependency"

        assert journey.rule_versions == {}, "rule versions must not be created during regression"
