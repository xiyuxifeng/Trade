from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TraderMemoryType(str, Enum):
    """Memory categories written back by the manager loop."""

    success_case = "success_case"
    failure_case = "failure_case"
    review_note = "review_note"


class TraderMemoryItem(BaseModel):
    """One persisted trader memory entry."""

    memory_id: UUID = Field(default_factory=uuid4)
    trader_id: str
    memory_type: TraderMemoryType
    as_of_date: date

    symbol: str | None = None
    title: str
    content: str
    source: str = "manager"
    source_ref: str | None = None
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5

    # P2-103: Soft delete support
    archived: bool = False
    archived_at: datetime | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TraderMemoryFilter(BaseModel):
    """Filter criteria for querying trader memories."""

    trader_id: str
    memory_types: list[TraderMemoryType] | None = None
    symbol: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    keyword: str | None = None  # 搜索 title + content
    include_archived: bool = False
    limit: int = 50
    offset: int = 0


class TraderMemorySummary(BaseModel):
    """Compact summary returned to the TraderAgent for prompt injection."""

    trader_id: str
    symbol: str | None = None
    total_items: int = 0
    total_symbol_items: int = 0
    archived_items: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    recent_titles: list[str] = Field(default_factory=list)
    symbol_titles: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
