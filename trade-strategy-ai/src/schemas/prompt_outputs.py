from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _config(title: str) -> ConfigDict:
    return ConfigDict(title=title, extra="forbid")


class VersionedSchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClassificationOutput(VersionedSchemaModel):
    article_type: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)


class ConceptItem(VersionedSchemaModel):
    name: str
    normalized_name: str
    type: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)


class TradingSymbolItem(VersionedSchemaModel):
    raw_name: str
    symbol: str | None = None
    asset_type: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)


class SentimentOutput(VersionedSchemaModel):
    score: float
    confidence: float


class ConceptExtractionOutput(VersionedSchemaModel):
    model_config = _config("concept_v1")

    prompt_version: Literal["concept_extraction_v1"]
    schema_version: Literal["concept_v1"]
    concepts: list[ConceptItem] = Field(default_factory=list)
    trading_symbols: list[TradingSymbolItem] = Field(default_factory=list)
    indicators: list[Any] = Field(default_factory=list)
    chart_patterns: list[Any] = Field(default_factory=list)
    market_themes: list[Any] = Field(default_factory=list)
    risk_concepts: list[Any] = Field(default_factory=list)
    data_dependencies: list[str] = Field(default_factory=list)
    sentiment: SentimentOutput
    warnings: list[str] = Field(default_factory=list)


class HoldingPeriodOutput(VersionedSchemaModel):
    value: str
    source: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)


class MarketStateHypothesis(VersionedSchemaModel):
    market_state: str | None = None
    hypothesis: str | None = None
    source: str | None = None
    confidence: float | None = None
    evidence: list[str] = Field(default_factory=list)
    validation_status: str | None = None


class ArticleMarketStateOutput(VersionedSchemaModel):
    status: Literal["explicit", "not_declared"]
    explicit_conditions: list[Any] = Field(default_factory=list)
    inferred_hypotheses: list[MarketStateHypothesis] = Field(default_factory=list)


class KeyClaimOutput(VersionedSchemaModel):
    claim: str
    claim_type: str
    source: Literal["explicit", "inferred"]
    confidence: float
    evidence: list[str] = Field(default_factory=list)


class ArticleQualityOutput(VersionedSchemaModel):
    information_density: str
    quantifiability: str
    duplicate_risk: str
    needs_manual_review: bool
    warnings: list[str] = Field(default_factory=list)


class ArticleStructureExtractionOutput(VersionedSchemaModel):
    model_config = _config("article_structure_v1")

    prompt_version: Literal["article_structure_extraction_v1"]
    schema_version: Literal["article_structure_v1"] = "article_structure_v1"
    article_id: str
    author_id: str | None = None
    published_at: datetime | None = None
    article_type: str
    method_tags: list[str] = Field(default_factory=list)
    analysis_dimensions: list[str] = Field(default_factory=list)
    instrument_focus: list[str] = Field(default_factory=list)
    holding_period: HoldingPeriodOutput
    entry_patterns: list[str] = Field(default_factory=list)
    exit_patterns: list[str] = Field(default_factory=list)
    risk_concepts: list[str] = Field(default_factory=list)
    data_dependencies: list[str] = Field(default_factory=list)
    market_state: ArticleMarketStateOutput
    key_claims: list[KeyClaimOutput] = Field(default_factory=list)
    article_quality: ArticleQualityOutput


class RuleClauseOutput(VersionedSchemaModel):
    field: str
    operator: str
    value: Any = None
    unit: Any = None
    lookback: Any = None
    raw_expression: str


class RuleConditionOutput(VersionedSchemaModel):
    logic: str
    clauses: list[RuleClauseOutput] = Field(default_factory=list)


class RuleActionOutput(VersionedSchemaModel):
    type: str
    side: str
    price_reference: str


class MarketStateApplicabilityOutput(VersionedSchemaModel):
    status: Literal["explicit", "not_declared"]
    explicit_conditions: list[Any] = Field(default_factory=list)
    inferred_hypotheses: list[Any] = Field(default_factory=list)


class RuleQuantificationOutput(VersionedSchemaModel):
    status: Literal["executable", "partially_executable", "not_executable"]
    missing_fields: list[str] = Field(default_factory=list)
    ambiguous_terms: list[str] = Field(default_factory=list)
    manual_review_required: bool


class RuleEvidenceOutput(VersionedSchemaModel):
    quote: str
    supports: str


class RuleCandidateOutput(VersionedSchemaModel):
    rule_key: str
    title: str
    rule_type: str
    instrument_focus: list[str] = Field(default_factory=list)
    timeframe: str
    holding_period: str
    condition: RuleConditionOutput
    action: RuleActionOutput
    risk_controls: list[Any] = Field(default_factory=list)
    data_dependencies: list[str] = Field(default_factory=list)
    market_state_applicability: MarketStateApplicabilityOutput
    quantification: RuleQuantificationOutput
    confidence: float
    evidence: list[RuleEvidenceOutput] = Field(default_factory=list)
    source_article_id: str


class RuleExtractionOutput(VersionedSchemaModel):
    model_config = _config("rule_v1")

    prompt_version: Literal["rule_extraction_v1"]
    schema_version: Literal["rule_v1"]
    strategy_rules: list[RuleCandidateOutput] = Field(default_factory=list)


class ExplicitConditionOutput(VersionedSchemaModel):
    field: str
    operator: str
    value: Any = None
    raw_expression: str


class ExplicitPreconditionItemOutput(VersionedSchemaModel):
    condition_type: str
    condition: ExplicitConditionOutput
    confidence: float
    evidence: list[str] = Field(default_factory=list)


class ExplicitPreconditionExtractionOutput(VersionedSchemaModel):
    model_config = _config("explicit_precondition_v1")

    prompt_version: Literal["explicit_precondition_extraction_v1"]
    schema_version: Literal["explicit_precondition_v1"] = "explicit_precondition_v1"
    status: Literal["explicit", "not_declared"]
    preconditions: list[ExplicitPreconditionItemOutput] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnalysisQualityOutput(VersionedSchemaModel):
    needs_repair: bool
    repair_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ArticleAnalysisOutput(VersionedSchemaModel):
    model_config = _config("article_analysis_v1")

    prompt_version: Literal["article_analysis_v1"]
    schema_version: Literal["article_analysis_v1"]
    classification: ClassificationOutput
    concept_extraction: ConceptExtractionOutput
    article_structure: ArticleStructureExtractionOutput
    rule_extraction: RuleExtractionOutput
    explicit_preconditions: ExplicitPreconditionExtractionOutput
    quality: AnalysisQualityOutput

    @model_validator(mode="after")
    def _normalize_market_state(self) -> "ArticleAnalysisOutput":
        if self.article_structure.market_state.status != "explicit":
            self.article_structure.market_state.status = "not_declared"
        for rule in self.rule_extraction.strategy_rules:
            if rule.market_state_applicability.status != "explicit":
                rule.market_state_applicability.status = "not_declared"
        if self.explicit_preconditions.status != "explicit":
            self.explicit_preconditions.status = "not_declared"
        return self


class ArticleAnalysisRepairOutput(VersionedSchemaModel):
    model_config = _config("article_analysis_repair_v1")

    prompt_version: Literal["article_analysis_repair_v1"]
    patched_fields: dict[str, Any] = Field(default_factory=dict)
    unresolved_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AuthorMethodProfileBatchOutput(VersionedSchemaModel):
    model_config = _config("author_method_profile_batch_v1")

    prompt_version: Literal["author_method_profile_batch_v1"]
    author_id: str
    batch_id: str
    date_range: dict[str, Any]
    article_count: int
    dominant_methods: list[dict[str, Any]] = Field(default_factory=list)
    analysis_framework: list[Any] = Field(default_factory=list)
    instrument_preferences: list[Any] = Field(default_factory=list)
    entry_preferences: list[Any] = Field(default_factory=list)
    exit_preferences: list[Any] = Field(default_factory=list)
    risk_expressions: list[Any] = Field(default_factory=list)
    holding_period_preferences: list[Any] = Field(default_factory=list)
    data_dependency_preferences: list[Any] = Field(default_factory=list)
    market_state_hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    stable_traits: list[Any] = Field(default_factory=list)
    stage_specific_traits: list[Any] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    representative_articles: list[Any] = Field(default_factory=list)
    quality: dict[str, Any]


class AuthorRuleProfileSummaryOutput(VersionedSchemaModel):
    model_config = _config("author_rule_profile_summary_v1")

    prompt_version: Literal["author_rule_profile_summary_v1"]
    author_id: str
    rule_statistics_snapshot_id: str
    rule_count: int
    rule_family_count: int
    dominant_rule_types: list[Any] = Field(default_factory=list)
    quantification_profile: dict[str, Any]
    data_dependency_profile: list[Any] = Field(default_factory=list)
    common_entry_patterns: list[Any] = Field(default_factory=list)
    common_exit_patterns: list[Any] = Field(default_factory=list)
    common_risk_patterns: list[Any] = Field(default_factory=list)
    holding_period_distribution: list[Any] = Field(default_factory=list)
    duplicate_and_conflict_summary: dict[str, Any]
    representative_rule_families: list[Any] = Field(default_factory=list)
    quality: dict[str, Any]


class AuthorValidatedProfileOutput(VersionedSchemaModel):
    model_config = _config("author_validated_profile_v1")

    prompt_version: Literal["author_validated_profile_v1"]
    author_id: str
    validation_snapshot_id: str
    rule_families_evaluated: int
    backtest_runs: int
    validated_strengths: list[dict[str, Any]] = Field(default_factory=list)
    validated_weaknesses: list[Any] = Field(default_factory=list)
    market_state_performance: list[dict[str, Any]] = Field(default_factory=list)
    data_mode_comparison: dict[str, Any]
    common_failure_modes: list[Any] = Field(default_factory=list)
    unverified_hypotheses: list[Any] = Field(default_factory=list)
    overall_validation_status: str
    quality: dict[str, Any]


class AuthorProfileMergeOutput(VersionedSchemaModel):
    model_config = _config("author_profile_merge_v1")

    prompt_version: Literal["author_profile_merge_v1"]
    author_id: str
    base_profile_version: str | None = None
    draft_profile_version: str
    status: Literal["draft"]
    method_profile: dict[str, Any]
    rule_profile: dict[str, Any]
    validated_profile: dict[str, Any]
    time_segments: list[dict[str, Any]] = Field(default_factory=list)
    stable_traits: list[Any] = Field(default_factory=list)
    validated_market_state_traits: list[Any] = Field(default_factory=list)
    unverified_hypotheses: list[Any] = Field(default_factory=list)
    changes_from_previous: list[dict[str, Any]] = Field(default_factory=list)
    review_required: bool
    review_items: list[Any] = Field(default_factory=list)
    quality: dict[str, Any]


class AuthorProfileRevisionOutput(VersionedSchemaModel):
    model_config = _config("author_profile_revision_v1")

    prompt_version: Literal["author_profile_revision_v1"]
    author_id: str
    current_profile_version: str
    decision: str
    revision_reasons: list[Any] = Field(default_factory=list)
    proposed_changes: list[Any] = Field(default_factory=list)
    evidence_summary: dict[str, Any]
    minimum_evidence_checks: list[Any] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LLMAttributionOutput(VersionedSchemaModel):
    model_config = _config("llm_attribution_v1")

    prompt_version: Literal["llm_attribution_v1"]
    decision: str
    primary_category: str
    secondary_categories: list[Any] = Field(default_factory=list)
    corrected_categories: list[Any] = Field(default_factory=list)
    reasoning: str
    supporting_facts: list[Any] = Field(default_factory=list)
    conflicting_facts: list[Any] = Field(default_factory=list)
    limitations: list[Any] = Field(default_factory=list)
    confidence: float
    follow_up: dict[str, Any]


class StrategyRevisionProposalOutput(VersionedSchemaModel):
    model_config = _config("strategy_revision_proposal_v1")

    prompt_version: Literal["strategy_revision_proposal_v1"]
    base_strategy_version_id: str
    decision: str
    trigger_type: str
    diagnosis: list[Any] = Field(default_factory=list)
    proposed_rule_changes: list[Any] = Field(default_factory=list)
    proposed_weight_changes: list[Any] = Field(default_factory=list)
    proposed_risk_changes: list[Any] = Field(default_factory=list)
    author_profile_revision_needed: bool
    required_validations: list[Any] = Field(default_factory=list)
    evidence_refs: list[Any] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LLMPostmortemNotesOutput(VersionedSchemaModel):
    model_config = _config("llm_postmortem_notes_v1")

    prompt_version: Literal["llm_postmortem_notes_v1"]
    summary: str
    result: str
    primary_attribution: str
    supporting_facts: list[Any] = Field(default_factory=list)
    limitations: list[Any] = Field(default_factory=list)
    follow_up_actions: list[Any] = Field(default_factory=list)
    author_profile_evidence: dict[str, Any]
