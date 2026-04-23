from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, Index, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class TopicConstituentsSnapshot(TimestampMixin, Base):
    """题材成分快照。"""

    __tablename__ = "topic_constituents_snapshots"
    __table_args__ = (
        UniqueConstraint("trade_date", "slot", "source", "dataset_version", name="uq_topic_constituents_snapshots_identity"),
        Index("ix_topic_constituents_snapshots_trade_date_slot", "trade_date", "slot"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="kaipan")
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    payload: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, default=list, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
