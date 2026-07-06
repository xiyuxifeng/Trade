from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ArticleAnalysisArticleResponse(BaseModel):
    article_id: str
    article_revision_id: str
    content_hash: str
    title: str
    source: str
    source_url: str
    author_name: str | None = None
    author_id: str | None = None
    published_at: datetime | None = None
    crawled_at: datetime
    original_text: str
    cleaned_content: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)


class SummaryProvenanceResponse(BaseModel):
    source: Literal["article_revision_source_payload", "blog_article_current", "unavailable"]
    article_revision_id: str
    content_hash: str
    available: bool
    aligned: bool
    reason: str | None = None


class ArticleStructureProvenanceResponse(BaseModel):
    article_structure_id: str | None = None
    article_revision_id: str | None = None
    prompt_run_id: str | None = None
    prompt_name: str | None = None
    prompt_version: str | None = None
    schema_name: str | None = None
    schema_version: str | None = None
    available: bool


class ArticleAnalysisTraceResponse(BaseModel):
    run_id: str | None = None
    prompt_name: str | None = None
    prompt_version: str | None = None
    schema_name: str | None = None
    schema_version: str | None = None
    provider: str | None = None
    model: str | None = None
    validation_state: str | None = None
    retry_count: int = 0
    token_usage: dict[str, Any] = Field(default_factory=dict)
    cost_amount: float | None = None
    cost_currency: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AutomaticReviewResponse(BaseModel):
    status: Literal["pending_backtest", "needs_human_review", "suggested_reject"]
    reasons: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"]


class HumanReviewResponse(BaseModel):
    review_state: str
    formal_rule_created: bool
    rule_version_id: str | None = None
    formal_lifecycle_state: str | None = None
    stage3_status: str | None = None


class GovernanceMatchResponse(BaseModel):
    relation: Literal["exact_duplicate", "parameter_variant", "conflict", "similar_rule", "distinct"]
    rule_version_id: str
    rule_id: str
    family_id: str | None = None
    title: str
    parameter_differences: dict[str, dict[str, Any]] = Field(default_factory=dict)
    conflict_reasons: list[str] = Field(default_factory=list)


class CandidateGovernanceResponse(BaseModel):
    algorithm_version: str
    exact_fingerprint: str
    family_fingerprint: str
    family_key: str
    exact_duplicate_of_rule_version_id: str | None = None
    eligible_for_formal_version: bool
    eligible_for_backtest: bool
    related_rules: list[GovernanceMatchResponse] = Field(default_factory=list)


class CandidateRuleResponse(BaseModel):
    candidate_id: str
    candidate_index: int
    title: str
    rule_type: str
    explicit_facts: dict[str, Any] = Field(default_factory=dict)
    hypotheses: dict[str, Any] = Field(default_factory=dict)
    missing_fields: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    data_dependencies: dict[str, Any] = Field(default_factory=dict)
    backtestability_status: str
    kaipan_dependency: bool
    market_state_declaration_status: str
    automatic_review: AutomaticReviewResponse
    human_review: HumanReviewResponse
    governance: CandidateGovernanceResponse


class ArticleAnalysisDetailResponse(BaseModel):
    status: Literal["ready", "partial", "empty"]
    message: str | None = None
    article: ArticleAnalysisArticleResponse
    summary_provenance: SummaryProvenanceResponse
    article_structure_provenance: ArticleStructureProvenanceResponse
    method_tags: list[str] = Field(default_factory=list)
    explicit_facts: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    missing_fields: dict[str, Any] = Field(default_factory=dict)
    prompt_trace: ArticleAnalysisTraceResponse
    candidates: list[CandidateRuleResponse] = Field(default_factory=list)


class RunArticleAnalysisRequest(BaseModel):
    article_revision_id: str | None = None


class ReviewCandidateRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = None
    article_revision_id: str | None = None


class UpdateArticleProcessingStatusRequest(BaseModel):
    action: Literal["ignored", "manual_review_required"]
    note: str | None = None


class ArticleProcessingStatusResponse(BaseModel):
    article_id: str
    processing_status: Literal["ignored", "manual_review_required"]
    processing_note: str | None = None
    processing_updated_at: datetime
    processing_updated_by: str
