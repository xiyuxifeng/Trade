"""Rule applicability profile ORM models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
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
            "profile_version_no",
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
    rule_version_fingerprint: Mapped[str | None] = mapped_column(String(128))
    rule_version_no: Mapped[int | None] = mapped_column(Integer)
    rule_family_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("rule_families.rule_family_id", name="fk_rap_rule_family", ondelete="SET NULL"),
    )
    rule_family_fingerprint: Mapped[str | None] = mapped_column(String(128))
    frozen_rule_version_ids: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    frozen_rule_version_fingerprints: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    dataset_snapshot_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("dataset_snapshots.dataset_snapshot_id", name="fk_rap_dataset_snapshot", ondelete="SET NULL"),
    )
    dataset_fingerprint: Mapped[str | None] = mapped_column(String(128))
    market_state_definition_version: Mapped[str | None] = mapped_column(String(64))
    market_state_model_version: Mapped[str | None] = mapped_column(String(64))
    market_state_source_version: Mapped[str | None] = mapped_column(String(64))
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
    profile_version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_backtest_run_ids: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    source_backtest_result_ids: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    source_result_fingerprints: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    market_snapshot_ids: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    market_snapshot_fingerprints: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluated_sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage: Mapped[float | None] = mapped_column(nullable=True)
    return_metric: Mapped[float | None] = mapped_column(nullable=True)
    win_rate: Mapped[float | None] = mapped_column(nullable=True)
    maximum_drawdown: Mapped[float | None] = mapped_column(nullable=True)
    recommendation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unavailable")
    data_level: Mapped[str | None] = mapped_column(String(32))
    requested_level: Mapped[str | None] = mapped_column(String(32))
    effective_level: Mapped[str | None] = mapped_column(String(32))
    level_policy_version: Mapped[str | None] = mapped_column(String(64))
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="partial")
    insufficient_sample_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    limitations: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    recommendation_policy_version: Mapped[str | None] = mapped_column(String(64))
    review_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(128))
    supersedes_profile_id: Mapped[UUID | None] = mapped_column(Uuid)
    superseded_by_profile_id: Mapped[UUID | None] = mapped_column(Uuid)
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
        **formal_fields: Any,
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
        json_formal_fields = {
            "frozen_rule_version_ids",
            "frozen_rule_version_fingerprints",
            "source_backtest_run_ids",
            "source_backtest_result_ids",
            "source_result_fingerprints",
            "market_snapshot_ids",
            "market_snapshot_fingerprints",
            "limitations",
            "warnings",
        }
        for key, value in formal_fields.items():
            if hasattr(type(self), key):
                setattr(self, key, _to_plain(value) if key in json_formal_fields else value)
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
            "applicability_profile_id": str(self.applicability_profile_id),
            "rule_id": self.rule_id,
            "rule_version_id": str(self.rule_version_id) if self.rule_version_id else None,
            "rule_version_fingerprint": self.rule_version_fingerprint,
            "rule_version_no": self.rule_version_no,
            "rule_family_id": str(self.rule_family_id) if self.rule_family_id else None,
            "rule_family_fingerprint": self.rule_family_fingerprint,
            "frozen_rule_version_ids": self.frozen_rule_version_ids,
            "frozen_rule_version_fingerprints": self.frozen_rule_version_fingerprints,
            "profile_version": self.profile_version,
            "profile_version_no": self.profile_version_no,
            "source_backtest_id": self.source_backtest_id,
            "source_backtest_run_ids": self.source_backtest_run_ids,
            "source_backtest_result_ids": self.source_backtest_result_ids,
            "source_result_fingerprints": self.source_result_fingerprints,
            "source_rule_version": self.source_rule_version,
            "market_regime_version": self.market_regime_version,
            "market_state_model_version": self.market_state_model_version,
            "market_state_source_version": self.market_state_source_version,
            "source_feature_version": self.source_feature_version,
            "review_status": self.review_status,
            "lifecycle_state": self.lifecycle_state.value if hasattr(self.lifecycle_state, "value") else str(self.lifecycle_state),
            "quality_status": self.quality_status,
            "insufficient_sample_status": self.insufficient_sample_status,
            "min_sample_count": self.min_sample_count,
            "sample_count": self.sample_count,
            "eligible_sample_count": self.eligible_sample_count,
            "evaluated_sample_count": self.evaluated_sample_count,
            "coverage": self.coverage,
            "return_metric": self.return_metric,
            "win_rate": self.win_rate,
            "maximum_drawdown": self.maximum_drawdown,
            "confidence": self.confidence,
            "recommendation_status": self.recommendation_status,
            "data_level": self.data_level,
            "requested_level": self.requested_level,
            "effective_level": self.effective_level,
            "level_policy_version": self.level_policy_version,
            "limitations": self.limitations,
            "warnings": self.warnings,
            "recommendation_policy_version": self.recommendation_policy_version,
            "dataset_snapshot_id": str(self.dataset_snapshot_id) if self.dataset_snapshot_id else None,
            "dataset_fingerprint": self.dataset_fingerprint,
            "market_snapshot_ids": self.market_snapshot_ids,
            "market_snapshot_fingerprints": self.market_snapshot_fingerprints,
            "applicable_regimes": self.applicable_regimes_json,
            "blocked_regimes": self.blocked_regimes_json,
            "neutral_regimes": self.neutral_regimes_json,
            "best_market_conditions": self.best_market_conditions_json,
            "worst_market_conditions": self.worst_market_conditions_json,
            "summary": self.summary_json,
            "storage_ref": self.storage_ref,
            "created_by": self.created_by,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_reason": self.review_reason,
            "supersedes_profile_id": str(self.supersedes_profile_id) if self.supersedes_profile_id else None,
            "superseded_by_profile_id": str(self.superseded_by_profile_id) if self.superseded_by_profile_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RuleApplicabilityProfileAudit(TimestampMixin, Base):
    """Formal RuleApplicabilityProfile state transition audit."""

    __tablename__ = "rule_applicability_profile_audits"
    __table_args__ = (
        Index("ix_rap_audit_profile_created", "profile_id", "created_at"),
        Index("ix_rap_audit_transition", "transition"),
    )

    audit_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("rule_applicability_profiles.profile_id", name="fk_rap_audit_profile", ondelete="CASCADE"),
        nullable=False,
    )
    transition: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    source_surface: Mapped[str] = mapped_column(String(128), nullable=False, default="/rules/backtests")
    before_state_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    after_state_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
