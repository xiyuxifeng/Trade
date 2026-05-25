from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Uuid, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class JobStatus(StrEnum):
    """Job 的生命周期状态。"""

    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class Job(TimestampMixin, Base):
    """持久化 Job 记录。

    用于后续 Job Center / Worker 统一承载长任务的状态、参数、结果和错误信息。
    """

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_job_type_status", "job_type", "status"),
        Index("ix_jobs_worker_id", "worker_id"),
        UniqueConstraint("idempotency_key", name="uq_jobs_idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobStatus.pending.value,
        server_default=text("'pending'"),
    )
    params: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    progress: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    artifacts: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, default=list, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default=text("3"))
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    timeout_seconds: Mapped[int | None] = mapped_column(Integer)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(64))
    lock_token: Mapped[str | None] = mapped_column(String(128))
    lock_acquired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    audit_events = relationship(
        "JobAuditEvent",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobAuditEvent.created_at",
    )
