from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


@dataclass(frozen=True)
class RegimeEvidenceRecord:
    """Market Regime 标签证据。"""

    feature_key: str
    feature_value: Any
    source_section: str
    source_field: str | None = None
    contribution: float = 0.0
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)


@dataclass(frozen=True)
class RegimeLabelRecord:
    """Market Regime 标签。"""

    label: str
    label_type: str
    score: float
    confidence: float
    status: str
    evidence: list[RegimeEvidenceRecord] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)


@dataclass(frozen=True)
class RegimeFeatureRecord:
    """Market Regime 判定输入特征。"""

    feature_key: str
    raw_value: Any
    normalized_value: Any | None
    source_section: str
    source_field: str | None
    source_version: str
    confidence: float
    weight: float
    missing_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)


class MarketRegimeRecord(TimestampMixin, Base):
    """市场状态主记录。"""

    __tablename__ = "market_regimes"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "regime_version", name="uq_market_regimes_snapshot_regime_version"),
        Index("ix_market_regimes_trade_date_market", "trade_date", "market"),
        Index("ix_market_regimes_snapshot_id", "snapshot_id"),
        Index("ix_market_regimes_regime_version", "regime_version"),
    )

    regime_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(128), ForeignKey("market_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False, default="CN")
    regime_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_feature_version: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_label: Mapped[str] = mapped_column(String(64), nullable=False)
    labels_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, default=list, nullable=False)
    features_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="partial")
    missing_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    def __init__(
        self,
        *,
        regime_id: str,
        snapshot_id: str,
        trade_date: date,
        market: str,
        regime_version: str,
        source_feature_version: str,
        primary_label: str,
        labels: list[RegimeLabelRecord | dict[str, Any]] | None = None,
        features: list[RegimeFeatureRecord | dict[str, Any]] | None = None,
        confidence: float = 0.0,
        quality_status: str = "partial",
        missing_reason: str | None = None,
        storage_ref: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.regime_id = regime_id
        self.snapshot_id = snapshot_id
        self.trade_date = trade_date
        self.market = market
        self.regime_version = regime_version
        self.source_feature_version = source_feature_version
        self.primary_label = primary_label
        self.labels_json = [_to_plain(item) for item in (labels or [])]
        self.features_json = [_to_plain(item) for item in (features or [])]
        self.confidence = confidence
        self.quality_status = quality_status
        self.missing_reason = missing_reason
        self.storage_ref = storage_ref or {}
        if created_at is not None:
            self.created_at = created_at
        if updated_at is not None:
            self.updated_at = updated_at

    @property
    def labels(self) -> list[dict[str, Any]]:
        """返回标签明细。"""
        return self.labels_json

    @property
    def features(self) -> list[dict[str, Any]]:
        """返回特征明细。"""
        return self.features_json

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "regime_id": self.regime_id,
            "snapshot_id": self.snapshot_id,
            "trade_date": self.trade_date.isoformat() if isinstance(self.trade_date, date) else self.trade_date,
            "market": self.market,
            "regime_version": self.regime_version,
            "source_feature_version": self.source_feature_version,
            "primary_label": self.primary_label,
            "labels": self.labels_json,
            "features": self.features_json,
            "confidence": self.confidence,
            "quality_status": self.quality_status,
            "missing_reason": self.missing_reason,
            "storage_ref": self.storage_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
