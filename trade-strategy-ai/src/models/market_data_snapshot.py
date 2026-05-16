"""Market snapshot ORM 模型。"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class MarketSnapshot(TimestampMixin, Base):
    """结构化市场快照主表。"""

    __tablename__ = "market_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_id", name="uq_market_snapshots_snapshot_id"),
        Index("ix_market_snapshots_trade_date_market", "trade_date", "market"),
        Index("ix_market_snapshots_profile_trade_date", "profile_id", "trade_date"),
        Index("ix_market_snapshots_quality_status_trade_date", "quality_status", "trade_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False, default="CN")
    profile_id: Mapped[str | None] = mapped_column(String(128))
    data_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    slot: Mapped[str] = mapped_column(String(16), nullable=False, default="17-30")
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="partial")
    provider_sources: Mapped[list[str]] = mapped_column(JSONVariant, default=list, nullable=False)
    section_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_section_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    partial_section_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_section_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    summary_artifact_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    quality_artifact_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    data_quality: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    sections: Mapped[list[Any]] = relationship(
        "MarketSnapshotSection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "id": str(self.id),
            "snapshot_id": self.snapshot_id,
            "trade_date": self.trade_date.isoformat() if isinstance(self.trade_date, date) else self.trade_date,
            "market": self.market,
            "profile_id": self.profile_id,
            "data_version": self.data_version,
            "slot": self.slot,
            "quality_status": self.quality_status,
            "provider_sources": self.provider_sources,
            "section_count": self.section_count,
            "available_section_count": self.available_section_count,
            "partial_section_count": self.partial_section_count,
            "missing_section_count": self.missing_section_count,
            "storage_ref": self.storage_ref,
            "summary_artifact_ref": self.summary_artifact_ref,
            "quality_artifact_ref": self.quality_artifact_ref,
            "data_quality": self.data_quality,
            "sections": {
                section.section_id: section.to_dict() if hasattr(section, "to_dict") else section
                for section in (self.sections or [])
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
