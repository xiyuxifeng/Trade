"""Rule applicability profile ORM models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin
from src.domain.enums import FormalLifecycleState
from src.models.stage2_canonical import RuleApplicabilityResultStatus, _enum


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
    if isinstance(value, UUID):
        return str(value)
    return value


@dataclass(frozen=True)
class RuleApplicabilityRegimeRecord:
    """单个 regime 的适用性判断记录。"""

    regime_label: str
    decision: str
    score: float
    sample_count: int
    win_rate: float | None
    avg_return: float | None
    avg_win_return: float | None
    avg_loss_return: float | None
    max_drawdown: float | None
    profit_factor: float | None
    confidence: float
    low_sample: bool
    reason: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)


class RuleApplicabilityProfile(TimestampMixin, Base):
    """Rule 适用性画像。"""

    __tablename__ = "rule_applicability_profiles"
    __table_args__ = (
        UniqueConstraint(
            "rule_id",
            "profile_version",
            "source_backtest_id",
            name="uq_rule_applicability_profiles_rule_profile_source",
        ),
        Index("ix_rule_applicability_profiles_rule_id", "rule_id"),
        Index("ix_rule_applicability_profiles_profile_version", "profile_version"),
        Index("ix_rule_applicability_profiles_source_backtest_id", "source_backtest_id"),
        Index("ix_rule_applicability_profiles_review_status", "review_status"),
        Index("ix_rule_applicability_profiles_created_at", "created_at"),
        UniqueConstraint(
            "applicability_profile_id",
            name="uq_rap_applicability_profile_id",
        ),
    )

    profile_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    applicability_profile_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, default=uuid4)
    rule_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("rule_versions.rule_version_id", name="fk_rap_rule_version", ondelete="SET NULL"),
    )
    dataset_snapshot_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("dataset_snapshots.dataset_snapshot_id", name="fk_rap_dataset_snapshot", ondelete="SET NULL"),
    )
    market_state_definition_version: Mapped[str | None] = mapped_column(String(64))
    lifecycle_state: Mapped[FormalLifecycleState] = mapped_column(
        _enum(FormalLifecycleState, "formal_lifecycle"),
        nullable=False,
        default=FormalLifecycleState.draft,
    )
    result_status: Mapped[RuleApplicabilityResultStatus] = mapped_column(
        _enum(RuleApplicabilityResultStatus, "rule_applicability_result_status"),
        nullable=False,
        default=RuleApplicabilityResultStatus.partial,
    )
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    profile_version: Mapped[str] = mapped_column(String(64), nullable=False, default="rule-applicability-v1")
    source_backtest_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_rule_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_regime_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_feature_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    min_sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    applicable_regimes_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, nullable=False, default=list)
    blocked_regimes_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, nullable=False, default=list)
    neutral_regimes_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, nullable=False, default=list)
    best_market_conditions_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    worst_market_conditions_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __init__(
        self,
        *,
        profile_id: UUID | None = None,
        rule_id: str,
        profile_version: str,
        source_backtest_id: str,
        source_rule_version: str | None = None,
        market_regime_version: str | None = None,
        source_feature_version: str | None = None,
        review_status: str = "draft",
        min_sample_count: int = 5,
        confidence: float = 0.0,
        applicable_regimes: list[RuleApplicabilityRegimeRecord | dict[str, Any]] | None = None,
        blocked_regimes: list[RuleApplicabilityRegimeRecord | dict[str, Any]] | None = None,
        neutral_regimes: list[RuleApplicabilityRegimeRecord | dict[str, Any]] | None = None,
        best_market_conditions: dict[str, Any] | None = None,
        worst_market_conditions: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        storage_ref: dict[str, Any] | None = None,
        reviewed_by: str | None = None,
        reviewed_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.profile_id = profile_id or uuid4()
        self.rule_id = rule_id
        self.profile_version = profile_version
        self.source_backtest_id = source_backtest_id
        self.source_rule_version = source_rule_version
        self.market_regime_version = market_regime_version
        self.source_feature_version = source_feature_version
        self.review_status = review_status
        self.min_sample_count = min_sample_count
        self.confidence = confidence
        self.applicable_regimes_json = [_to_plain(item) for item in (applicable_regimes or [])]
        self.blocked_regimes_json = [_to_plain(item) for item in (blocked_regimes or [])]
        self.neutral_regimes_json = [_to_plain(item) for item in (neutral_regimes or [])]
        self.best_market_conditions_json = _to_plain(best_market_conditions or {})
        self.worst_market_conditions_json = _to_plain(worst_market_conditions or {})
        self.summary_json = _to_plain(summary or {})
        self.storage_ref = _to_plain(storage_ref or {})
        self.reviewed_by = reviewed_by
        self.reviewed_at = reviewed_at
        if created_at is not None:
            self.created_at = created_at
        if updated_at is not None:
            self.updated_at = updated_at

    @property
    def applicable_regimes(self) -> list[dict[str, Any]]:
        """返回适用 regime 明细。"""
        return self.applicable_regimes_json

    @property
    def blocked_regimes(self) -> list[dict[str, Any]]:
        """返回禁用 regime 明细。"""
        return self.blocked_regimes_json

    @property
    def neutral_regimes(self) -> list[dict[str, Any]]:
        """返回中性 regime 明细。"""
        return self.neutral_regimes_json

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "profile_id": str(self.profile_id),
            "rule_id": self.rule_id,
            "profile_version": self.profile_version,
            "source_backtest_id": self.source_backtest_id,
            "source_rule_version": self.source_rule_version,
            "market_regime_version": self.market_regime_version,
            "source_feature_version": self.source_feature_version,
            "review_status": self.review_status,
            "min_sample_count": self.min_sample_count,
            "confidence": self.confidence,
            "applicable_regimes": self.applicable_regimes_json,
            "blocked_regimes": self.blocked_regimes_json,
            "neutral_regimes": self.neutral_regimes_json,
            "best_market_conditions": self.best_market_conditions_json,
            "worst_market_conditions": self.worst_market_conditions_json,
            "summary": self.summary_json,
            "storage_ref": self.storage_ref,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
