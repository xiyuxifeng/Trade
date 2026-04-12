"""
股票基本信息模型 - 存储 A 股股票名称→代码映射表
用于元数据提取时将中文股票名称转换为标准代码格式
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class StockInfo(TimestampMixin, Base):
    """股票基本信息表

    存储股票的标准代码、中文名称、交易所等信息，
    用于元数据提取时将中文名称映射为标准代码。
    """

    __tablename__ = "stock_info"
    __table_args__ = (
        # 代码唯一
        UniqueConstraint("symbol", name="uq_stock_info_symbol"),
        # 名称可能有重名，但 symbol+market 唯一
        UniqueConstraint("symbol", "market", name="uq_stock_info_symbol_market"),
        # 便于按名称查询
        Index("ix_stock_info_name", "name"),
        # 便于按代码查询
        Index("ix_stock_info_code", "code"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # 标准代码，如 "000001.SZ"、"600519.SH"、"430001.BJ"
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    # 股票代码，如 "000001"、"600519"、"430001"
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    # 交易所：SZ/SH/BJ
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    # 中文名称
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 股票类型：stock/etf/fund/bond
    security_type: Mapped[str] = mapped_column(String(32), nullable=False, default="stock")
    # 更新日期（用于判断是否需要刷新）
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
