from __future__ import annotations

from src.models import Job, JobStatus
from src.models.base import Base


def test_job_table_metadata() -> None:
    """Job 表应包含 Job Center 所需的基础字段。"""
    assert Job.__tablename__ == "jobs"

    column_names = set(Job.__table__.columns.keys())
    assert {
        "job_type",
        "status",
        "params",
        "result",
        "error",
        "artifacts",
        "created_by",
        "idempotency_key",
        "retry_count",
        "max_retries",
        "retry_backoff_seconds",
        "timeout_seconds",
        "cancel_requested",
        "cancel_requested_at",
        "worker_id",
        "lock_token",
        "lock_acquired_at",
        "heartbeat_at",
        "scheduled_at",
        "started_at",
        "finished_at",
    } <= column_names

    constraint_names = {constraint.name for constraint in Job.__table__.constraints}
    assert "uq_jobs_idempotency_key" in constraint_names

    index_names = {index.name for index in Job.__table__.indexes}
    assert "ix_jobs_status_created_at" in index_names
    assert "ix_jobs_job_type_status" in index_names
    assert "ix_jobs_worker_id" in index_names


def test_job_model_is_registered_and_exports_status_enum() -> None:
    """Job 模型应注册到全局 metadata 且导出状态枚举。"""
    assert "jobs" in Base.metadata.tables
    assert JobStatus.pending.value == "pending"
    assert JobStatus.running.value == "running"
    assert JobStatus.success.value == "success"
    assert JobStatus.failed.value == "failed"
    assert JobStatus.cancelled.value == "cancelled"
