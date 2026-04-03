from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class MarketData(TimestampMixin, Base):
    __tablename__ = "market_data"
    __table_args__ = (
        Index("ix_market_data_symbol_timeframe_traded_at", "symbol", "timeframe", "traded_at"),
        Index("ix_market_data_market_traded_at", "market", "traded_at"),
        Index("ix_market_data_source_traded_at", "source", "traded_at"),
        Index("ix_market_data_symbol_market_timeframe_source", "symbol", "market", "timeframe", "source"),
        UniqueConstraint(
            "symbol",
            "market",
            "timeframe",
            "traded_at",
            "source",
            name="uq_market_data_symbol_market_timeframe_traded_at_source",
        ),
        CheckConstraint("open >= 0", name="open_non_negative"),
        CheckConstraint("high >= 0", name="high_non_negative"),
        CheckConstraint("low >= 0", name="low_non_negative"),
        CheckConstraint("close >= 0", name="close_non_negative"),
        CheckConstraint("volume >= 0", name="volume_non_negative"),
        CheckConstraint("turnover >= 0", name="turnover_non_negative"),
        CheckConstraint("high >= low", name="high_low_consistent"),
        CheckConstraint("high >= open", name="high_open_consistent"),
        CheckConstraint("high >= close", name="high_close_consistent"),
        CheckConstraint("low <= open", name="low_open_consistent"),
        CheckConstraint("low <= close", name="low_close_consistent"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False, default="CN")
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, default="1d")
    traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    turnover: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    adj_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    is_adjusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    indicators: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
