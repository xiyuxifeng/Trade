"""Market data quality report ORM 模型。"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Index, String, UniqueConstraint, Uuid, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class MarketDataQualityReport(TimestampMixin, Base):
    """市场数据质量报告。"""

    __tablename__ = "market_data_quality_reports"
    __table_args__ = (
        UniqueConstraint("snapshot_id", name="uq_market_data_quality_reports_snapshot_id"),
        Index("ix_market_data_quality_reports_status_created_at", "overall_status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    snapshot_id: Mapped[str] = mapped_column(String(128), ForeignKey("market_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(32), nullable=False, default="partial")
    warning_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(default=0, nullable=False)
    section_summary_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    report_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "id": str(self.id),
            "snapshot_id": self.snapshot_id,
            "overall_status": self.overall_status,
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "section_summary_json": self.section_summary_json,
            "report_json": self.report_json,
            "storage_ref": self.storage_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
