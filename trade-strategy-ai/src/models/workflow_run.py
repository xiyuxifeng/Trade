from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class WorkflowRun(TimestampMixin, Base):
    """Workflow 运行主记录。

    作为 workflow execution 的数据库级事实源，承载一次运行的汇总信息、输入、输出和错误。
    """

    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("ix_workflow_runs_workflow_id_created_at", "workflow_id", "created_at"),
        Index("ix_workflow_runs_status_created_at", "status", "created_at"),
        Index("ix_workflow_runs_created_by_created_at", "created_by", "created_at"),
        Index("ix_workflow_runs_trigger_source_created_at", "trigger_source", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workflow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_title: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(64), nullable=False, default="workflow-v1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    trigger_source: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    created_by: Mapped[str | None] = mapped_column(String(64))
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    input_params_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    output_summary_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    steps = relationship(
        "WorkflowRunStep",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        order_by="WorkflowRunStep.step_order",
    )

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "id": str(self.id),
            "workflow_id": self.workflow_id,
            "workflow_title": self.workflow_title,
            "workflow_version": self.workflow_version,
            "status": self.status,
            "trigger_source": self.trigger_source,
            "created_by": self.created_by,
            "confirmed": self.confirmed,
            "idempotency_key": self.idempotency_key,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "input_params_json": self.input_params_json,
            "output_summary_json": self.output_summary_json,
            "error_json": self.error_json,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowRunStep(TimestampMixin, Base):
    """Workflow 运行中的单个 step 明细。"""

    __tablename__ = "workflow_run_steps"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "step_order", name="uq_workflow_run_steps_run_order"),
        Index("ix_workflow_run_steps_workflow_run_id", "workflow_run_id"),
        Index("ix_workflow_run_steps_job_id", "job_id"),
        Index("ix_workflow_run_steps_step_id", "step_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workflow_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_id: Mapped[str] = mapped_column(String(128), nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    job_id: Mapped[str | None] = mapped_column(String(128))
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    artifact_refs_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    workflow_run = relationship("WorkflowRun", back_populates="steps")

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return {
            "id": str(self.id),
            "workflow_run_id": str(self.workflow_run_id),
            "step_id": self.step_id,
            "step_name": self.step_name,
            "step_order": self.step_order,
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "input_json": self.input_json,
            "output_json": self.output_json,
            "error_json": self.error_json,
            "artifact_refs_json": self.artifact_refs_json,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
