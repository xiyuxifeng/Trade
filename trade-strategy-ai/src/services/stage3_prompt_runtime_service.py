from __future__ import annotations

import hashlib
import json
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.stage2_writer_routing import canonical_write_scope
from src.db.repositories.stage3_prompt_runtime_repository import (
    Stage3ArticleAnalysisRepository,
    Stage3PromptRunRepository,
)
from src.llm.prompt_registry import get_prompt_spec
from src.llm.runtime import (
    LLMClientGateway,
    LLMInvocationTrace,
    PromptGateway,
    PromptRuntimeError,
    invoke_with_bounded_retry,
)
from src.llm.client import from_env_and_config
from src.models.stage2_canonical import (
    ArticleStructure,
    CandidateReviewState,
    FormalLifecycleState,
    PromptRun,
    PromptValidationState,
    QualityStatus,
    RuleCandidate,
)
from src.services.rule_governance_service import fingerprint_rule_payload


@dataclass(frozen=True, slots=True)
class ArticlePromptInput:
    article_id: UUID
    article_revision_id: UUID
    article_title: str
    article_content: str
    source_url: str
    published_at: datetime | None
    article_content_hash: str | None = None


@dataclass(frozen=True, slots=True)
class ArticlePromptRuntimeResult:
    cache_hit: bool
    repair_count: int
    prompt_run_id: UUID
    article_structure_id: UUID
    rule_candidate_ids: list[UUID]


def _default_identity_hasher(article_input: ArticlePromptInput, spec, model: str) -> str:
    content_material = article_input.article_content_hash or article_input.article_content
    material = json.dumps(
        {
            "article_revision_id": str(article_input.article_revision_id),
            "article_content_hash": content_material,
            "prompt_name": spec.prompt_name,
            "prompt_version": spec.prompt_version,
            "schema_version": spec.schema_version,
            "model": model,
            "source_url": article_input.source_url,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _apply_patch(document: dict[str, Any], patched_fields: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(document))
    for path, value in patched_fields.items():
        parts = path.split(".")
        cursor: Any = updated
        for raw_part in parts[:-1]:
            part: Any = int(raw_part) if raw_part.isdigit() else raw_part
            cursor = cursor[part]
        final = parts[-1]
        cursor[int(final) if final.isdigit() else final] = value
    return updated


def _collect_repair_targets(errors: list[dict[str, Any]]) -> list[str]:
    targets = []
    for item in errors:
        location = ".".join(str(part) for part in item.get("loc", ()))
        if location:
            targets.append(location)
    return sorted(set(targets))


def _collect_evidence_from_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    article_structure = payload["article_structure"]
    rule_extraction = payload["rule_extraction"]
    return {
        "classification": payload["classification"].get("evidence", []),
        "key_claims": [claim.get("evidence", []) for claim in article_structure.get("key_claims", [])],
        "rule_evidence": [
            {"rule_key": rule.get("rule_key"), "evidence": rule.get("evidence", [])}
            for rule in rule_extraction.get("strategy_rules", [])
        ],
    }


def _missing_fields(payload: dict[str, Any]) -> dict[str, Any]:
    missing = {
        "article_structure.market_state": payload["article_structure"]["market_state"].get("status"),
        "explicit_preconditions.status": payload["explicit_preconditions"].get("status"),
        "rules": [
            {
                "rule_key": rule.get("rule_key"),
                "missing_fields": rule.get("quantification", {}).get("missing_fields", []),
                "ambiguous_terms": rule.get("quantification", {}).get("ambiguous_terms", []),
            }
            for rule in payload["rule_extraction"].get("strategy_rules", [])
        ],
    }
    return missing


def _inference_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "article_market_state_hypotheses": payload["article_structure"]["market_state"].get("inferred_hypotheses", []),
        "rule_market_state_hypotheses": [
            {
                "rule_key": rule.get("rule_key"),
                "inferred_hypotheses": rule.get("market_state_applicability", {}).get("inferred_hypotheses", []),
            }
            for rule in payload["rule_extraction"].get("strategy_rules", [])
        ],
    }


def _fingerprint(payload: dict[str, Any]) -> str:
    return fingerprint_rule_payload(payload).exact_fingerprint


class Stage3PromptRuntimeService:
    service_name = "stage3-prompt-runtime"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any],
        gateway: PromptGateway | None = None,
        prompt_run_repository: Stage3PromptRunRepository | Any | None = None,
        article_analysis_repository: Stage3ArticleAnalysisRepository | Any | None = None,
        model: str,
        identity_hasher: Callable[[ArticlePromptInput, Any, str], str] = _default_identity_hasher,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._gateway = gateway or LLMClientGateway.from_config(
            from_env_and_config(provider=None, model=model, url=None, api_key=None)
        )
        self._prompt_run_repository = prompt_run_repository or Stage3PromptRunRepository()
        self._article_analysis_repository = article_analysis_repository or Stage3ArticleAnalysisRepository()
        self._model = model
        self._identity_hasher = identity_hasher
        self._locks: dict[str, Any] = {}

    async def analyze_article(self, article_input: ArticlePromptInput) -> ArticlePromptRuntimeResult:
        main_spec = get_prompt_spec("article_analysis_v1")
        identity = self._identity_hasher(article_input, main_spec, self._model)
        lock = self._locks.setdefault(identity, asyncio.Lock())
        async with lock:
            async with self._session_scope_factory() as session:
                cached = await self._load_cached(session, identity=identity)
                if cached is not None:
                    prompt_run, structure, candidates = cached
                    return ArticlePromptRuntimeResult(
                        cache_hit=True,
                        repair_count=0,
                        prompt_run_id=prompt_run.prompt_run_id,
                        article_structure_id=structure.article_structure_id,
                        rule_candidate_ids=[candidate.rule_candidate_id for candidate in candidates],
                    )

                return await self._run_article_analysis(session, article_input=article_input, identity=identity)

    async def _load_cached(
        self,
        session: AsyncSession,
        *,
        identity: str,
    ):
        return await self._prompt_run_repository.get_cached_result(
            session,
            prompt_name="article_analysis_v1",
            prompt_version="article_analysis_v1",
            schema_version="article_analysis_v1",
            model=self._model,
            input_hash=identity,
            retry_count=0,
        )

    async def _run_article_analysis(
        self,
        session: AsyncSession,
        *,
        article_input: ArticlePromptInput,
        identity: str,
    ) -> ArticlePromptRuntimeResult:
        main_spec = get_prompt_spec("article_analysis_v1")
        repair_spec = get_prompt_spec("article_analysis_repair_v1")
        article_payload = {
            "article_id": str(article_input.article_id),
            "article_revision_id": str(article_input.article_revision_id),
            "title": article_input.article_title,
            "content": article_input.article_content,
            "content_hash": article_input.article_content_hash,
            "source_url": article_input.source_url,
            "published_at": article_input.published_at.isoformat() if article_input.published_at else None,
        }

        main_trace, main_retry_count = await invoke_with_bounded_retry(
            self._gateway,
            prompt_name=main_spec.prompt_name,
            system_prompt=main_spec.load_prompt_text(),
            user_prompt=json.dumps(article_payload, ensure_ascii=False, sort_keys=True),
            model=self._model,
        )
        main_run = self._build_prompt_run(
            article_input=article_input,
            identity=identity,
            spec=main_spec,
            trace=main_trace,
            retry_count=main_retry_count,
            validation_state=PromptValidationState.pending,
            validation_errors={},
            request_json=article_payload,
        )
        try:
            validated = main_spec.validate_output(main_trace.data)
            main_run.validation_state = PromptValidationState.valid
            repair_count = 0
        except ValidationError as exc:
            main_run.validation_state = PromptValidationState.invalid_schema
            main_run.validation_errors = {"errors": exc.errors()}
            with canonical_write_scope("article_analysis", self.service_name):
                await self._prompt_run_repository.save_run(session, main_run)
            validated, repair_trace, repair_retry_count = await self._repair_once(
                article_input=article_input,
                identity=identity,
                previous_result=main_trace.data,
                validation_error=exc,
            )
            main_run.validation_state = PromptValidationState.repaired
            main_run.validation_errors = {}
            main_run.completed_at = datetime.now(UTC)
            repair_count = 1
            repair_run = self._build_prompt_run(
                article_input=article_input,
                identity=identity,
                spec=repair_spec,
                trace=repair_trace,
                retry_count=repair_retry_count,
                validation_state=PromptValidationState.valid,
                validation_errors={},
                request_json={
                    "article": article_payload,
                    "previous_result": main_trace.data,
                    "repair_targets": _collect_repair_targets(exc.errors()),
                    "validation_errors": exc.errors(),
                },
            )
            with canonical_write_scope("article_analysis", self.service_name):
                await self._prompt_run_repository.save_run(session, repair_run)

        final_payload = validated.model_dump(mode="json")
        structure = ArticleStructure(
            article_id=article_input.article_id,
            article_revision_id=article_input.article_revision_id,
            prompt_run_id=main_run.prompt_run_id,
            schema_version=main_spec.schema_version,
            payload=final_payload["article_structure"],
            evidence_json=_collect_evidence_from_analysis(final_payload),
            missing_fields=_missing_fields(final_payload),
            inference_fields=_inference_fields(final_payload),
            lifecycle_state=FormalLifecycleState.draft,
            quality_status=QualityStatus.partial,
            created_by=self.service_name,
            updated_by=self.service_name,
        )
        candidates = [
            RuleCandidate(
                article_structure_id=structure.article_structure_id,
                source_article_id=article_input.article_id,
                candidate_index=index,
                candidate_fingerprint=_fingerprint(rule),
                rule_type=rule["rule_type"],
                canonical_payload=rule,
                evidence_json={"evidence": rule.get("evidence", [])},
                explicit_fields={"market_state": rule.get("market_state_applicability", {}).get("explicit_conditions", [])},
                inferred_fields={"market_state": rule.get("market_state_applicability", {}).get("inferred_hypotheses", [])},
                missing_fields={
                    "missing_fields": rule.get("quantification", {}).get("missing_fields", []),
                    "ambiguous_terms": rule.get("quantification", {}).get("ambiguous_terms", []),
                },
                data_dependencies={"dependencies": rule.get("data_dependencies", [])},
                backtestability_status=rule.get("quantification", {}).get("status", "not_executable"),
                review_state=CandidateReviewState.extracted,
                quality_status=QualityStatus.partial,
                created_by=self.service_name,
                updated_by=self.service_name,
            )
            for index, rule in enumerate(final_payload["rule_extraction"]["strategy_rules"])
        ]

        with canonical_write_scope("article_analysis", self.service_name):
            saved_run = await self._prompt_run_repository.save_run(session, main_run)
            structure.prompt_run_id = saved_run.prompt_run_id
            saved_structure, saved_candidates = await self._article_analysis_repository.save_structure_with_candidates(
                session,
                structure=structure,
                candidates=candidates,
            )

        return ArticlePromptRuntimeResult(
            cache_hit=False,
            repair_count=repair_count,
            prompt_run_id=saved_run.prompt_run_id,
            article_structure_id=saved_structure.article_structure_id,
            rule_candidate_ids=[candidate.rule_candidate_id for candidate in saved_candidates],
        )

    async def _repair_once(
        self,
        *,
        article_input: ArticlePromptInput,
        identity: str,
        previous_result: dict[str, Any],
        validation_error: ValidationError,
    ):
        repair_spec = get_prompt_spec("article_analysis_repair_v1")
        request_json = {
            "article": {
                "article_id": str(article_input.article_id),
                "article_revision_id": str(article_input.article_revision_id),
                "title": article_input.article_title,
                "content": article_input.article_content,
                "content_hash": article_input.article_content_hash,
                "source_url": article_input.source_url,
                "published_at": article_input.published_at.isoformat() if article_input.published_at else None,
            },
            "previous_result": previous_result,
            "repair_targets": _collect_repair_targets(validation_error.errors()),
            "validation_errors": validation_error.errors(),
        }
        repair_trace, repair_retry_count = await invoke_with_bounded_retry(
            self._gateway,
            prompt_name=repair_spec.prompt_name,
            system_prompt=repair_spec.load_prompt_text(),
            user_prompt=json.dumps(request_json, ensure_ascii=False, sort_keys=True),
            model=self._model,
        )
        repair_output = repair_spec.validate_output(repair_trace.data)
        if repair_output.unresolved_errors:
            raise PromptRuntimeError("repair failed and requires human handling")
        if not repair_output.patched_fields:
            raise PromptRuntimeError("repair returned no targeted fields")
        patched = _apply_patch(previous_result, repair_output.patched_fields)
        try:
            validated = get_prompt_spec("article_analysis_v1").validate_output(patched)
        except ValidationError as exc:
            raise PromptRuntimeError("second repair is not allowed") from exc
        return validated, repair_trace, repair_retry_count

    def _build_prompt_run(
        self,
        *,
        article_input: ArticlePromptInput,
        identity: str,
        spec,
        trace: LLMInvocationTrace,
        retry_count: int,
        validation_state: PromptValidationState,
        validation_errors: dict[str, Any],
        request_json: dict[str, Any],
    ) -> PromptRun:
        started_at = datetime.now(UTC)
        return PromptRun(
            prompt_run_id=uuid4(),
            run_id=uuid4().hex,
            article_id=article_input.article_id,
            prompt_name=spec.prompt_name,
            prompt_version=spec.prompt_version,
            schema_name=spec.schema_name,
            schema_version=spec.schema_version,
            provider=trace.provider,
            model=trace.model,
            input_object_type="article_revision",
            input_object_id=str(article_input.article_id),
            input_version_id=str(article_input.article_revision_id),
            input_hash=identity,
            request_json=_jsonable(request_json),
            raw_output=trace.raw_output,
            raw_output_text=trace.raw_output_text,
            validation_state=validation_state,
            validation_errors=_jsonable(validation_errors),
            retry_count=retry_count,
            token_usage=_jsonable(trace.token_usage),
            cost_amount=trace.cost_amount,
            cost_currency=trace.cost_currency,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
