from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Numeric, String, Uuid
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class MarketData(Base, TimestampMixin):
    __tablename__ = "market_data"
    __table_args__ = (
        Index("ix_market_data_symbol_traded_at", "symbol", "traded_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    turnover: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    adj_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    is_adjusted: Mapped[bool] = mapped_column(nullable=False, default=False)
    indicators: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
