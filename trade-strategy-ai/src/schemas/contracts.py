from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DataResponseStatus(str, Enum):
    ok = "ok"
    partial = "partial"
    capability_missing = "capability_missing"
    error = "error"


class DataRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    trader_id: str
    symbols: list[str] = Field(default_factory=list)
    market: str = "CN"
    timeframe: str | None = None
    date_range: tuple[date | None, date | None] | None = None
    fields: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class DataResponse(BaseModel):
    request_id: UUID
    status: DataResponseStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_refs: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class TradeEntry(BaseModel):
    type: str = "limit"  # limit/market/trigger
    price: float | None = None
    condition: str | None = None


class TradeIdea(BaseModel):
    idea_id: UUID = Field(default_factory=uuid4)
    trader_id: str
    as_of_date: date

    symbol: str
    side: str = "buy"

    entry: TradeEntry
    target_price: float | None = None
    stop_loss_price: float | None = None

    position_size: float | None = None  # 0-1 fraction
    time_horizon: str | None = None

    rationale: str | None = None
    invalidation: str | None = None
    confidence: float | None = None  # 0-1


class DailyReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    as_of_date: date
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    ideas: list[TradeIdea] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    trader_id: str
    as_of_date: date
    idea_ids: list[UUID] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class IdeaEvaluation(BaseModel):
    idea_id: UUID
    symbol: str
    entry_price: float | None = None
    current_price: float | None = None
    return_pct: float | None = None
    status: str = "not_evaluated"  # ok/not_evaluated/error
    notes: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    result_id: UUID = Field(default_factory=uuid4)
    as_of_date: date
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    evaluations: list[IdeaEvaluation] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class AgentTask(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    type: str
    title: str
    details: dict[str, Any] = Field(default_factory=dict)

    trader_id: str | None = None
    idea_id: UUID | None = None
