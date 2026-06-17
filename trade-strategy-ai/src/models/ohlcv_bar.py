# src/models/ohlcv_bar.py
"""OHLCVBar 模型 - 日线行情数据"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, Float, String, UniqueConstraint, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class OHLCVBar(TimestampMixin, Base):
    """日线行情数据表

    存储股票每日 OHLCV 数据，用于回测和规则验真。
    """

    __tablename__ = "ohlcv_bars"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "exchange",
            "asset_type",
            "frequency",
            "adjustment_policy",
            "trade_date",
            name="uq_ohlcv_identity_trade_date",
        ),
        Index("ix_ohlcv_symbol", "symbol"),
        Index("ix_ohlcv_trade_date", "trade_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # 标准代码，如 "000001.SZ"
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    source_symbol: Mapped[str | None] = mapped_column(String(32))
    exchange: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False, default="stock")
    frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="1d")
    adjustment_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="unadjusted")
    source: Mapped[str | None] = mapped_column(String(64))
    source_payload_fingerprint: Mapped[str | None] = mapped_column(String(128))
    # 交易日期
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    # 成交额（可选）
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_time_reason: Mapped[str | None] = mapped_column(String(255))
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
