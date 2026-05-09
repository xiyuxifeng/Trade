from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, update

from src.models.job import Job, JobStatus
from src.services.base import BaseService, ServiceResult
from src.common.paths import resolve_project_path


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


class JobService(BaseService):
    """Job Center 的数据库服务。"""

    service_name = "job"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        job_base_dir: str | Path = resolve_project_path("data/jobs"),
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._job_base_dir = resolve_project_path(job_base_dir)

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

    def _write_json_file(self, path: Path, payload: Any) -> None:
        """把结构化 payload 写入 JSON 文件。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_to_plain(payload), ensure_ascii=False, indent=2), encoding="utf-8")

    def _materialize_job_dir(
        self,
        *,
        job: Job,
        result_payload: dict[str, Any] | None = None,
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
        if result_payload is not None:
            self._write_json_file(self._result_path(job.id), result_payload)

    def _serialize_job(self, job: Job) -> dict[str, Any]:
        """把 Job ORM 对象转成前端可用结构。"""
        return {
            "id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "params": _to_plain(job.params),
            "result": _to_plain(job.result),
            "error": _to_plain(job.error),
            "artifacts": _to_plain(job.artifacts),
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
            "created_at": _to_plain(job.created_at),
            "updated_at": _to_plain(job.updated_at),
        }

    async def _load_job(self, session: Any, job_id: str | UUID) -> Job | None:
        """从数据库加载 Job。"""
        job_uuid = _parse_job_id(job_id)
        stmt = select(Job).where(Job.id == job_uuid)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

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
        scheduled_at: datetime | None = None,
    ) -> ServiceResult:
        """创建新的 Job 记录。"""
        session_scope = self._ensure_session_factory()
        if idempotency_key:
            async with session_scope() as session:
                stmt = select(Job).where(Job.idempotency_key == idempotency_key)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing is not None:
                    self._materialize_job_dir(job=existing)
                    return ServiceResult(
                        status="ok",
                        message="job already exists",
                        payload={
                            "created": False,
                            "job_dir": str(self._job_dir(existing.id)),
                            "log_path": str(self._log_path(existing.id)),
                            "params_path": str(self._params_path(existing.id)),
                            "result_path": str(self._result_path(existing.id)),
                            "artifacts_path": str(self._artifacts_path(existing.id)),
                            "job": self._serialize_job(existing),
                        },
                    )

        job_id = uuid4()
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
            await session.flush()

        self._materialize_job_dir(job=job)

        return ServiceResult(
            status="ok",
            message="job created",
            payload={
                "created": True,
                "job_dir": str(self._job_dir(job_id)),
                "log_path": str(self._log_path(job_id)),
                "params_path": str(self._params_path(job_id)),
                "result_path": str(self._result_path(job_id)),
                "artifacts_path": str(self._artifacts_path(job_id)),
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
            payload={
                "job_dir": str(self._job_dir(job.id)),
                "log_path": str(self._log_path(job.id)),
                "params_path": str(self._params_path(job.id)),
                "result_path": str(self._result_path(job.id)),
                "artifacts_path": str(self._artifacts_path(job.id)),
                "job": self._serialize_job(job),
            },
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
    ) -> ServiceResult:
        """把 Job 置为 running 并记录 worker 锁信息。"""
        return await self.claim_job(job_id=job_id, worker_id=worker_id, lock_token=lock_token)

    async def claim_job(
        self,
        *,
        job_id: str | UUID,
        worker_id: str,
        lock_token: str,
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

        return ServiceResult(
            status="ok",
            message="job started",
            payload={
                "job_dir": str(self._job_dir(job.id)),
                "log_path": str(self._log_path(job.id)),
                "params_path": str(self._params_path(job.id)),
                "result_path": str(self._result_path(job.id)),
                "artifacts_path": str(self._artifacts_path(job.id)),
                "job": self._serialize_job(job),
            },
        )

    async def complete_job(
        self,
        *,
        job_id: str | UUID,
        result: dict[str, Any] | None = None,
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
            else:
                job.status = JobStatus.success.value
                job.result = result or {}
                job.error = None
            job.finished_at = now
            job.cancel_requested = False
            job.cancel_requested_at = job.cancel_requested_at or None
            await self._persist(session, job)

        self._materialize_job_dir(
            job=job,
            result_payload={
                "status": job.status,
                "result": _to_plain(job.result or {}),
                "error": _to_plain(job.error),
            },
        )
        return ServiceResult(
            status="ok",
            message="job completed",
            payload={
                "job_dir": str(self._job_dir(job.id)),
                "log_path": str(self._log_path(job.id)),
                "params_path": str(self._params_path(job.id)),
                "result_path": str(self._result_path(job.id)),
                "artifacts_path": str(self._artifacts_path(job.id)),
                "job": self._serialize_job(job),
            },
        )

    async def fail_job(
        self,
        *,
        job_id: str | UUID,
        error: dict[str, Any] | str,
        increment_retry: bool = True,
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

        self._materialize_job_dir(
            job=job,
            result_payload={
                "status": job.status,
                "result": _to_plain(job.result or {}),
                "error": _to_plain(job.error),
            },
        )
        return ServiceResult(
            status="ok",
            message="job failed",
            payload={
                "job_dir": str(self._job_dir(job.id)),
                "log_path": str(self._log_path(job.id)),
                "params_path": str(self._params_path(job.id)),
                "result_path": str(self._result_path(job.id)),
                "artifacts_path": str(self._artifacts_path(job.id)),
                "job": self._serialize_job(job),
            },
        )

    async def cancel_job(
        self,
        *,
        job_id: str | UUID,
        reason: str | None = None,
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

        self._materialize_job_dir(
            job=job,
            result_payload={
                "status": job.status,
                "result": _to_plain(job.result or {}),
                "error": _to_plain(job.error),
            },
        )
        return ServiceResult(
            status="ok",
            message="job cancelled",
            payload={
                "job_dir": str(self._job_dir(job.id)),
                "log_path": str(self._log_path(job.id)),
                "params_path": str(self._params_path(job.id)),
                "result_path": str(self._result_path(job.id)),
                "artifacts_path": str(self._artifacts_path(job.id)),
                "job": self._serialize_job(job),
            },
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

        return ServiceResult(status="ok", message="job heartbeat updated", payload={"job": self._serialize_job(job)})

    async def bind_artifact(
        self,
        *,
        job_id: str | UUID,
        kind: str,
        path: str | Path,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """给 Job 绑定一个产物引用。"""
        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            job = await self._load_job(session, job_id)
            if job is None:
                return ServiceResult(status="partial", message="job not found", payload={"job_id": str(job_id)})
            artifacts = list(job.artifacts or [])
            artifact = {
                "kind": kind,
                "path": str(Path(path)),
                "metadata": metadata or {},
            }
            artifacts.append(artifact)
            job.artifacts = artifacts
            await self._persist(session, job)

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
    ) -> ServiceResult:
        """把 Job 标记为超时失败。"""
        return await self.fail_job(
            job_id=job_id,
            error={"type": "timeout", "message": reason or "job timed out"},
            increment_retry=True,
        )

    async def recover_stale_jobs(
        self,
        *,
        stale_before: datetime,
    ) -> ServiceResult:
        """把超出心跳阈值的 running Job 标记为 failed。"""
        session_scope = self._ensure_session_factory()
        recovered: list[str] = []
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
                job.finished_at = datetime.now(UTC)
                job.worker_id = None
                job.lock_token = None
                job.lock_acquired_at = None
                if job.retry_count < job.max_retries:
                    backoff_seconds = max(0, int(job.retry_backoff_seconds or 0))
                    job.scheduled_at = datetime.now(UTC) + timedelta(seconds=backoff_seconds)
                else:
                    job.scheduled_at = None
                await self._persist(session, job)
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
            stmt = select(Job).where(*conditions).order_by(Job.created_at.asc(), Job.id.asc()).limit(limit)
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
