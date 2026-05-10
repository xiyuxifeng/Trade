from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class JobAuditEvent(TimestampMixin, Base):
    """Job 关键操作的结构化审计记录。"""

    __tablename__ = "job_audit_events"
    __table_args__ = (
        Index("ix_job_audit_events_job_id_created_at", "job_id", "created_at"),
        Index("ix_job_audit_events_operation_created_at", "operation", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    params_summary: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job = relationship("Job", back_populates="audit_events")
