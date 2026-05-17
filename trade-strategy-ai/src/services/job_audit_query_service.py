from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import and_, desc, select

from src.models.job import Job
from src.models.job_audit_event import JobAuditEvent
from src.services.base import BaseService, ServiceResult
from src.services.job_service import _sanitize_audit_data, _to_plain


def _normalize_date(value: date | str | None) -> date | None:
    """把日期参数统一成 date。"""
    if value in {None, ""}:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _parse_job_id(job_id: str | UUID) -> UUID:
    """将字符串 job_id 转成 UUID。"""
    if isinstance(job_id, UUID):
        return job_id
    return UUID(str(job_id))


def _event_confirmed(payload: Any) -> bool | None:
    """从审计 payload 中提取确认标记。"""
    if not isinstance(payload, dict):
        return None
    request_context = payload.get("request_context")
    if isinstance(request_context, dict) and "confirmed" in request_context:
        return bool(request_context.get("confirmed"))
    details = payload.get("details")
    if isinstance(details, dict) and "confirmed" in details:
        return bool(details.get("confirmed"))
    if "confirmed" in payload:
        return bool(payload.get("confirmed"))
    return None


class JobAuditQueryService(BaseService):
    """Job 审计查询服务。"""

    service_name = "job-audit-query"

    def __init__(self, *, session_scope_factory: Callable[[], Any] | None = None) -> None:
        self._session_scope_factory = session_scope_factory

    def _ensure_session_factory(self) -> Callable[[], Any]:
        """确保存在数据库 session_scope 工厂。"""
        if self._session_scope_factory is not None:
            return self._session_scope_factory

        from src.db.session import session_scope

        self._session_scope_factory = session_scope
        return session_scope

    def _error(self, *, status: str, error_type: str, message: str, detail: str | None = None, metadata: dict[str, Any] | None = None) -> ServiceResult:
        """构造结构化错误结果。"""
        return ServiceResult(
            status=status,  # type: ignore[arg-type]
            message=message,
            payload={
                "error": {
                    "type": error_type,
                    "message": message,
                    "detail": detail,
                    "metadata": metadata or {},
                }
            },
        )

    def _serialize_audit_event(self, event: JobAuditEvent, job: Job) -> dict[str, Any]:
        """把审计记录整理成 UI 可直接消费的结构。"""
        confirmed = _event_confirmed(event.payload)
        return {
            "id": str(event.id),
            "job_id": str(event.job_id),
            "job_type": job.job_type,
            "job_status": job.status,
            "created_by": job.created_by,
            "operation": event.operation,
            "actor": event.actor,
            "source": event.source,
            "confirmed": confirmed,
            "params_summary": _sanitize_audit_data(event.params_summary),
            "payload": _sanitize_audit_data(event.payload),
            "event_at": _to_plain(event.event_at),
            "created_at": _to_plain(event.created_at),
            "updated_at": _to_plain(event.updated_at),
        }

    def _serialize_artifact(self, artifact: Any) -> dict[str, Any]:
        """把 Job 产物引用整理成安全结构。"""
        plain = artifact if isinstance(artifact, dict) else {}
        return {
            "artifact_id": str(plain.get("artifact_id") or ""),
            "job_id": str(plain.get("job_id") or ""),
            "workflow_id": plain.get("workflow_id"),
            "step_id": plain.get("step_id"),
            "kind": str(plain.get("kind") or "unknown"),
            "title": str(plain.get("title") or plain.get("kind") or "artifact"),
            "summary": plain.get("summary"),
            "safe_download_url": plain.get("safe_download_url"),
            "download_token": plain.get("download_token"),
            "size_bytes": plain.get("size_bytes"),
            "created_at": plain.get("created_at"),
            "visibility": plain.get("visibility") or "internal",
            "metadata": plain.get("metadata") or {},
            "storage_ref": plain.get("storage_ref"),
        }

    def _serialize_job_summary(self, job: Job) -> dict[str, Any]:
        """把 Job 转成只读审计摘要。"""
        return {
            "id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "created_by": job.created_by,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "retry_backoff_seconds": job.retry_backoff_seconds,
            "timeout_seconds": job.timeout_seconds,
            "cancel_requested": job.cancel_requested,
            "cancel_requested_at": _to_plain(job.cancel_requested_at),
            "worker_id": job.worker_id,
            "lock_acquired_at": _to_plain(job.lock_acquired_at),
            "heartbeat_at": _to_plain(job.heartbeat_at),
            "scheduled_at": _to_plain(job.scheduled_at),
            "started_at": _to_plain(job.started_at),
            "finished_at": _to_plain(job.finished_at),
            "created_at": _to_plain(job.created_at),
            "updated_at": _to_plain(job.updated_at),
            "artifacts": [self._serialize_artifact(artifact) for artifact in (job.artifacts or [])],
        }

    async def _load_job(self, session: Any, job_id: str | UUID) -> Job | None:
        """加载指定 Job。"""
        job_uuid = _parse_job_id(job_id)
        result = await session.execute(select(Job).where(Job.id == job_uuid))
        return result.scalar_one_or_none()

    async def _load_audit_rows(self, session: Any, *, actor: str | None, job_type: str | None, operation: str | None, start_date: date | None, end_date: date | None) -> list[tuple[JobAuditEvent, Job]]:
        """加载满足基础条件的审计记录。"""
        conditions = []
        if actor:
            conditions.append(JobAuditEvent.actor == actor)
        if job_type:
            conditions.append(Job.job_type == job_type)
        if operation:
            conditions.append(JobAuditEvent.operation == operation)
        if start_date is not None:
            conditions.append(JobAuditEvent.event_at >= datetime.combine(start_date, time.min, tzinfo=UTC))
        if end_date is not None:
            conditions.append(JobAuditEvent.event_at <= datetime.combine(end_date, time.max, tzinfo=UTC))

        stmt = (
            select(JobAuditEvent, Job)
            .join(Job, Job.id == JobAuditEvent.job_id)
            .where(and_(*conditions) if conditions else True)
            .order_by(desc(JobAuditEvent.event_at), desc(JobAuditEvent.created_at), desc(JobAuditEvent.id))
        )
        result = await session.execute(stmt)
        return list(result.all())

    async def list_job_audits(
        self,
        *,
        actor: str | None = None,
        job_type: str | None = None,
        operation: str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        confirmed: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ServiceResult:
        """查询 Job 审计记录。"""
        if skip < 0 or limit < 1:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="skip must be >= 0 and limit must be >= 1",
                metadata={"skip": skip, "limit": limit},
            )

        try:
            normalized_start_date = _normalize_date(start_date)
            normalized_end_date = _normalize_date(end_date)
        except ValueError as exc:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid date",
                detail=str(exc),
                metadata={"start_date": start_date, "end_date": end_date},
            )

        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            rows = await self._load_audit_rows(
                session,
                actor=actor,
                job_type=job_type,
                operation=operation,
                start_date=normalized_start_date,
                end_date=normalized_end_date,
            )

        filtered: list[dict[str, Any]] = []
        for event, job in rows:
            confirmed_flag = _event_confirmed(event.payload)
            if confirmed is not None and confirmed_flag is not confirmed:
                continue
            filtered.append(self._serialize_audit_event(event, job))

        total = len(filtered)
        page_items = filtered[skip : skip + limit]
        confirmed_count = sum(1 for item in filtered if item.get("confirmed") is True)
        high_risk_count = confirmed_count
        unique_jobs = len({item["job_id"] for item in filtered})
        operation_counts: dict[str, int] = {}
        for item in filtered:
            op = str(item.get("operation") or "unknown")
            operation_counts[op] = operation_counts.get(op, 0) + 1

        return ServiceResult(
            status="ok",
            message="job audits listed",
            payload={
                "filters": {
                    "actor": actor,
                    "job_type": job_type,
                    "operation": operation,
                    "start_date": normalized_start_date.isoformat() if normalized_start_date else None,
                    "end_date": normalized_end_date.isoformat() if normalized_end_date else None,
                    "confirmed": confirmed,
                },
                "summary": {
                    "total": total,
                    "confirmed_count": confirmed_count,
                    "high_risk_count": high_risk_count,
                    "unique_jobs": unique_jobs,
                    "operation_counts": operation_counts,
                },
                "page": {
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                    "count": len(page_items),
                },
                "items": page_items,
            },
        )

    async def get_job_audit_detail(self, job_id: str | UUID) -> ServiceResult:
        """查询单个 Job 的审计详情。"""
        session_scope = self._ensure_session_factory()
        try:
            job_uuid = _parse_job_id(job_id)
        except ValueError:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid job_id",
                detail=str(job_id),
                metadata={"job_id": str(job_id)},
            )

        async with session_scope() as session:
            job = await self._load_job(session, job_uuid)
            if job is None:
                return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
            audit_rows = await session.execute(
                select(JobAuditEvent).where(JobAuditEvent.job_id == job_uuid).order_by(JobAuditEvent.event_at, JobAuditEvent.created_at, JobAuditEvent.id)
            )
            events = list(audit_rows.scalars().all())

        serialized_events = [self._serialize_audit_event(event, job) for event in events]
        created_event = next((event for event in serialized_events if event["operation"] == "create"), None)
        return ServiceResult(
            status="ok",
            message="job audit detail loaded",
            payload={
                "job": self._serialize_job_summary(job),
                "summary": {
                    "event_count": len(serialized_events),
                    "confirmed_count": sum(1 for item in serialized_events if item.get("confirmed") is True),
                    "high_risk_count": sum(1 for item in serialized_events if item.get("confirmed") is True),
                    "has_artifacts": bool(job.artifacts),
                },
                "request_context": created_event["payload"].get("request_context") if created_event else {},
                "items": serialized_events,
            },
        )
