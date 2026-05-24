from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Date, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class BacktestResultRun(TimestampMixin, Base):
    """3 年回测结果摘要与索引主表。"""

    __tablename__ = "backtest_result_runs"
    __table_args__ = (
        UniqueConstraint("source_job_id", name="uq_backtest_result_runs_source_job_id"),
        Index("ix_backtest_result_runs_trader_date", "request_trader_id", "request_date_from", "request_date_to"),
        Index("ix_backtest_result_runs_strategy_date", "strategy_version_id", "request_date_from", "request_date_to"),
        Index("ix_backtest_result_runs_regime_versions", "regime_version", "source_feature_version"),
        Index("ix_backtest_result_runs_benchmark_date", "benchmark_symbol", "request_date_from"),
        Index("ix_backtest_result_runs_created_at", "created_at"),
    )

    result_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    request_trader_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version_id: Mapped[str | None] = mapped_column(String(128))
    request_date_from: Mapped[date] = mapped_column(Date, nullable=False)
    request_date_to: Mapped[date] = mapped_column(Date, nullable=False)
    benchmark_symbol: Mapped[str | None] = mapped_column(String(32))
    regime_version: Mapped[str | None] = mapped_column(String(64))
    source_feature_version: Mapped[str | None] = mapped_column(String(64))
    mode: Mapped[str | None] = mapped_column(String(32))
    scoring_profile: Mapped[str | None] = mapped_column(String(64))
    result_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    total_days: Mapped[int | None] = mapped_column(Integer)
    total_trades: Mapped[int | None] = mapped_column(Integer)
    valid_trades: Mapped[int | None] = mapped_column(Integer)
    skipped_trades: Mapped[int | None] = mapped_column(Integer)
    win_rate: Mapped[float | None] = mapped_column(Float)
    avg_return_pct: Mapped[float | None] = mapped_column(Float)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    regime_metrics_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, default=list, nullable=False)
    rule_regime_metrics_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    artifact_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "result_run_id": self.result_run_id,
            "source_job_id": self.source_job_id,
            "job_type": self.job_type,
            "request_trader_id": self.request_trader_id,
            "strategy_version_id": self.strategy_version_id,
            "request_date_from": self.request_date_from.isoformat() if isinstance(self.request_date_from, date) else self.request_date_from,
            "request_date_to": self.request_date_to.isoformat() if isinstance(self.request_date_to, date) else self.request_date_to,
            "benchmark_symbol": self.benchmark_symbol,
            "regime_version": self.regime_version,
            "source_feature_version": self.source_feature_version,
            "mode": self.mode,
            "scoring_profile": self.scoring_profile,
            "result_version": self.result_version,
            "status": self.status,
            "quality_status": self.quality_status,
            "total_days": self.total_days,
            "total_trades": self.total_trades,
            "valid_trades": self.valid_trades,
            "skipped_trades": self.skipped_trades,
            "win_rate": self.win_rate,
            "avg_return_pct": self.avg_return_pct,
            "summary_json": self.summary_json,
            "regime_metrics_json": self.regime_metrics_json,
            "rule_regime_metrics_json": self.rule_regime_metrics_json,
            "fingerprint": self.fingerprint,
            "storage_ref": self.storage_ref,
            "artifact_ref": self.artifact_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
