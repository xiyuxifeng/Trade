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


class ExtractionEligibilityResponse(BaseModel):
    eligible: bool
    reason: str
    required_next_step: str
    blocked_by: list[str] = Field(default_factory=list)


class ExtractionItemResponse(BaseModel):
    item_id: str
    item_index: int
    article_id: str
    article_revision_id: str | None = None
    article_structure_id: str
    prompt_run_id: str
    primary_type: Literal[
        "executable_rule",
        "rule_candidate",
        "research_hypothesis",
        "semantic_experience",
        "risk_control_hint",
        "data_requirement_hint",
        "unusable_noise",
    ]
    secondary_tags: list[str] = Field(default_factory=list)
    display_title: str
    display_summary: str
    source_evidence: dict[str, Any]
    taxonomy_payload: dict[str, Any]
    confidence: dict[str, Any]
    quality_state: str
    review_destination: str
    review_state: str
    backtest_eligibility: ExtractionEligibilityResponse
    promotion_eligibility: ExtractionEligibilityResponse
    provenance: dict[str, Any]
    rule_version_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ExtractionSummaryResponse(BaseModel):
    total: int
    by_primary_type: dict[str, int] = Field(default_factory=dict)
    by_destination: dict[str, int] = Field(default_factory=dict)
    by_quality_state: dict[str, int] = Field(default_factory=dict)
    by_review_state: dict[str, int] = Field(default_factory=dict)


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
    taxonomy_version: str | None = None
    extraction_summary: ExtractionSummaryResponse
    extraction_items: list[ExtractionItemResponse] = Field(default_factory=list)


class RunArticleAnalysisRequest(BaseModel):
    article_revision_id: str | None = None


class ReviewExtractionItemRequest(BaseModel):
    decision: Literal["accept", "reject"]
    reason: str | None = None
    article_revision_id: str | None = None


class RepairRuleCandidateRequest(BaseModel):
    repaired_payload: dict[str, Any]
    source_quote: str
    rationale: str
    article_revision_id: str | None = None


class PromoteExtractionItemRequest(BaseModel):
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
