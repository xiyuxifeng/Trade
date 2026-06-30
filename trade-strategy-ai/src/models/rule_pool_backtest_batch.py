from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class RulePoolBacktestBatchRun(TimestampMixin, Base):
    __tablename__ = "rule_pool_backtest_batch_runs"
    __table_args__ = (
        Index("ix_rpbt_batch_runs_status_created", "status", "created_at"),
        Index("ix_rpbt_batch_runs_fingerprint", "fingerprint"),
    )

    batch_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default=text("'draft'"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    min_confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    market_regime_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selected_rule_count: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    merged_result_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)

    batches = relationship(
        "RulePoolBacktestBatch",
        back_populates="batch_run",
        cascade="all, delete-orphan",
        order_by="RulePoolBacktestBatch.batch_index",
        lazy="selectin",
    )


class RulePoolBacktestBatch(TimestampMixin, Base):
    __tablename__ = "rule_pool_backtest_batches"
    __table_args__ = (
        Index("ix_rpbt_batches_run_index", "batch_run_id", "batch_index", unique=True),
        Index("ix_rpbt_batches_status", "status"),
        Index("ix_rpbt_batches_job_id", "job_id"),
    )

    batch_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    batch_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("rule_pool_backtest_batch_runs.batch_run_id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_index: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_ids_json: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    job_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default=text("'pending'"))
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)
    result_artifact_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    batch_run = relationship("RulePoolBacktestBatchRun", back_populates="batches")
