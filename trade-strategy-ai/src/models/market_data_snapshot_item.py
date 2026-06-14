"""Market snapshot item ORM 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class MarketSnapshotItem(TimestampMixin, Base):
    """结构化市场快照明细表。"""

    __tablename__ = "market_snapshot_items"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "section_id", "item_key", name="uq_market_snapshot_items_identity"),
        Index("ix_market_snapshot_items_snapshot_section", "snapshot_id", "section_id"),
        Index("ix_market_snapshot_items_snapshot_symbol", "snapshot_id", "symbol"),
        Index("ix_market_snapshot_items_dataset_id", "dataset_id"),
        Index("ix_market_snapshot_items_section_quality", "section_id", "quality_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    snapshot_id: Mapped[str] = mapped_column(String(128), ForeignKey("market_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(128))
    symbol: Mapped[str | None] = mapped_column(String(32))
    item_key: Mapped[str] = mapped_column(String(128), nullable=False)
    item_type: Mapped[str | None] = mapped_column(String(64))
    source_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "id": str(self.id),
            "snapshot_id": self.snapshot_id,
            "section_id": self.section_id,
            "dataset_id": self.dataset_id,
            "symbol": self.symbol,
            "item_key": self.item_key,
            "item_type": self.item_type,
            "source_time": self.source_time.isoformat() if self.source_time else None,
            "quality_status": self.quality_status,
            "payload_json": self.payload_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
