from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import selectinload

from src.services.config_service import ConfigService
from src.services.config_snapshot_service import ConfigSnapshotService
from src.services.config_profile_service import ConfigProfileService
from src.models.job_audit_event import JobAuditEvent
from src.models.job import Job, JobStatus
from src.services.base import BaseService, ServiceResult
from src.common.paths import resolve_project_path
from src.services.runtime_contracts import ArtifactRef, StorageRef
from src.services.step_timeline_service import StepTimelineService


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    return value


def _parse_job_id(job_id: str | UUID) -> UUID:
    """将字符串或 UUID 转换为 UUID 对象。"""
    if isinstance(job_id, UUID):
        return job_id
    return UUID(str(job_id))


def _sanitize_audit_data(value: Any) -> Any:
    """把审计 payload 变成可安全展示的结构化数据。"""
    plain = _to_plain(value)
    if isinstance(plain, dict):
        return ConfigService().mask_config(plain)
    if isinstance(plain, list):
        return [_sanitize_audit_data(item) for item in plain]
    return plain


_SENSITIVE_RESULT_PATH_KEYS = {
    "html_path",
    "market_state_path",
    "quality_report_path",
    "result_path",
    "snapshot_path",
    "snapshot_summary_path",
}


def _sanitize_result_payload_for_output(payload: dict[str, Any]) -> dict[str, Any]:
    """把落盘的 job result 脱敏，避免暴露绝对路径。"""

    def _sanitize(value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {item_key: _sanitize(item_value, item_key) for item_key, item_value in value.items()}
        if isinstance(value, list):
            return [_sanitize(item) for item in value]
        if key in _SENSITIVE_RESULT_PATH_KEYS and isinstance(value, (str, Path)):
            return Path(value).name
        return value

    return _sanitize(_to_plain(payload))


class JobService(BaseService):
    """Job Center 的数据库服务。"""

    service_name = "job"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        job_base_dir: str | Path = resolve_project_path("data/jobs"),
        config_snapshot_service: ConfigSnapshotService | None = None,
        config_profile_service: ConfigProfileService | None = None,
        step_timeline_service: StepTimelineService | None = None,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._job_base_dir = resolve_project_path(job_base_dir)
        self._config_snapshot_service = config_snapshot_service or ConfigSnapshotService()
        self._config_profile_service = config_profile_service or ConfigProfileService()
        self._step_timeline_service = step_timeline_service or StepTimelineService()

    def _ensure_session_factory(self) -> Callable[[], Any]:
        """确保存在数据库 session_scope 工厂。"""
        if self._session_scope_factory is not None:
            return self._session_scope_factory

        from src.db.session import session_scope

        self._session_scope_factory = session_scope
        return session_scope

    def _job_dir(self, job_id: UUID) -> Path:
        """返回 job 的文件目录。"""
        return self._job_base_dir / str(job_id)

    def _log_path(self, job_id: UUID) -> Path:
        """返回 job 的日志文件路径。"""
        return self._job_dir(job_id) / "job.log"

    def _params_path(self, job_id: UUID) -> Path:
        """返回 job 的参数快照文件路径。"""
        return self._job_dir(job_id) / "params.json"

    def _result_path(self, job_id: UUID) -> Path:
        """返回 job 的结果文件路径。"""
        return self._job_dir(job_id) / "result.json"

    def _artifacts_path(self, job_id: UUID) -> Path:
        """返回 job 的产物引用文件路径。"""
        return self._job_dir(job_id) / "artifacts.json"

    def _config_snapshot_path(self, job_id: UUID) -> Path:
        """返回 job 的配置快照文件路径。"""
        return self._job_dir(job_id) / "config_snapshot.json"

    def _profile_snapshot_path(self, job_id: UUID) -> Path:
        """返回 job 的 Profile 快照文件路径。"""
        return self._job_dir(job_id) / "profile_snapshot.json"

    def _write_json_file(self, path: Path, payload: Any) -> None:
        """把结构化 payload 写入 JSON 文件。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_to_plain(payload), ensure_ascii=False, indent=2), encoding="utf-8")

    def _artifact_safe_download_url(self, artifact_id: str) -> str:
        """返回统一的 artifact 下载地址。"""
        return f"/api/ui/v1/artifacts/{artifact_id}/download"

    def _serialize_artifact(self, artifact: Any) -> dict[str, Any]:
        """把 job.artifacts 中的单条记录规范化为单一契约。"""
        plain = _to_plain(artifact)
        if not isinstance(plain, dict):
            return {"metadata": {}, "kind": "unknown", "title": "unknown"}

        artifact_id = plain.get("artifact_id")
        if not artifact_id:
            raw_path = str(plain.get("path") or plain.get("download_name") or plain.get("title") or plain.get("kind") or "artifact")
            artifact_id = hashlib.sha256(raw_path.encode("utf-8")).hexdigest()[:16]

        storage_ref_data = plain.get("storage_ref")
        if isinstance(storage_ref_data, dict):
            storage_ref = storage_ref_data
        else:
            raw_path = plain.get("path")
            storage_ref = None
            if raw_path:
                path = Path(str(raw_path))
                storage_ref = StorageRef(
                    source="file",
                    logical_id=artifact_id,
                    relative_path=path.name if path.name else None,
                ).model_dump(mode="json")

        artifact_ref = ArtifactRef(
            artifact_id=str(artifact_id),
            job_id=str(plain.get("job_id") or "unknown"),
            workflow_id=plain.get("workflow_id"),
            step_id=plain.get("step_id"),
            kind=str(plain.get("kind") or "unknown"),
            title=str(plain.get("title") or plain.get("name") or plain.get("kind") or "artifact"),
            summary=plain.get("summary"),
            safe_download_url=plain.get("safe_download_url") or self._artifact_safe_download_url(str(artifact_id)),
            download_token=plain.get("download_token"),
            size_bytes=plain.get("size_bytes"),
            visibility=plain.get("visibility") or "internal",
            metadata=plain.get("metadata") or {},
            storage_ref=StorageRef.model_validate(storage_ref) if storage_ref is not None else None,
        )
        return artifact_ref.model_dump(mode="json")

    def _serialize_audit_event(self, event: JobAuditEvent) -> dict[str, Any]:
        """把 Job 审计记录转成 API 可用结构。"""
        return {
            "id": str(event.id),
            "job_id": str(event.job_id),
            "operation": event.operation,
            "actor": event.actor,
            "source": event.source,
            "params_summary": _sanitize_audit_data(event.params_summary),
            "payload": _sanitize_audit_data(event.payload),
            "event_at": _to_plain(event.event_at),
            "created_at": _to_plain(event.created_at),
            "updated_at": _to_plain(event.updated_at),
        }

    def _materialize_job_dir(
        self,
        *,
        job: Job,
        result_payload: dict[str, Any] | None = None,
        config_snapshot_payload: dict[str, Any] | None = None,
        profile_snapshot_payload: dict[str, Any] | None = None,
    ) -> None:
        """把 Job 的文件目录统一落盘。

        目录约定：
        - job.log: 任务日志
        - params.json: 创建时的参数快照
        - result.json: 最终执行结果或错误摘要
        - artifacts.json: 产物引用列表
        """
        job_dir = self._job_dir(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._log_path(job.id)
        if not log_path.exists():
            log_path.write_text("", encoding="utf-8")

        self._write_json_file(self._params_path(job.id), job.params or {})
        self._write_json_file(self._artifacts_path(job.id), job.artifacts or [])
        if config_snapshot_payload is None:
            config_snapshot_payload = self._load_config_snapshot(job.id)
        if profile_snapshot_payload is None:
            profile_snapshot_payload = self._load_profile_snapshot(job.id)
        if config_snapshot_payload is not None:
            self._write_json_file(self._config_snapshot_path(job.id), config_snapshot_payload)
        if profile_snapshot_payload is not None:
            self._write_json_file(self._profile_snapshot_path(job.id), profile_snapshot_payload)
        if result_payload is not None:
            self._write_json_file(self._result_path(job.id), _sanitize_result_payload_for_output(result_payload))

    def _load_config_snapshot(self, job_id: UUID) -> dict[str, Any] | None:
        """从 job 目录读取配置快照摘要。"""
        snapshot_path = self._config_snapshot_path(job_id)
        if not snapshot_path.exists():
            return None
        return json.loads(snapshot_path.read_text(encoding="utf-8"))

    def _load_profile_snapshot(self, job_id: UUID) -> dict[str, Any] | None:
        """从 job 目录读取 Profile 快照摘要。"""
        snapshot_path = self._profile_snapshot_path(job_id)
        if not snapshot_path.exists():
            return None
        return json.loads(snapshot_path.read_text(encoding="utf-8"))

    def _job_path_payload(self, job_id: UUID) -> dict[str, Any]:
        """构造 Job 文件路径返回结构。"""
        config_snapshot_path = self._config_snapshot_path(job_id)
        profile_snapshot_path = self._profile_snapshot_path(job_id)
        return {
            "job_dir": str(self._job_dir(job_id)),
            "log_path": str(self._log_path(job_id)),
            "params_path": str(self._params_path(job_id)),
            "result_path": str(self._result_path(job_id)),
            "artifacts_path": str(self._artifacts_path(job_id)),
            "config_snapshot_path": str(config_snapshot_path) if self._load_config_snapshot(job_id) is not None else None,
            "profile_snapshot_path": str(profile_snapshot_path) if self._load_profile_snapshot(job_id) is not None else None,
        }

    def _serialize_job(self, job: Job) -> dict[str, Any]:
        """把 Job ORM 对象转成前端可用结构。"""
        config_snapshot = self._load_config_snapshot(job.id)
        profile_snapshot = self._load_profile_snapshot(job.id)
        artifacts = [self._serialize_artifact(artifact) for artifact in (job.artifacts or [])]
        return {
            "id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "params": _to_plain(job.params),
            "result": _to_plain(job.result),
            "error": _to_plain(job.error),
            "artifacts": artifacts,
            "created_by": job.created_by,
            "idempotency_key": job.idempotency_key,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "retry_backoff_seconds": job.retry_backoff_seconds,
            "timeout_seconds": job.timeout_seconds,
            "cancel_requested": job.cancel_requested,
            "cancel_requested_at": _to_plain(job.cancel_requested_at),
            "worker_id": job.worker_id,
            "lock_token": job.lock_token,
            "lock_acquired_at": _to_plain(job.lock_acquired_at),
            "heartbeat_at": _to_plain(job.heartbeat_at),
            "scheduled_at": _to_plain(job.scheduled_at),
            "started_at": _to_plain(job.started_at),
            "finished_at": _to_plain(job.finished_at),
            "config_snapshot_path": str(self._config_snapshot_path(job.id)) if config_snapshot is not None else None,
            "config_snapshot": config_snapshot,
            "profile_snapshot_path": str(self._profile_snapshot_path(job.id)) if profile_snapshot is not None else None,
            "profile_snapshot": profile_snapshot,
            "audit_events": [self._serialize_audit_event(event) for event in getattr(job, "audit_events", [])],
            "created_at": _to_plain(job.created_at),
            "updated_at": _to_plain(job.updated_at),
        }

    async def _load_job(self, session: Any, job_id: str | UUID) -> Job | None:
        """从数据库加载 Job。"""
        job_uuid = _parse_job_id(job_id)
        stmt = select(Job).options(selectinload(Job.audit_events)).where(Job.id == job_uuid)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _record_job_audit(
        self,
        *,
        session: Any,
        job: Job,
        operation: str,
        actor: str | None,
        audit_source: dict[str, Any] | None,
        params_summary: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        event_at: datetime | None = None,
    ) -> JobAuditEvent:
        """写入一条 Job 操作审计。"""
        source = audit_source or {}
        event = JobAuditEvent(
            job_id=job.id,
            operation=operation,
            actor=actor or job.created_by or "system",
            source=str(source.get("channel") or "system"),
            params_summary=_sanitize_audit_data(params_summary or {}),
            payload=_sanitize_audit_data({"request_context": source, "details": payload or {}}),
            event_at=event_at or datetime.now(UTC),
        )
        session.add(event)
        audit_events = job.__dict__.setdefault("audit_events", [])
        if event not in audit_events:
            audit_events.append(event)
        await session.flush()
        return event

    async def _persist(self, session: Any, job: Job) -> None:
        """刷新并写回数据库。"""
        job.updated_at = datetime.now(UTC)
        await session.flush()

    async def create_job(
        self,
        *,
        job_type: str,
        params: dict[str, Any] | None = None,
        created_by: str | None = None,
        idempotency_key: str | None = None,
        max_retries: int = 3,
        retry_backoff_seconds: int = 0,
        timeout_seconds: int | None = None,
        confirmed: bool = False,
        scheduled_at: datetime | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """创建新的 Job 记录。"""
        session_scope = self._ensure_session_factory()
        config_snapshot_payload: dict[str, Any] | None = None
        profile_snapshot_payload: dict[str, Any] | None = None
        config_path_value = (params or {}).get("config_path")
        profile_id_value = (params or {}).get("profile_id")
        if idempotency_key:
            async with session_scope() as session:
                stmt = select(Job).options(selectinload(Job.audit_events)).where(Job.idempotency_key == idempotency_key)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing is not None:
                    self._materialize_job_dir(job=existing)
                    return ServiceResult(
                        status="ok",
                        message="job already exists",
                        payload={"created": False, **self._job_path_payload(existing.id), "job": self._serialize_job(existing)},
                    )

        job_id = uuid4()
        if profile_id_value is not None:
            snapshot_result = await self._config_profile_service.capture_profile_snapshot(
                str(profile_id_value),
                job_id=str(job_id),
                source="job",
                config_path=config_path_value,
            )
            if snapshot_result.status != "ok":
                return ServiceResult(
                    status="error",
                    message=snapshot_result.message or "profile snapshot capture failed",
                    payload=snapshot_result.payload,
                    warnings=snapshot_result.warnings,
                )
            profile_snapshot_payload = snapshot_result.payload
        elif config_path_value is not None:
            snapshot_result = self._config_snapshot_service.capture_config_snapshot(config_path_value)
            if snapshot_result.status != "ok":
                return ServiceResult(
                    status="error",
                    message=snapshot_result.message or "config snapshot capture failed",
                    payload=snapshot_result.payload,
                    warnings=snapshot_result.warnings,
                )
            config_snapshot_payload = snapshot_result.payload
        now = datetime.now(UTC)
        job = Job(
            id=job_id,
            job_type=job_type,
            status=JobStatus.pending.value,
            params=params or {},
            result=None,
            error=None,
            artifacts=[],
            created_by=created_by or "system",
            idempotency_key=idempotency_key,
            retry_count=0,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            timeout_seconds=timeout_seconds,
            cancel_requested=False,
            cancel_requested_at=None,
            worker_id=None,
            lock_token=None,
            lock_acquired_at=None,
            heartbeat_at=None,
            scheduled_at=scheduled_at,
            started_at=None,
            finished_at=None,
            created_at=now,
            updated_at=now,
        )

        async with session_scope() as session:
            session.add(job)
            await self._persist(session, job)
            await self._record_job_audit(
                session=session,
                job=job,
                operation="create",
                actor=created_by,
                audit_source={**(audit_source or {}), "confirmed": confirmed},
                params_summary=params or {},
                payload={
                    "job_type": job_type,
                    "idempotency_key": idempotency_key,
                    "max_retries": max_retries,
                    "retry_backoff_seconds": retry_backoff_seconds,
                    "timeout_seconds": timeout_seconds,
                    "confirmed": confirmed,
                    "scheduled_at": _to_plain(scheduled_at),
                },
                event_at=now,
            )
            await session.flush()

        self._materialize_job_dir(
            job=job,
            config_snapshot_payload=config_snapshot_payload,
            profile_snapshot_payload=profile_snapshot_payload,
        )

        return ServiceResult(
            status="ok",
            message="job created",
            payload={
                "created": True,
                **self._job_path_payload(job_id),
                "job": self._serialize_job(job),
            },
        )

    async def get_job(self, job_id: str | UUID) -> ServiceResult:
        """按 job_id 查询单个 Job。"""
        session_scope = self._ensure_session_factory()
        try:
            job_uuid = _parse_job_id(job_id)
        except ValueError:
            return ServiceResult(status="error", message="invalid job_id", payload={"job_id": str(job_id)})

        async with session_scope() as session:
            job = await self._load_job(session, job_uuid)

        if job is None:
            return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})

        return ServiceResult(
            status="ok",
            message="job loaded",
            payload={**self._job_path_payload(job.id), "job": self._serialize_job(job)},
        )

    async def get_job_timeline(self, job_id: str | UUID) -> ServiceResult:
        """按 job_id 查询结构化 Step Timeline。"""
        job_result = await self.get_job(job_id)
        if job_result.status != "ok":
            return job_result
        timeline = self._step_timeline_service.build_job_timeline(job=job_result.payload["job"])
        return ServiceResult(
            status="ok",
            message="job timeline loaded",
            payload=timeline.to_payload(),
        )

    async def list_jobs(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        created_by: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ServiceResult:
        """列出 Job，支持分页和过滤。"""
        session_scope = self._ensure_session_factory()
        conditions = []
        if status is not None:
            try:
                conditions.append(Job.status == JobStatus(status).value)
            except ValueError as exc:
                return ServiceResult(status="error", message=f"invalid status: {status}", payload={"error": str(exc)})
        if job_type is not None:
            conditions.append(Job.job_type == job_type)
        if created_by is not None:
            conditions.append(Job.created_by == created_by)

        async with session_scope() as session:
            count_stmt = select(func.count()).select_from(Job)
            if conditions:
                count_stmt = count_stmt.where(*conditions)
            total = int((await session.execute(count_stmt)).scalar() or 0)

            stmt = select(Job)
            stmt = stmt.options(selectinload(Job.audit_events))
            if conditions:
                stmt = stmt.where(*conditions)
            stmt = stmt.order_by(Job.created_at.desc(), Job.id.desc()).offset(skip).limit(limit)
            result = await session.execute(stmt)
            rows = list(result.scalars().all())

        items = [self._serialize_job(job) for job in rows]
        return ServiceResult(
            status="ok",
            message="jobs listed",
            payload={
                "count": len(items),
                "total": total,
                "skip": skip,
                "limit": limit,
                "items": items,
            },
        )

    async def start_job(
        self,
        *,
        job_id: str | UUID,
        worker_id: str,
        lock_token: str,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """把 Job 置为 running 并记录 worker 锁信息。"""
        return await self.claim_job(
            job_id=job_id,
            worker_id=worker_id,
            lock_token=lock_token,
            audit_source=audit_source,
        )

    async def claim_job(
        self,
        *,
        job_id: str | UUID,
        worker_id: str,
        lock_token: str,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """原子领取一个可执行 Job。"""
        session_scope = self._ensure_session_factory()
        now = datetime.now(UTC)
        async with session_scope() as session:
            job_uuid = _parse_job_id(job_id)
            stmt = (
                update(Job)
                .where(Job.id == job_uuid)
                .where(Job.status.in_([JobStatus.pending.value, JobStatus.failed.value]))
                .where(or_(Job.scheduled_at.is_(None), Job.scheduled_at <= now))
                .where(Job.cancel_requested.is_(False))
                .values(
                    status=JobStatus.running.value,
                    worker_id=worker_id,
                    lock_token=lock_token,
                    lock_acquired_at=now,
                    started_at=now,
                    heartbeat_at=now,
                    scheduled_at=None,
                    error=None,
                    result=None,
                    cancel_requested=False,
                    updated_at=now,
                )
            )
            result = await session.execute(stmt)
            if result.rowcount == 0:
                job = await self._load_job(session, job_uuid)
                if job is None:
                    return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
                if job.cancel_requested and job.status != JobStatus.running.value:
                    return ServiceResult(
                        status="error",
                        message=f"job cannot start from status {job.status}",
                        payload={"job_id": str(job_id), "status": job.status},
                    )
                if job.status not in {JobStatus.pending.value, JobStatus.failed.value}:
                    return ServiceResult(
                        status="error",
                        message=f"job cannot start from status {job.status}",
                        payload={"job_id": str(job_id), "status": job.status},
                    )
                if job.scheduled_at is not None and job.scheduled_at > now:
                    return ServiceResult(
                        status="partial",
                        message="job is scheduled for later",
                        payload={
                            "job_id": str(job_id),
                            "status": job.status,
                            "scheduled_at": _to_plain(job.scheduled_at),
                        },
                    )
                return ServiceResult(
                    status="error",
                    message="job claim failed",
                    payload={"job_id": str(job_id), "status": job.status},
                )

            job = await self._load_job(session, job_uuid)
            if job is None:
                return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
            await self._record_job_audit(
                session=session,
                job=job,
                operation="start",
                actor=worker_id,
                audit_source=audit_source,
                params_summary=job.params,
                payload={"worker_id": worker_id, "lock_token": lock_token},
                event_at=now,
            )

        return ServiceResult(
            status="ok",
            message="job started",
            payload={**self._job_path_payload(job.id), "job": self._serialize_job(job)},
        )

    async def complete_job(
        self,
        *,
        job_id: str | UUID,
        result: dict[str, Any] | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """把 Job 标记为 success。"""
        session_scope = self._ensure_session_factory()
        now = datetime.now(UTC)
        async with session_scope() as session:
            job = await self._load_job(session, job_id)
            if job is None:
                return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
            if job.status not in {JobStatus.running.value, JobStatus.pending.value}:
                return ServiceResult(
                    status="error",
                    message=f"job cannot complete from status {job.status}",
                    payload={"job_id": str(job_id), "status": job.status},
                )
            if job.cancel_requested:
                job.status = JobStatus.cancelled.value
                job.error = {"type": "cancelled", "message": "cancel requested"}
                operation = "cancel"
            else:
                job.status = JobStatus.success.value
                job.result = result or {}
                job.error = None
                operation = "complete"
            job.finished_at = now
            job.cancel_requested = False
            job.cancel_requested_at = job.cancel_requested_at or None
            await self._persist(session, job)
            await self._record_job_audit(
                session=session,
                job=job,
                operation=operation,
                actor=job.created_by,
                audit_source=audit_source,
                params_summary=job.params,
                payload={"result": result or {}, "status": job.status},
                event_at=now,
            )

        self._materialize_job_dir(
            job=job,
            result_payload={
                "status": job.status,
                "result": _to_plain(job.result or {}),
                "error": _to_plain(job.error),
            },
            config_snapshot_payload=self._load_config_snapshot(job.id),
            profile_snapshot_payload=self._load_profile_snapshot(job.id),
        )
        return ServiceResult(
            status="ok",
            message="job completed",
            payload={**self._job_path_payload(job.id), "job": self._serialize_job(job)},
        )

    async def fail_job(
        self,
        *,
        job_id: str | UUID,
        error: dict[str, Any] | str,
        increment_retry: bool = True,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """把 Job 标记为 failed。"""
        session_scope = self._ensure_session_factory()
        now = datetime.now(UTC)
        async with session_scope() as session:
            job = await self._load_job(session, job_id)
            if job is None:
                return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
            if increment_retry:
                job.retry_count += 1
            job.status = JobStatus.failed.value
            job.error = error if isinstance(error, dict) else {"message": error}
            job.result = None
            job.finished_at = now
            job.cancel_requested = False
            if job.retry_count < job.max_retries:
                backoff_seconds = max(0, int(job.retry_backoff_seconds or 0))
                job.scheduled_at = now + timedelta(seconds=backoff_seconds)
            else:
                job.scheduled_at = None
            await self._persist(session, job)
            await self._record_job_audit(
                session=session,
                job=job,
                operation="fail",
                actor=job.created_by,
                audit_source=audit_source,
                params_summary=job.params,
                payload={"error": error, "increment_retry": increment_retry, "retry_count": job.retry_count},
                event_at=now,
            )

        self._materialize_job_dir(
            job=job,
            result_payload={
                "status": job.status,
                "result": _to_plain(job.result or {}),
                "error": _to_plain(job.error),
            },
            config_snapshot_payload=self._load_config_snapshot(job.id),
            profile_snapshot_payload=self._load_profile_snapshot(job.id),
        )
        return ServiceResult(
            status="ok",
            message="job failed",
            payload={**self._job_path_payload(job.id), "job": self._serialize_job(job)},
        )

    async def cancel_job(
        self,
        *,
        job_id: str | UUID,
        reason: str | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """请求取消 Job，并在未完成时直接标记为 cancelled。"""
        session_scope = self._ensure_session_factory()
        now = datetime.now(UTC)
        async with session_scope() as session:
            job = await self._load_job(session, job_id)
            if job is None:
                return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
            if job.status in {JobStatus.success.value, JobStatus.failed.value, JobStatus.cancelled.value} and job.status != JobStatus.running.value:
                return ServiceResult(
                    status="error",
                    message=f"job cannot be cancelled from status {job.status}",
                    payload={"job_id": str(job_id), "status": job.status},
                )
            if job.status == JobStatus.running.value:
                job.cancel_requested = True
                job.cancel_requested_at = now
                if job.error is None:
                    job.error = {"message": reason or "cancel requested", "type": "cancel_requested"}
            else:
                job.cancel_requested = True
                job.cancel_requested_at = now
                job.status = JobStatus.cancelled.value
                job.error = {"message": reason or "cancel requested", "type": "cancelled"}
                job.finished_at = now
            await self._persist(session, job)
            await self._record_job_audit(
                session=session,
                job=job,
                operation="cancel",
                actor=job.created_by,
                audit_source=audit_source,
                params_summary=job.params,
                payload={"reason": reason, "status": job.status},
                event_at=now,
            )

        self._materialize_job_dir(
            job=job,
            result_payload={
                "status": job.status,
                "result": _to_plain(job.result or {}),
                "error": _to_plain(job.error),
            },
            config_snapshot_payload=self._load_config_snapshot(job.id),
            profile_snapshot_payload=self._load_profile_snapshot(job.id),
        )
        return ServiceResult(
            status="ok",
            message="job cancelled",
            payload={**self._job_path_payload(job.id), "job": self._serialize_job(job)},
        )

    async def append_log(self, *, job_id: str | UUID, line: str) -> ServiceResult:
        """追加 Job 日志。"""
        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            job = await self._load_job(session, job_id)
            if job is None:
                return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
            log_path = self._log_path(job.id)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(line.rstrip("\n") + "\n")

        return ServiceResult(
            status="ok",
            message="job log appended",
            payload={"job_id": str(job_id), "log_path": str(log_path)},
        )

    async def heartbeat_job(
        self,
        *,
        job_id: str | UUID,
        worker_id: str | None = None,
        lock_token: str | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """刷新运行中 Job 的心跳时间。"""
        session_scope = self._ensure_session_factory()
        now = datetime.now(UTC)
        async with session_scope() as session:
            job = await self._load_job(session, job_id)
            if job is None:
                return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
            if job.status != JobStatus.running.value:
                return ServiceResult(
                    status="error",
                    message=f"job cannot heartbeat from status {job.status}",
                    payload={"job_id": str(job_id), "status": job.status},
                )
            if worker_id is not None and job.worker_id is not None and job.worker_id != worker_id:
                return ServiceResult(
                    status="error",
                    message="worker mismatch",
                    payload={"job_id": str(job_id), "worker_id": job.worker_id},
                )
            if lock_token is not None and job.lock_token is not None and job.lock_token != lock_token:
                return ServiceResult(
                    status="error",
                    message="lock token mismatch",
                    payload={"job_id": str(job_id), "lock_token": job.lock_token},
                )
            job.heartbeat_at = now
            await self._persist(session, job)
            await self._record_job_audit(
                session=session,
                job=job,
                operation="heartbeat",
                actor=worker_id or job.created_by,
                audit_source=audit_source,
                params_summary=job.params,
                payload={"worker_id": worker_id, "lock_token": lock_token},
                event_at=now,
            )

        return ServiceResult(status="ok", message="job heartbeat updated", payload={"job": self._serialize_job(job)})

    async def bind_artifact(
        self,
        *,
        job_id: str | UUID,
        kind: str,
        path: str | Path,
        workflow_id: str | None = None,
        step_id: str | None = None,
        title: str | None = None,
        summary: str | None = None,
        metadata: dict[str, Any] | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """给 Job 绑定一个产物引用。"""
        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            job = await self._load_job(session, job_id)
            if job is None:
                return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
            artifacts = list(job.artifacts or [])
            artifact_path = Path(path)
            artifact_id = hashlib.sha256(f"{job.id}|{kind}|{artifact_path.resolve()}".encode("utf-8")).hexdigest()[:16]
            relative_path = None
            try:
                relative_path = artifact_path.resolve().relative_to(self._job_dir(job.id).resolve()).as_posix()
            except ValueError:
                relative_path = artifact_path.name
            artifact = ArtifactRef(
                artifact_id=artifact_id,
                job_id=str(job.id),
                workflow_id=workflow_id,
                step_id=step_id,
                kind=kind,
                title=title or artifact_path.name,
                summary=summary or (metadata or {}).get("summary"),
                safe_download_url=self._artifact_safe_download_url(artifact_id),
                size_bytes=artifact_path.stat().st_size if artifact_path.exists() else None,
                metadata=metadata or {},
                storage_ref=StorageRef(
                    source="file",
                    logical_id=artifact_id,
                    relative_path=relative_path,
                    metadata={"job_id": str(job.id)},
                ),
            ).model_dump(mode="json")
            artifacts.append(artifact)
            job.artifacts = artifacts
            await self._persist(session, job)
            await self._record_job_audit(
                session=session,
                job=job,
                operation="bind_artifact",
                actor=job.created_by,
                audit_source=audit_source,
                params_summary=job.params,
                payload={"artifact": artifact},
                event_at=datetime.now(UTC),
            )

        return ServiceResult(
            status="ok",
            message="job artifact bound",
            payload={
                "job": self._serialize_job(job),
                "artifact": artifact,
                "artifacts_path": str(self._artifacts_path(job.id)),
            },
        )

    async def mark_timed_out(
        self,
        *,
        job_id: str | UUID,
        reason: str | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """把 Job 标记为超时失败。"""
        return await self.fail_job(
            job_id=job_id,
            error={"type": "timeout", "message": reason or "job timed out"},
            increment_retry=True,
            audit_source=audit_source,
        )

    async def recover_stale_jobs(
        self,
        *,
        stale_before: datetime,
        actor: str | None = None,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """把超出心跳阈值的 running Job 标记为 failed。"""
        session_scope = self._ensure_session_factory()
        recovered: list[str] = []
        now = datetime.now(UTC)
        async with session_scope() as session:
            stmt = select(Job).where(
                Job.status == JobStatus.running.value,
                or_(
                    Job.heartbeat_at.is_(None),
                    Job.heartbeat_at <= stale_before,
                ),
            )
            result = await session.execute(stmt)
            jobs = list(result.scalars().all())
            for job in jobs:
                job.status = JobStatus.failed.value
                job.retry_count += 1
                job.error = {
                    "type": "stale_recovery",
                    "message": f"heartbeat stale before {stale_before.isoformat()}",
                }
                job.finished_at = now
                job.worker_id = None
                job.lock_token = None
                job.lock_acquired_at = None
                if job.retry_count < job.max_retries:
                    backoff_seconds = max(0, int(job.retry_backoff_seconds or 0))
                    job.scheduled_at = now + timedelta(seconds=backoff_seconds)
                else:
                    job.scheduled_at = None
                await self._persist(session, job)
                await self._record_job_audit(
                    session=session,
                    job=job,
                    operation="stale_recovery",
                    actor=actor or job.created_by,
                    audit_source=audit_source,
                    params_summary=job.params,
                    payload={
                        "stale_before": stale_before.isoformat(),
                        "retry_count": job.retry_count,
                        "scheduled_at": _to_plain(job.scheduled_at),
                    },
                    event_at=now,
                )
                recovered.append(str(job.id))

        return ServiceResult(
            status="ok",
            message="stale jobs recovered",
            payload={"count": len(recovered), "job_ids": recovered, "stale_before": stale_before.isoformat()},
        )

    async def count_jobs(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
    ) -> ServiceResult:
        """统计 Job 数量，供 Worker 做并发限制。"""
        session_scope = self._ensure_session_factory()
        conditions = []
        if status is not None:
            try:
                conditions.append(Job.status == JobStatus(status).value)
            except ValueError as exc:
                return ServiceResult(status="error", message=f"invalid status: {status}", payload={"error": str(exc)})
        if job_type is not None:
            conditions.append(Job.job_type == job_type)

        async with session_scope() as session:
            stmt = select(func.count()).select_from(Job)
            if conditions:
                stmt = stmt.where(*conditions)
            total = int((await session.execute(stmt)).scalar() or 0)

        return ServiceResult(status="ok", message="jobs counted", payload={"count": total, "status": status, "job_type": job_type})

    async def list_ready_jobs(
        self,
        *,
        job_type: str | None = None,
        limit: int = 50,
    ) -> ServiceResult:
        """列出当前可领取的 pending / retryable Job。"""
        session_scope = self._ensure_session_factory()
        now = datetime.now(UTC)
        conditions = [
            Job.status.in_([JobStatus.pending.value, JobStatus.failed.value]),
            or_(Job.scheduled_at.is_(None), Job.scheduled_at <= now),
            Job.cancel_requested.is_(False),
        ]
        if job_type is not None:
            conditions.append(Job.job_type == job_type)

        async with session_scope() as session:
            stmt = (
                select(Job)
                .options(selectinload(Job.audit_events))
                .where(*conditions)
                .order_by(Job.created_at.asc(), Job.id.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = list(result.scalars().all())

        items = [self._serialize_job(job) for job in rows]
        return ServiceResult(
            status="ok",
            message="ready jobs listed",
            payload={"count": len(items), "items": items, "limit": limit, "job_type": job_type},
        )


def get_job_service() -> JobService:
    """获取 JobService 实例，供 API 层依赖注入复用。"""
    return JobService()
