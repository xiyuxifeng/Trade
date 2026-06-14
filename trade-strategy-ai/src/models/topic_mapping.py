from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class TopicMapping(Base):
    __tablename__ = "topic_mapping"
    __table_args__ = (
        UniqueConstraint("provider", "raw_topic_id", name="uq_topic_mapping_provider_raw_id"),
        Index("ix_topic_mapping_provider", "provider"),
        Index("ix_topic_mapping_canonical", "canonical_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_topic_id: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
