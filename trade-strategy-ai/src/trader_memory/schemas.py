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
    postmortem = "postmortem"                        # 新增：盘后复盘结论
    strategy_adjustment = "strategy_adjustment"     # 新增：策略调整建议
    market_regime_note = "market_regime_note"        # 新增：市场状态备注


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

    # 新增：交易上下文关联
    idea_id: UUID | None = None
    strategy_version_id: str | None = None
    ranking_entry_id: UUID | None = None

    # 新增：topic 关联（NTL-S5-006）
    topic_source: str | None = None                        # provider 名称，如 "kaipan"
    raw_topic_ids: dict[str, list[str]] | None = None     # {provider: [raw_topic_id, ...]}

    # 新增：盘后评估数据
    postmortem_data: dict | None = None
    strategy_adjustment_data: dict | None = None
    market_regime_data: dict | None = None

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

    # 新增：检索过滤（NTL-S5-006）
    tags: list[str] | None = None               # 按标签检索（匹配任一 tag 即可）
    strategy_version_id: str | None = None     # 按策略版本检索


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

    # 新增字段
    postmortem_notes: list[str] = Field(default_factory=list)
    strategy_adjustments: list[str] = Field(default_factory=list)
    market_regime_notes: list[str] = Field(default_factory=list)
