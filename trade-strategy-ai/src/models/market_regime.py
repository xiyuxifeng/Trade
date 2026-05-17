"""Market regime feature ORM 模型。"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class MarketRegimeFeature(TimestampMixin, Base):
    """市场状态特征主表。"""

    __tablename__ = "market_regime_features"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "feature_version", name="uq_market_regime_features_snapshot_feature_version"),
        Index("ix_market_regime_features_trade_date_market", "trade_date", "market"),
        Index("ix_market_regime_features_snapshot_id", "snapshot_id"),
        Index("ix_market_regime_features_feature_version", "feature_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    snapshot_id: Mapped[str] = mapped_column(String(128), ForeignKey("market_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False, default="CN")
    feature_version: Mapped[str] = mapped_column(String(64), nullable=False, default="market-regime-features-v1")
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="partial")
    available_feature_count: Mapped[int] = mapped_column(nullable=False, default=0)
    partial_feature_count: Mapped[int] = mapped_column(nullable=False, default=0)
    missing_feature_count: Mapped[int] = mapped_column(nullable=False, default=0)
    feature_payload_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "id": str(self.id),
            "snapshot_id": self.snapshot_id,
            "trade_date": self.trade_date.isoformat() if isinstance(self.trade_date, date) else self.trade_date,
            "market": self.market,
            "feature_version": self.feature_version,
            "quality_status": self.quality_status,
            "available_feature_count": self.available_feature_count,
            "partial_feature_count": self.partial_feature_count,
            "missing_feature_count": self.missing_feature_count,
            "feature_payload_json": self.feature_payload_json,
            "summary_json": self.summary_json,
            "storage_ref": self.storage_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
