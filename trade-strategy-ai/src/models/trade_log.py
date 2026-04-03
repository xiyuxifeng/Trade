from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class TradeLog(TimestampMixin, Base):
    __tablename__ = "trade_logs"
    __table_args__ = (
        Index("ix_trade_logs_symbol_executed_at", "symbol", "executed_at"),
        Index("ix_trade_logs_account_executed_at", "account_id", "executed_at"),
        Index("ix_trade_logs_article_executed_at", "article_id", "executed_at"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint("fee >= 0", name="fee_non_negative"),
        CheckConstraint(
            "side IN ('buy', 'sell')",
            name="side_allowed",
        ),
        CheckConstraint(
            "position_side IN ('long', 'short', 'flat')",
            name="position_side_allowed",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False, default="CN")
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    position_side: Mapped[str] = mapped_column(String(10), nullable=False, default="long")
    order_type: Mapped[str | None] = mapped_column(String(20))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    strategy_tag: Mapped[str | None] = mapped_column(String(128))
    rationale: Mapped[str | None] = mapped_column(Text)
    article_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", ondelete="SET NULL"),
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
