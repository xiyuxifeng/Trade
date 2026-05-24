from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class StrategyRegimeSelection(TimestampMixin, Base):
    """Regime-aware rule selection 的运行摘要主表。"""

    __tablename__ = "strategy_regime_selections"
    __table_args__ = (
        Index("ix_strategy_regime_selections_strategy_version_id", "strategy_version_id"),
        Index("ix_strategy_regime_selections_snapshot_id", "snapshot_id"),
        Index("ix_strategy_regime_selections_market_regime_versions", "market_regime_version", "source_feature_version"),
        Index("ix_strategy_regime_selections_selected_by_created_at", "selected_by", "created_at"),
    )

    selection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_version_id: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    market_regime_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_feature_version: Mapped[str | None] = mapped_column(String(64))
    applicability_profile_version: Mapped[str | None] = mapped_column(String(64))
    selected_rule_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rule_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_rule_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="partial")
    selection_reason: Mapped[str | None] = mapped_column(String(255))
    evidence_json: Mapped[list[str]] = mapped_column(JSONVariant, default=list, nullable=False)
    override_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    selected_by: Mapped[str | None] = mapped_column(String(64))
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    artifact_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "selection_id": self.selection_id,
            "strategy_version_id": self.strategy_version_id,
            "snapshot_id": self.snapshot_id,
            "market_regime_version": self.market_regime_version,
            "source_feature_version": self.source_feature_version,
            "applicability_profile_version": self.applicability_profile_version,
            "selected_rule_count": self.selected_rule_count,
            "skipped_rule_count": self.skipped_rule_count,
            "blocked_rule_count": self.blocked_rule_count,
            "confidence": self.confidence,
            "quality_status": self.quality_status,
            "selection_reason": self.selection_reason,
            "evidence_json": self.evidence_json,
            "override_json": self.override_json,
            "selected_by": self.selected_by,
            "storage_ref": self.storage_ref,
            "artifact_ref": self.artifact_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RegimeRuleSelection(TimestampMixin, Base):
    """Regime-aware rule selection 的单条规则结果明细。"""

    __tablename__ = "regime_rule_selections"
    __table_args__ = (
        UniqueConstraint("selection_id", "rule_id", name="uq_regime_rule_selections_selection_rule"),
        Index("ix_regime_rule_selections_selection_id", "selection_id"),
        Index("ix_regime_rule_selections_rule_id", "rule_id"),
        Index("ix_regime_rule_selections_decision", "decision"),
        Index("ix_regime_rule_selections_regime_version", "regime_version"),
    )

    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    selection_id: Mapped[str] = mapped_column(String(64), ForeignKey("strategy_regime_selections.selection_id", ondelete="CASCADE"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reason: Mapped[str | None] = mapped_column(String(255))
    evidence_json: Mapped[list[str]] = mapped_column(JSONVariant, default=list, nullable=False)
    regime_version: Mapped[str] = mapped_column(String(64), nullable=False)
    applicability_profile_version: Mapped[str | None] = mapped_column(String(64))
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    profile_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    override_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rule_applicability_profile_id: Mapped[str | None] = mapped_column(String(64))

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "item_id": self.item_id,
            "selection_id": self.selection_id,
            "rule_id": self.rule_id,
            "decision": self.decision,
            "score": self.score,
            "reason": self.reason,
            "evidence_json": self.evidence_json,
            "regime_version": self.regime_version,
            "applicability_profile_version": self.applicability_profile_version,
            "sample_count": self.sample_count,
            "profile_confidence": self.profile_confidence,
            "override_applied": self.override_applied,
            "rule_applicability_profile_id": self.rule_applicability_profile_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
