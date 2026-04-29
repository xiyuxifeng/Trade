# src/models/indicator.py
"""Indicator 模型 - 技术指标数据（按需计算更新）"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Float, String, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Indicator(Base):
    """技术指标数据表

    按需计算并存储，支持后续回测和规则验真。
    """

    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_indicator_symbol_date"),
        Index("ix_indicator_symbol", "symbol"),
        Index("ix_indicator_trade_date", "trade_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # 标准代码
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    # 交易日期
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    # RSI
    rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MACD 柱状图
    macd_histogram: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 布林带宽度
    bb_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    # CCI
    cci: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MA50
    ma50: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MA200
    ma200: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 随机指标 K
    stoch_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 量比
    volume_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 价格相对均线比率
    price_vs_ma: Mapped[float | None] = mapped_column(Float, nullable=True)
    # ATR 比率
    atr_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 收盘位置
    close_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 计算时间
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
