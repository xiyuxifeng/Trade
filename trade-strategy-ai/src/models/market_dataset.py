"""Market dataset ORM 模型。"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, Index, String, UniqueConstraint, Uuid, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class MarketDataset(TimestampMixin, Base):
    """市场数据集主表。"""

    __tablename__ = "market_datasets"
    __table_args__ = (
        UniqueConstraint("dataset_id", name="uq_market_datasets_dataset_id"),
        Index("ix_market_datasets_trade_date_market", "trade_date", "market"),
        Index("ix_market_datasets_snapshot_id", "snapshot_id"),
        Index("ix_market_datasets_type_trade_date", "dataset_type", "trade_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dataset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False, default="CN")
    source: Mapped[str | None] = mapped_column(String(64))
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    snapshot_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("market_snapshots.snapshot_id", ondelete="SET NULL"))
    profile_id: Mapped[str | None] = mapped_column(String(128))
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "id": str(self.id),
            "dataset_id": self.dataset_id,
            "dataset_type": self.dataset_type,
            "trade_date": self.trade_date.isoformat() if isinstance(self.trade_date, date) else self.trade_date,
            "market": self.market,
            "source": self.source,
            "storage_ref": self.storage_ref,
            "snapshot_id": self.snapshot_id,
            "profile_id": self.profile_id,
            "quality_status": self.quality_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
