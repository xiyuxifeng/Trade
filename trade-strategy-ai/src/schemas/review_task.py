from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewTriggerReason(StrEnum):
    """Why a review task was triggered."""

    loss = "loss"                       # 亏损（return_pct < 0）
    below_expected = "below_expected"   # 低于预期收益
    stopped_out = "stopped_out"         # 触发止损
    taken_profit = "taken_profit"       # 触发止盈（特殊记录）


class ReviewWritebackStatus(StrEnum):
    """Status of the review write-back step."""

    pending = "pending"     # 等待复盘结论写回
    written = "written"     # 已写回 TraderMemory
    skipped = "skipped"     # 跳過（无需写回）


class ReviewEvaluationSnapshot(BaseModel):
    """Snapshot of the evaluation state when the review task was created."""

    idea_id: UUID
    symbol: str
    entry_price: float
    current_price: float
    return_pct: float
    threshold: float
    as_of_date: date


class ReviewTaskDetails(BaseModel):
    """Minimum field set for a structured trader review task.

    This formalizes the P2-109A closed loop:
        EvaluationResult → ReviewTask created → Trader writes back review note
    """

    # 触发原因
    review_type: str = "trader_review"
    trigger_reason: ReviewTriggerReason

    # 关联的交易建议
    source_idea_id: UUID
    symbol: str
    trader_id: str

    # 评估快照（创建时固化，后续不再修改）
    evaluation_snapshot: ReviewEvaluationSnapshot

    # 复盘结论写回状态
    writeback_status: ReviewWritebackStatus = ReviewWritebackStatus.pending

    # 复盘结论（由 TraderAgent 或人工填入）
    conclusion: str | None = None
    concluded_at: datetime | None = None
    concluded_by: str | None = None  # "trader_agent" | "human"

    # 关联的写回 memory_id（写回后填入，可追踪）
    memory_id: UUID | None = None
