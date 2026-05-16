from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class ConfigProfile(TimestampMixin, Base):
    """Profile 的长期配置事实源。

    该模型承载运行配置的正式版本，不再把 `config_path` 作为长期事实源。
    """

    __tablename__ = "config_profiles"
    __table_args__ = (
        Index("ix_config_profiles_environment_validation_status", "environment", "validation_status"),
        Index("ix_config_profiles_updated_at", "updated_at"),
    )

    profile_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    environment: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    sections: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    secret_refs: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default=text("'draft'"))
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
