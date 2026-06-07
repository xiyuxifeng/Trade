from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any, Literal
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
    dataset: str | None = None
    topic_ids: list[str] = Field(default_factory=list)
    indicator_names: list[str] = Field(default_factory=list)
    snapshot_date: date | None = None
    fields: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class DataResponse(BaseModel):
    request_id: UUID
    status: DataResponseStatus
    dataset: str | None = None
    available_datasets: list[str] = Field(default_factory=list)
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

    # Stage 1 追溯字段：用于连接策略版本、主题证据与决策模式
    strategy_version_id: str | None = None
    source_topic_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    decision_mode: str | None = None
    # NTL-S4-008 新增：来源追踪
    source_recommendation_idx: int | None = None  # 来源 recommendation 在版本中的索引位置

    rationale: str | None = None
    invalidation: str | None = None
    confidence: float | None = None  # 0-1

    # Persona routing (Phase 1+)
    style_cluster_id: str | None = None
    style_cluster_label: str | None = None
    style_score: float | None = None
    style_reasons: list[str] = Field(default_factory=list)


class DailyReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    as_of_date: date
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    ideas: list[TradeIdea] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    # NTL-S4-008: 盘前报告级策略版本追溯
    strategy_version_ids: list[str] = Field(default_factory=list)  # 本次生成所用的策略版本 ID 列表

    # 兼容字段：候选池快照（仅用于盘后/回放兼容与内部桥接，不作为新的对外入口）
    market_universe_snapshot: dict[str, Any] | None = None
    # 统一市场上下文快照（对外唯一主语义；盘前 / 盘后 / 回测共用）
    market_context_snapshot: dict[str, Any] | None = None


class EvaluationRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    trader_id: str
    as_of_date: date
    idea_ids: list[UUID] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class IdeaEvaluation(BaseModel):
    """单笔交易评估结果。

    .. deprecated::
        current_price 字段废弃（2026-04-26），语义从"评估时刻快照价"
        改为"exit_price"（bars 收盘价）。保留以兼容外部消费方。

    结构化扩展字段：
    - partial_data：标记是否为部分行情数据
    - fallback_reason：标记降级/缺失的原因，便于报告和日志消费
    """
    idea_id: UUID
    symbol: str
    entry_price: float | None = None
    current_price: float | None = None  # deprecated: 语义变为 exit_price
    return_pct: float | None = None
    status: Literal["ok", "partial", "fallback", "not_evaluated"] = "not_evaluated"
    partial_data: bool = False
    fallback_reason: str | None = None
    notes: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    result_id: UUID = Field(default_factory=uuid4)
    as_of_date: date
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    evaluations: list[IdeaEvaluation] = Field(default_factory=list)
    # Stage 1 盘后扩展字段：用于证据包、归因和 ranking 入口
    evidence_pack_refs: list[str] = Field(default_factory=list)
    failure_categories: list[str] = Field(default_factory=list)
    ranking_features: dict[str, Any] = Field(default_factory=dict)
    postmortem_notes: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class AgentTask(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    type: str
    title: str
    details: dict[str, Any] = Field(default_factory=dict)

    trader_id: str | None = None
    idea_id: UUID | None = None
