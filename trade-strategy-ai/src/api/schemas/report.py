from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TradeIdeaResponse(BaseModel):
    idea_id: UUID
    trader_id: str
    symbol: str
    side: str
    entry_price: float | None = None
    target_price: float | None = None
    stop_loss_price: float | None = None
    position_size: float | None = None
    confidence: float | None = None
    style_cluster_id: str | None = None
    style_cluster_label: str | None = None
    style_score: float | None = None
    style_reasons: list[str] = Field(default_factory=list)
    rationale: str | None = None
    invalidation: str | None = None


class DailyReportResponse(BaseModel):
    report_id: UUID
    as_of_date: date
    generated_at: datetime
    ideas: list[TradeIdeaResponse] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class IdeaEvaluationResponse(BaseModel):
    idea_id: UUID
    symbol: str
    entry_price: float | None = None
    current_price: float | None = None
    return_pct: float | None = None
    status: str = "not_evaluated"
    notes: list[str] = Field(default_factory=list)


class EvaluationResultResponse(BaseModel):
    result_id: UUID
    as_of_date: date
    generated_at: datetime
    evaluations: list[IdeaEvaluationResponse] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class DailyReportSummary(BaseModel):
    report_id: UUID
    as_of_date: date
    generated_at: datetime
    ideas_count: int
    highlights_count: int


class EvaluationResultSummary(BaseModel):
    result_id: UUID
    as_of_date: date
    generated_at: datetime
    evaluations_count: int
    summary_count: int
