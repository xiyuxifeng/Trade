from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import asyncio
from uuid import UUID

import pytest

from src.llm.runtime import LLMInvocationTrace, PromptRuntimeError
from src.services.stage3_prompt_runtime_service import (
    ArticlePromptInput,
    Stage3PromptRuntimeService,
)


@dataclass
class _FakePromptRun:
    prompt_run_id: UUID
    prompt_name: str
    retry_count: int
    validation_state: str


@dataclass
class _FakeArticleStructure:
    article_structure_id: UUID
    schema_version: str
    payload: dict


@dataclass
class _FakeRuleCandidate:
    rule_candidate_id: UUID


class _FakePromptRunRepository:
    def __init__(self) -> None:
        self.by_identity: dict[tuple[str, str, str, str, str, int], tuple[_FakePromptRun, _FakeArticleStructure, list[dict]]] = {}
        self.saved_runs: list[_FakePromptRun] = []

    async def get_cached_result(
        self,
        session,
        *,
        prompt_name: str,
        prompt_version: str,
        schema_version: str,
        model: str,
        input_hash: str,
        retry_count: int,
    ):
        del session
        exact = self.by_identity.get((prompt_name, prompt_version, schema_version, model, input_hash, retry_count))
        if exact is not None:
            return exact
        for key, value in self.by_identity.items():
            if key[:5] == (prompt_name, prompt_version, schema_version, model, input_hash):
                return value
        return None

    async def save_run(self, session, run):
        del session
        saved = _FakePromptRun(
            prompt_run_id=run.prompt_run_id,
            prompt_name=run.prompt_name,
            retry_count=run.retry_count,
            validation_state=str(run.validation_state),
        )
        for index, existing in enumerate(self.saved_runs):
            if existing.prompt_run_id == saved.prompt_run_id:
                self.saved_runs[index] = saved
                return run
        self.saved_runs.append(saved)
        return run


class _FakeArticleRepository:
    def __init__(self, prompt_runs: _FakePromptRunRepository | None = None, identity: str | None = None) -> None:
        self.saved = []
        self.prompt_runs = prompt_runs
        self.identity = identity

    async def save_structure_with_candidates(self, session, *, structure, candidates):
        del session
        self.saved.append((structure, candidates))
        if self.prompt_runs is not None and self.identity is not None and self.prompt_runs.saved_runs:
            latest_run = self.prompt_runs.saved_runs[-1]
            self.prompt_runs.by_identity[(
                "article_analysis_v1",
                "article_analysis_v1",
                "article_analysis_v1",
                "test-model",
                self.identity,
                latest_run.retry_count,
            )] = (latest_run, structure, candidates)
        return structure, candidates


class _FakeSessionScope:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeGateway:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    async def invoke_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str, model: str) -> LLMInvocationTrace:
        del system_prompt, user_prompt
        self.calls.append(prompt_name)
        payload = self._responses.pop(0)
        return LLMInvocationTrace(
            provider="test-provider",
            model=model,
            data=payload,
            raw_output=payload,
            raw_output_text=str(payload),
            token_usage={"total_tokens": 12},
            cost_amount=None,
            cost_currency=None,
        )


class _SlowGateway(_FakeGateway):
    async def invoke_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str, model: str) -> LLMInvocationTrace:
        await asyncio.sleep(0.01)
        return await super().invoke_json(
            prompt_name=prompt_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
        )


def _article_input() -> ArticlePromptInput:
    return ArticlePromptInput(
        article_id=UUID("11111111-1111-1111-1111-111111111111"),
        article_revision_id=UUID("22222222-2222-2222-2222-222222222222"),
        article_title="测试文章",
        article_content="文章明确说到竞价强势时关注放量突破。",
        source_url="https://example.com/article",
        published_at=datetime(2026, 6, 15, 9, 30, tzinfo=UTC),
    )


def _valid_article_analysis_payload() -> dict:
    return {
        "prompt_version": "article_analysis_v1",
        "schema_version": "article_analysis_v1",
        "classification": {"article_type": "rule", "confidence": 0.9, "evidence": ["竞价强势"]},
        "concept_extraction": {
            "prompt_version": "concept_extraction_v1",
            "schema_version": "concept_v1",
            "concepts": [{"name": "放量突破", "normalized_name": "放量突破", "type": "pattern", "confidence": 0.8, "evidence": ["放量突破"]}],
            "trading_symbols": [],
            "indicators": [],
            "chart_patterns": [],
            "market_themes": [],
            "risk_concepts": [],
            "data_dependencies": ["ohlcv_1d"],
            "sentiment": {"score": 0.0, "confidence": 0.0},
            "warnings": [],
        },
        "article_structure": {
            "prompt_version": "article_structure_extraction_v1",
            "schema_version": "article_structure_v1",
            "article_id": "11111111-1111-1111-1111-111111111111",
            "author_id": "author-1",
            "published_at": "2026-06-15T09:30:00Z",
            "article_type": "rule",
            "method_tags": ["竞价"],
            "analysis_dimensions": ["price"],
            "instrument_focus": ["stock"],
            "holding_period": {"value": "intraday", "source": "explicit", "confidence": 0.9, "evidence": ["竞价"]},
            "entry_patterns": ["放量突破"],
            "exit_patterns": [],
            "risk_concepts": [],
            "data_dependencies": ["ohlcv_1d"],
            "market_state": {"status": "not_declared", "explicit_conditions": [], "inferred_hypotheses": []},
            "key_claims": [{"claim": "竞价强势时关注放量突破", "claim_type": "entry", "source": "explicit", "confidence": 0.9, "evidence": ["竞价强势时关注放量突破"]}],
            "article_quality": {"information_density": "high", "quantifiability": "medium", "duplicate_risk": "low", "needs_manual_review": False, "warnings": []},
        },
        "rule_extraction": {
            "prompt_version": "rule_extraction_v1",
            "schema_version": "rule_v1",
            "strategy_rules": [{
                "rule_key": "rule-1",
                "title": "竞价放量突破",
                "rule_type": "entry",
                "instrument_focus": ["stock"],
                "timeframe": "5m",
                "holding_period": "intraday",
                "condition": {"logic": "single", "clauses": [{"field": "volume", "operator": "gt", "value": 1, "unit": None, "lookback": None, "raw_expression": "放量"}]},
                "action": {"type": "enter", "side": "buy", "price_reference": "market"},
                "risk_controls": [],
                "data_dependencies": ["ohlcv_1d"],
                "market_state_applicability": {"status": "not_declared", "explicit_conditions": [], "inferred_hypotheses": []},
                "quantification": {"status": "partially_executable", "missing_fields": ["threshold"], "ambiguous_terms": ["放量"], "manual_review_required": True},
                "confidence": 0.8,
                "evidence": [{"quote": "放量突破", "supports": "condition"}],
                "source_article_id": "11111111-1111-1111-1111-111111111111",
            }],
        },
        "explicit_preconditions": {
            "prompt_version": "explicit_precondition_extraction_v1",
            "schema_version": "explicit_precondition_v1",
            "status": "not_declared",
            "preconditions": [],
            "warnings": [],
        },
        "quality": {"needs_repair": False, "repair_reasons": [], "warnings": []},
    }


@pytest.mark.asyncio
async def test_runtime_uses_exactly_one_main_call_when_output_is_valid() -> None:
    gateway = _FakeGateway([_valid_article_analysis_payload()])
    prompt_runs = _FakePromptRunRepository()
    article_repo = _FakeArticleRepository()
    service = Stage3PromptRuntimeService(
        session_scope_factory=lambda: _FakeSessionScope(),
        gateway=gateway,
        prompt_run_repository=prompt_runs,
        article_analysis_repository=article_repo,
        model="test-model",
    )

    result = await service.analyze_article(_article_input())

    assert gateway.calls == ["article_analysis_v1"]
    assert result.repair_count == 0
    assert len(article_repo.saved) == 1
    assert prompt_runs.saved_runs[0].prompt_name == "article_analysis_v1"


@pytest.mark.asyncio
async def test_runtime_uses_at_most_one_targeted_repair_call() -> None:
    invalid = _valid_article_analysis_payload()
    del invalid["rule_extraction"]["strategy_rules"][0]["title"]
    repaired = {
        "prompt_version": "article_analysis_repair_v1",
        "patched_fields": {"rule_extraction.strategy_rules.0.title": "竞价放量突破"},
        "unresolved_errors": [],
        "warnings": [],
    }
    gateway = _FakeGateway([invalid, repaired])
    prompt_runs = _FakePromptRunRepository()
    article_repo = _FakeArticleRepository()
    service = Stage3PromptRuntimeService(
        session_scope_factory=lambda: _FakeSessionScope(),
        gateway=gateway,
        prompt_run_repository=prompt_runs,
        article_analysis_repository=article_repo,
        model="test-model",
    )

    result = await service.analyze_article(_article_input())

    assert gateway.calls == ["article_analysis_v1", "article_analysis_repair_v1"]
    assert result.repair_count == 1
    assert [run.prompt_name for run in prompt_runs.saved_runs] == [
        "article_analysis_v1",
        "article_analysis_repair_v1",
    ]


@pytest.mark.asyncio
async def test_runtime_rejects_second_repair_attempt() -> None:
    invalid = _valid_article_analysis_payload()
    del invalid["classification"]["article_type"]
    unresolved = {
        "prompt_version": "article_analysis_repair_v1",
        "patched_fields": {},
        "unresolved_errors": ["classification.article_type"],
        "warnings": [],
    }
    gateway = _FakeGateway([invalid, unresolved])
    service = Stage3PromptRuntimeService(
        session_scope_factory=lambda: _FakeSessionScope(),
        gateway=gateway,
        prompt_run_repository=_FakePromptRunRepository(),
        article_analysis_repository=_FakeArticleRepository(),
        model="test-model",
    )

    with pytest.raises(PromptRuntimeError):
        await service.analyze_article(_article_input())

    assert gateway.calls == ["article_analysis_v1", "article_analysis_repair_v1"]


@pytest.mark.asyncio
async def test_runtime_cache_hit_suppresses_duplicate_provider_call() -> None:
    cached_payload = _valid_article_analysis_payload()
    prompt_runs = _FakePromptRunRepository()
    prompt_runs.by_identity[(
        "article_analysis_v1",
        "article_analysis_v1",
        "article_analysis_v1",
        "test-model",
        "cached-hash",
        0,
    )] = (
        _FakePromptRun(prompt_run_id=UUID("44444444-4444-4444-4444-444444444444"), prompt_name="article_analysis_v1", retry_count=0, validation_state="valid"),
        _FakeArticleStructure(schema_version="article_analysis_v1", article_structure_id=UUID("33333333-3333-3333-3333-333333333333"), payload=cached_payload["article_structure"]),
        [_FakeRuleCandidate(rule_candidate_id=UUID("55555555-5555-5555-5555-555555555555"))],
    )
    gateway = _FakeGateway([])
    service = Stage3PromptRuntimeService(
        session_scope_factory=lambda: _FakeSessionScope(),
        gateway=gateway,
        prompt_run_repository=prompt_runs,
        article_analysis_repository=_FakeArticleRepository(),
        model="test-model",
        identity_hasher=lambda article_input, spec, model: "cached-hash",
    )

    result = await service.analyze_article(_article_input())

    assert result.cache_hit is True
    assert gateway.calls == []


@pytest.mark.asyncio
async def test_runtime_cache_reuses_valid_result_even_when_previous_attempt_needed_retry() -> None:
    cached_payload = _valid_article_analysis_payload()
    prompt_runs = _FakePromptRunRepository()
    prompt_runs.by_identity[(
        "article_analysis_v1",
        "article_analysis_v1",
        "article_analysis_v1",
        "test-model",
        "cached-hash",
        1,
    )] = (
        _FakePromptRun(prompt_run_id=UUID("66666666-6666-6666-6666-666666666666"), prompt_name="article_analysis_v1", retry_count=1, validation_state="valid"),
        _FakeArticleStructure(schema_version="article_analysis_v1", article_structure_id=UUID("77777777-7777-7777-7777-777777777777"), payload=cached_payload["article_structure"]),
        [_FakeRuleCandidate(rule_candidate_id=UUID("88888888-8888-8888-8888-888888888888"))],
    )
    gateway = _FakeGateway([cached_payload])
    article_repo = _FakeArticleRepository()
    service = Stage3PromptRuntimeService(
        session_scope_factory=lambda: _FakeSessionScope(),
        gateway=gateway,
        prompt_run_repository=prompt_runs,
        article_analysis_repository=article_repo,
        model="test-model",
        identity_hasher=lambda article_input, spec, model: "cached-hash",
    )

    result = await service.analyze_article(_article_input())

    assert result.cache_hit is True
    assert gateway.calls == []
    assert article_repo.saved == []


@pytest.mark.asyncio
async def test_runtime_suppresses_concurrent_duplicate_requests() -> None:
    gateway = _SlowGateway([_valid_article_analysis_payload()])
    prompt_runs = _FakePromptRunRepository()
    article_repo = _FakeArticleRepository(prompt_runs=prompt_runs, identity="shared-hash")
    service = Stage3PromptRuntimeService(
        session_scope_factory=lambda: _FakeSessionScope(),
        gateway=gateway,
        prompt_run_repository=prompt_runs,
        article_analysis_repository=article_repo,
        model="test-model",
        identity_hasher=lambda article_input, spec, model: "shared-hash",
    )

    first, second = await asyncio.gather(
        service.analyze_article(_article_input()),
        service.analyze_article(_article_input()),
    )

    assert gateway.calls == ["article_analysis_v1"]
    assert len(article_repo.saved) == 1
    assert first.prompt_run_id == second.prompt_run_id
