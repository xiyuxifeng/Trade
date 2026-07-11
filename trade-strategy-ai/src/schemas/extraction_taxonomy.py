from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


TAXONOMY_VERSION = "extraction_taxonomy_v1"
SCHEMA_VERSION = "extraction_item_v1"


class PrimaryType(StrEnum):
    executable_rule = "executable_rule"
    rule_candidate = "rule_candidate"
    research_hypothesis = "research_hypothesis"
    semantic_experience = "semantic_experience"
    risk_control_hint = "risk_control_hint"
    data_requirement_hint = "data_requirement_hint"
    unusable_noise = "unusable_noise"


class ReviewDestination(StrEnum):
    executable_rule_validation = "executable_rule_validation"
    rule_candidate_repair = "rule_candidate_repair"
    research_hypothesis_review = "research_hypothesis_review"
    semantic_dictionary_review = "semantic_dictionary_review"
    risk_backlog = "risk_backlog"
    data_requirement_backlog = "data_requirement_backlog"
    noise_rejection = "noise_rejection"


REVIEW_DESTINATIONS: dict[PrimaryType, ReviewDestination] = {
    PrimaryType.executable_rule: ReviewDestination.executable_rule_validation,
    PrimaryType.rule_candidate: ReviewDestination.rule_candidate_repair,
    PrimaryType.research_hypothesis: ReviewDestination.research_hypothesis_review,
    PrimaryType.semantic_experience: ReviewDestination.semantic_dictionary_review,
    PrimaryType.risk_control_hint: ReviewDestination.risk_backlog,
    PrimaryType.data_requirement_hint: ReviewDestination.data_requirement_backlog,
    PrimaryType.unusable_noise: ReviewDestination.noise_rejection,
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Confidence(StrictModel):
    score: float = Field(ge=0, le=1)
    level: Literal["high", "medium", "low"]
    rationale: str = Field(min_length=1)
    requires_human_confirmation: bool


class SourceSpan(StrictModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_order(self) -> "SourceSpan":
        if self.end <= self.start:
            raise ValueError("source span end must be greater than start")
        return self


class SourceEvidenceDraft(StrictModel):
    quote: str = ""
    span: SourceSpan | None = None
    section: str | int | None = None
    evidence_kind: Literal[
        "explicit_quote",
        "inferred_from_context",
        "old_candidate_reclassification",
        "human_annotation",
    ]
    rationale: str = Field(min_length=1)


class LookaheadCheck(StrictModel):
    passed: bool
    rationale: str = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)


class ExecutableRulePayload(StrictModel):
    primary_type: Literal[PrimaryType.executable_rule] = PrimaryType.executable_rule
    title: str = Field(min_length=1)
    rule_type: Literal["entry", "exit", "filter", "risk", "sizing", "selection"]
    instrument_universe: dict[str, Any]
    entry_condition: dict[str, Any]
    entry_timing: str = Field(min_length=1)
    entry_price_reference: str = Field(min_length=1)
    exit_condition: dict[str, Any]
    exit_timing: str = Field(min_length=1)
    exit_price_reference: str = Field(min_length=1)
    stop_loss_or_invalidation: dict[str, Any]
    position_sizing: dict[str, Any]
    holding_period: dict[str, Any] | None = None
    data_dependencies: list[dict[str, Any]] = Field(min_length=1)
    timestamp_availability: list[dict[str, Any]] = Field(min_length=1)
    lookahead_check: LookaheadCheck
    ambiguous_terms: list[str]
    parameterization: list[dict[str, Any]]
    rule_version_candidate: dict[str, Any]
    not_directly_backtestable: Literal[False]

    @model_validator(mode="after")
    def strict_admission(self) -> "ExecutableRulePayload":
        required_objects = {
            "instrument_universe": self.instrument_universe,
            "entry_condition": self.entry_condition,
            "exit_condition": self.exit_condition,
            "stop_loss_or_invalidation": self.stop_loss_or_invalidation,
            "position_sizing": self.position_sizing,
            "rule_version_candidate": self.rule_version_candidate,
        }
        empty = [name for name, value in required_objects.items() if not value]
        if empty:
            raise ValueError(f"executable rule fields must not be empty: {', '.join(empty)}")
        if self.ambiguous_terms:
            raise ValueError("executable rule cannot contain unresolved ambiguous terms")
        if not self.lookahead_check.passed or self.lookahead_check.risks:
            raise ValueError("executable rule must pass lookahead validation without risks")
        return self


class RuleCandidatePayload(StrictModel):
    primary_type: Literal[PrimaryType.rule_candidate] = PrimaryType.rule_candidate
    candidate_rule_summary: str = Field(min_length=1)
    known_components: dict[str, Any]
    missing_fields: list[str] = Field(min_length=1)
    repair_tasks: list[str] = Field(min_length=1)
    repair_source: Literal["source_text", "project_convention", "parameter_search", "human_input"]
    repairability: Literal["high", "medium", "low"]
    instrument_universe_status: Literal["complete", "partial", "missing", "not_applicable"]
    entry_exit_status: dict[str, Any]
    data_dependencies: list[dict[str, Any]]
    timestamp_availability_risk: list[str]
    ambiguous_terms: list[dict[str, Any]]
    not_directly_backtestable: Literal[True]


class ResearchHypothesisPayload(StrictModel):
    primary_type: Literal[PrimaryType.research_hypothesis] = PrimaryType.research_hypothesis
    hypothesis_statement: str = Field(min_length=1)
    source_experience: str = Field(min_length=1)
    dependent_variables: list[str] = Field(min_length=1)
    independent_variables: list[str] = Field(min_length=1)
    candidate_observable_indicators: list[str] = Field(min_length=1)
    required_data: list[str] = Field(min_length=1)
    validation_method: str = Field(min_length=1)
    timestamp_availability_assumptions: list[str] = Field(min_length=1)
    research_status: Literal["proposed", "accepted", "rejected", "tested", "archived"]
    not_directly_backtestable: Literal[True]


class SemanticExperiencePayload(StrictModel):
    primary_type: Literal[PrimaryType.semantic_experience] = PrimaryType.semantic_experience
    term_or_phrase: str = Field(min_length=1)
    source_context: str = Field(min_length=1)
    plain_language_interpretation: str = Field(min_length=1)
    related_market_state: str | None = None
    possible_observable_proxies: list[str] = Field(default_factory=list)
    semantic_dictionary_action: Literal["add", "merge", "clarify", "reject", "observe"]
    ambiguity_level: Literal["high", "medium", "low"]
    not_directly_backtestable: Literal[True]


class RiskControlHintPayload(StrictModel):
    primary_type: Literal[PrimaryType.risk_control_hint] = PrimaryType.risk_control_hint
    risk_context: str = Field(min_length=1)
    risk_action: str = Field(min_length=1)
    sizing_boundary: dict[str, Any] | None = None
    trigger_terms: list[str] = Field(min_length=1)
    missing_definitions: list[str]
    system_design_use: list[str] = Field(min_length=1)
    data_dependencies: list[str] = Field(default_factory=list)
    not_directly_backtestable: Literal[True]


class DataRequirementHintPayload(StrictModel):
    primary_type: Literal[PrimaryType.data_requirement_hint] = PrimaryType.data_requirement_hint
    data_name: str = Field(min_length=1)
    data_description: str = Field(min_length=1)
    needed_by: list[str] = Field(default_factory=list)
    timestamp_requirement: str = Field(min_length=1)
    granularity: Literal["tick", "auction", "intraday", "daily", "sector", "market", "article"]
    source_or_provider: str | None = None
    availability_status: Literal["available", "unavailable", "unknown", "partial"]
    data_contract_gap: list[str] = Field(min_length=1)
    not_directly_backtestable: Literal[True]


class UnusableNoisePayload(StrictModel):
    primary_type: Literal[PrimaryType.unusable_noise] = PrimaryType.unusable_noise
    reason: str = Field(min_length=1)
    noise_category: Literal[
        "motivational",
        "duplicate",
        "hallucinated",
        "contradictory",
        "non_trading",
        "too_vague",
        "unsupported",
    ]
    retain_source_reference_only: Literal[True]
    dedupe_key: str | None = None


TaxonomyPayload = Annotated[
    ExecutableRulePayload
    | RuleCandidatePayload
    | ResearchHypothesisPayload
    | SemanticExperiencePayload
    | RiskControlHintPayload
    | DataRequirementHintPayload
    | UnusableNoisePayload,
    Field(discriminator="primary_type"),
]
TAXONOMY_PAYLOAD_ADAPTER: TypeAdapter[TaxonomyPayload] = TypeAdapter(TaxonomyPayload)


class ExtractionItemDraft(StrictModel):
    primary_type: PrimaryType
    secondary_tags: list[str] = Field(default_factory=list)
    taxonomy_payload: TaxonomyPayload
    source_evidence: SourceEvidenceDraft
    confidence: Confidence

    @model_validator(mode="after")
    def aligned_type_and_evidence(self) -> "ExtractionItemDraft":
        if self.taxonomy_payload.primary_type != self.primary_type:
            raise ValueError("primary_type must match taxonomy_payload discriminator")
        if self.primary_type != PrimaryType.unusable_noise and not self.source_evidence.quote.strip():
            raise ValueError("retained extraction item requires a source quote")
        return self


def validate_taxonomy_payload(primary_type: PrimaryType | str, payload: dict[str, Any]) -> TaxonomyPayload:
    expected = PrimaryType(primary_type)
    material = dict(payload)
    material.setdefault("primary_type", expected.value)
    validated = cast(TaxonomyPayload, TAXONOMY_PAYLOAD_ADAPTER.validate_python(material))
    if validated.primary_type != expected:
        raise ValueError("taxonomy payload type does not match primary_type")
    return validated


def review_destination_for(primary_type: PrimaryType | str) -> ReviewDestination:
    return REVIEW_DESTINATIONS[PrimaryType(primary_type)]
