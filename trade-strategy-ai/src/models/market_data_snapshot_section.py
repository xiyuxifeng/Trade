"""Market snapshot section ORM 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class MarketSnapshotSection(TimestampMixin, Base):
    """结构化市场快照 section 摘要表。"""

    __tablename__ = "market_snapshot_sections"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "section_id", name="uq_market_snapshot_sections_snapshot_section"),
        Index("ix_market_snapshot_sections_snapshot_quality", "snapshot_id", "quality_status"),
        Index("ix_market_snapshot_sections_section_quality", "section_id", "quality_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    snapshot_id: Mapped[str] = mapped_column(String(128), ForeignKey("market_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    source_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_reason: Mapped[str | None] = mapped_column(String(255))
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="missing")
    section_version: Mapped[str | None] = mapped_column(String(32))
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "id": str(self.id),
            "snapshot_id": self.snapshot_id,
            "section_id": self.section_id,
            "provider": self.provider,
            "source_time": self.source_time.isoformat() if self.source_time else None,
            "record_count": self.record_count,
            "missing_reason": self.missing_reason,
            "quality_status": self.quality_status,
            "section_version": self.section_version,
            "storage_ref": self.storage_ref,
            "payload_json": self.payload_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
