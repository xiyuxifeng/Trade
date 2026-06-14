from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class TraderStrategyVersion(TimestampMixin, Base):
    """交易员策略版本表。

    记录每个 trader 每日生成的策略版本、证据来源和发布状态。
    """

    __tablename__ = "trader_strategy_versions"
    __table_args__ = (
        UniqueConstraint(
            "trader_id",
            "strategy_date",
            "version_name",
            name="uq_tsv_trader_dt_ver",
        ),
        Index("ix_trader_strategy_versions_trader_status", "trader_id", "status"),
        Index("ix_trader_strategy_versions_strategy_date", "strategy_date"),
        Index("ix_trader_strategy_versions_version_type", "version_type"),
        Index(
            "ux_trader_strategy_versions_one_released_per_day",
            "trader_id",
            "strategy_date",
            unique=True,
            postgresql_where="status = 'released'",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    trader_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_date: Mapped[date] = mapped_column(Date, nullable=False)
    version_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_article_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    strategy_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    version_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    parent_version_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
