from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.extraction_taxonomy_repository import ExtractionTaxonomyRepository
from src.domain.enums import FormalLifecycleState, QualityStatus
from src.models.extraction_taxonomy import (
    ExtractionItem,
    ExtractionQualityState,
    ExtractionReviewState,
)
from src.models.stage2_canonical import LifecycleEvent, PromptRun, PromptValidationState, Rule, RuleVersion
from src.schemas.extraction_taxonomy import (
    SCHEMA_VERSION,
    TAXONOMY_VERSION,
    ExecutableRulePayload,
    ExtractionItemDraft,
    PrimaryType,
    review_destination_for,
    validate_taxonomy_payload,
)


class ExtractionTaxonomyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reason: str
    required_next_step: str
    blocked_by: list[str]


def stable_fingerprint(material: dict[str, Any]) -> str:
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_extraction_item(
    *,
    draft: ExtractionItemDraft,
    article_id: UUID,
    article_revision_id: UUID | None,
    article_structure_id: UUID,
    prompt_run: PromptRun,
    item_index: int,
    source_url: str | None,
    origin: str = "new_taxonomy_extraction",
    source_object_type: str = "article_revision",
    source_object_id: str | None = None,
    lineage: list[str] | None = None,
    created_by: str = "taxonomy-runtime",
) -> ExtractionItem:
    evidence = {
        "article_id": str(article_id),
        "article_revision_id": str(article_revision_id) if article_revision_id else None,
        "article_structure_id": str(article_structure_id),
        "prompt_run_id": str(prompt_run.prompt_run_id),
        "source_url": source_url,
        **draft.source_evidence.model_dump(mode="json"),
    }
    payload = draft.taxonomy_payload.model_dump(mode="json")
    provenance = {
        "origin": origin,
        "source_object_type": source_object_type,
        "source_object_id": source_object_id or (str(article_revision_id) if article_revision_id else str(article_id)),
        "prompt_name": prompt_run.prompt_name,
        "prompt_version": prompt_run.prompt_version,
        "schema_version": SCHEMA_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "model": prompt_run.model,
        "classifier": None,
        "lineage": lineage or [],
        "created_by_process": created_by,
    }
    fingerprint = stable_fingerprint(
        {
            "taxonomy_version": TAXONOMY_VERSION,
            "schema_version": SCHEMA_VERSION,
            "article_revision_id": str(article_revision_id) if article_revision_id else None,
            "prompt_run_id": str(prompt_run.prompt_run_id),
            "item_index": item_index,
            "primary_type": draft.primary_type.value,
            "source_evidence": evidence,
            "taxonomy_payload": payload,
        }
    )
    return ExtractionItem(
        extraction_item_id=uuid4(),
        article_id=article_id,
        article_revision_id=article_revision_id,
        article_structure_id=article_structure_id,
        prompt_run_id=prompt_run.prompt_run_id,
        item_index=item_index,
        item_fingerprint=fingerprint,
        taxonomy_version=TAXONOMY_VERSION,
        schema_version=SCHEMA_VERSION,
        primary_type=draft.primary_type,
        secondary_tags=draft.secondary_tags,
        taxonomy_payload=payload,
        source_evidence=evidence,
        confidence=draft.confidence.model_dump(mode="json"),
        quality_state=ExtractionQualityState.valid,
        review_destination=review_destination_for(draft.primary_type),
        review_state=ExtractionReviewState.queued,
        provenance=provenance,
        created_by=created_by,
        updated_by=created_by,
    )


def validate_item_integrity(item: ExtractionItem) -> None:
    validated = validate_taxonomy_payload(item.primary_type, item.taxonomy_payload)
    evidence = item.source_evidence if isinstance(item.source_evidence, dict) else {}
    required_evidence = ("article_id", "article_structure_id", "prompt_run_id", "evidence_kind", "rationale")
    missing = [field for field in required_evidence if not evidence.get(field)]
    if PrimaryType(item.primary_type) != PrimaryType.unusable_noise and not str(evidence.get("quote") or "").strip():
        missing.append("quote")
    if missing:
        raise ExtractionTaxonomyError(f"missing source evidence: {', '.join(sorted(set(missing)))}")
    if item.review_destination != review_destination_for(item.primary_type):
        raise ExtractionTaxonomyError("review destination does not match primary type")
    if isinstance(validated, ExecutableRulePayload) and item.quality_state != ExtractionQualityState.valid:
        raise ExtractionTaxonomyError("executable rule quality must be valid")


def eligibility_for(item: ExtractionItem) -> Eligibility:
    primary_type = PrimaryType(item.primary_type)
    if primary_type != PrimaryType.executable_rule:
        step = {
            PrimaryType.rule_candidate: "repair",
            PrimaryType.research_hypothesis: "research_review",
            PrimaryType.semantic_experience: "semantic_review",
            PrimaryType.risk_control_hint: "risk_backlog",
            PrimaryType.data_requirement_hint: "data_backlog",
            PrimaryType.unusable_noise: "rejection",
        }[primary_type]
        return Eligibility(False, f"{primary_type.value} is not a formal trading rule", step, ["non_rule_type"])
    try:
        validate_item_integrity(item)
    except (ValueError, ExtractionTaxonomyError) as exc:
        return Eligibility(False, str(exc), "validation", ["contract_validation"])
    if item.review_state not in {ExtractionReviewState.accepted, ExtractionReviewState.promoted}:
        return Eligibility(False, "strict executable validation has not been accepted", "validation", ["validation_not_accepted"])
    return Eligibility(True, "strict executable contract and evidence validation passed", "none", [])


class ExtractionTaxonomyService:
    service_name = "extraction-taxonomy-service"

    def __init__(self, repository: ExtractionTaxonomyRepository | None = None) -> None:
        self._repository = repository or ExtractionTaxonomyRepository()

    async def accept_review(
        self, session: AsyncSession, *, item: ExtractionItem, actor_id: str
    ) -> ExtractionItem:
        validate_item_integrity(item)
        if PrimaryType(item.primary_type) == PrimaryType.unusable_noise:
            item.review_state = ExtractionReviewState.rejected
            item.quality_state = ExtractionQualityState.rejected
        else:
            item.review_state = ExtractionReviewState.accepted
        item.updated_by = actor_id
        await session.flush()
        return item

    async def reject_review(
        self, session: AsyncSession, *, item: ExtractionItem, actor_id: str
    ) -> ExtractionItem:
        item.review_state = ExtractionReviewState.rejected
        item.quality_state = ExtractionQualityState.rejected
        item.updated_by = actor_id
        await session.flush()
        return item

    async def repair_candidate(
        self,
        session: AsyncSession,
        *,
        item: ExtractionItem,
        repaired_payload: dict[str, Any],
        source_quote: str,
        rationale: str,
        actor_id: str,
    ) -> ExtractionItem:
        if PrimaryType(item.primary_type) != PrimaryType.rule_candidate:
            raise ExtractionTaxonomyError("only rule_candidate can enter repair")
        validated = validate_taxonomy_payload(PrimaryType.executable_rule, repaired_payload)
        if not isinstance(validated, ExecutableRulePayload):
            raise ExtractionTaxonomyError("repair must produce an executable_rule")
        if not source_quote.strip() or not rationale.strip():
            raise ExtractionTaxonomyError("repair requires traceable source quote and rationale")

        now = datetime.now(UTC)
        repair_identity = stable_fingerprint(
            {"parent": str(item.extraction_item_id), "payload": validated.model_dump(mode="json"), "actor": actor_id}
        )
        repair_run = PromptRun(
            prompt_run_id=uuid4(),
            run_id=uuid4().hex,
            article_id=item.article_id,
            prompt_name="taxonomy_rule_candidate_repair_v1",
            prompt_version="taxonomy_rule_candidate_repair_v1",
            schema_name=SCHEMA_VERSION,
            schema_version=SCHEMA_VERSION,
            provider="human",
            model="human-reviewed-repair",
            input_object_type="extraction_item",
            input_object_id=str(item.extraction_item_id),
            input_version_id=item.item_fingerprint,
            input_hash=repair_identity,
            request_json={"source_item_id": str(item.extraction_item_id)},
            raw_output=validated.model_dump(mode="json"),
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
        session.add(repair_run)
        await session.flush()
        draft = ExtractionItemDraft.model_validate(
            {
                "primary_type": "executable_rule",
                "secondary_tags": list(item.secondary_tags or []) + ["repaired_from_rule_candidate"],
                "taxonomy_payload": validated.model_dump(mode="json"),
                "source_evidence": {
                    "quote": source_quote,
                    "span": None,
                    "section": None,
                    "evidence_kind": "human_annotation",
                    "rationale": rationale,
                },
                "confidence": {
                    "score": 1.0,
                    "level": "high",
                    "rationale": "human-reviewed bounded repair",
                    "requires_human_confirmation": False,
                },
            }
        )
        repaired = build_extraction_item(
            draft=draft,
            article_id=item.article_id,
            article_revision_id=item.article_revision_id,
            article_structure_id=item.article_structure_id,
            prompt_run=repair_run,
            item_index=0,
            source_url=(item.source_evidence or {}).get("source_url"),
            origin="repair_output",
            source_object_type="extraction_item",
            source_object_id=str(item.extraction_item_id),
            lineage=[str(item.extraction_item_id)],
            created_by=actor_id,
        )
        await self._repository.save_items(session, items=[repaired])
        item.review_state = ExtractionReviewState.repaired
        item.updated_by = actor_id
        await session.flush()
        return repaired

    async def promote_to_rule_version(
        self, session: AsyncSession, *, item: ExtractionItem, actor_id: str
    ) -> RuleVersion:
        admission = eligibility_for(item)
        if not admission.eligible:
            raise ExtractionTaxonomyError(admission.reason)
        existing = await self._repository.get_rule_version_for_item(
            session, item_id=item.extraction_item_id
        )
        if existing is not None:
            return existing
        duplicate = await self._repository.get_rule_version_by_fingerprint(
            session, fingerprint=item.item_fingerprint
        )
        if duplicate is not None:
            raise ExtractionTaxonomyError("governance duplicate fingerprint must be resolved before promotion")

        payload = ExecutableRulePayload.model_validate(item.taxonomy_payload)
        now = datetime.now(UTC)
        rule = Rule(
            rule_id=uuid4(),
            business_key=f"taxonomy:{item.item_fingerprint}",
            current_published_version_id=None,
            created_at=now,
            created_by=actor_id,
            updated_at=now,
            updated_by=actor_id,
        )
        session.add(rule)
        await session.flush()
        version = RuleVersion(
            rule_version_id=uuid4(),
            rule_id=rule.rule_id,
            version_no=1,
            source_candidate_id=None,
            source_extraction_item_id=item.extraction_item_id,
            canonical_fingerprint=item.item_fingerprint,
            schema_version=SCHEMA_VERSION,
            lifecycle_state=FormalLifecycleState.draft,
            title=payload.title,
            description=(item.source_evidence or {}).get("rationale"),
            rule_type=payload.rule_type,
            instrument_scope=payload.instrument_universe,
            condition_json={"entry": payload.entry_condition, "exit": payload.exit_condition},
            action_json={
                "entry_timing": payload.entry_timing,
                "entry_price_reference": payload.entry_price_reference,
                "exit_timing": payload.exit_timing,
                "exit_price_reference": payload.exit_price_reference,
            },
            parameter_json={
                "position_sizing": payload.position_sizing,
                "stop_loss_or_invalidation": payload.stop_loss_or_invalidation,
                "holding_period": payload.holding_period,
                "parameterization": payload.parameterization,
                "timestamp_availability": payload.timestamp_availability,
                "lookahead_check": payload.lookahead_check.model_dump(mode="json"),
            },
            data_dependencies={"dependencies": payload.data_dependencies},
            evidence_json={"source_evidence": item.source_evidence, "provenance": item.provenance},
            quality_status=QualityStatus.complete,
            parent_version_id=None,
            published_at=None,
            published_by=None,
            superseded_at=None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(version)
        await session.flush()
        item.review_state = ExtractionReviewState.promoted
        item.updated_by = actor_id
        session.add(
            LifecycleEvent(
                event_id=uuid4(),
                object_type="extraction_item",
                object_id=item.extraction_item_id,
                from_state=ExtractionReviewState.accepted.value,
                to_state=ExtractionReviewState.promoted.value,
                actor_type="human",
                actor_id=actor_id,
                reason_code="strict_executable_promoted",
                reason_text="strict executable taxonomy item promoted to RuleVersion",
                before_json={"review_state": ExtractionReviewState.accepted.value},
                after_json={
                    "review_state": ExtractionReviewState.promoted.value,
                    "rule_version_id": str(version.rule_version_id),
                },
                occurred_at=now,
                correlation_id=str(version.rule_version_id),
            )
        )
        await session.flush()
        return version
