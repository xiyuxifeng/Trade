from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.repositories import WorkflowRunRepository
from src.db.session import get_session_factory
from src.models.workflow_run import WorkflowRun, WorkflowRunStep
from src.services.base import BaseService, ServiceResult


def _to_plain(value: Any) -> Any:
    """把 contract / 容器值转成 JSON 兼容结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _coerce_date(value: Any) -> date | None:
    """把日期参数归一化为 date。"""
    if value in {None, ""}:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"invalid date value: {value}")
class WorkflowRunService(BaseService):
    """Workflow 运行事实源的持久化与查询服务。"""

    service_name = "workflow-run"

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        repository: WorkflowRunRepository | None = None,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        self._repository = repository or WorkflowRunRepository()

    def _page_payload(self, *, total: int, limit: int, offset: int, count: int) -> dict[str, int]:
        """构造分页信息。"""
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": count,
        }

    def _run_summary(self, run: WorkflowRun) -> dict[str, Any]:
        """把 workflow run 归一化成前端可展示摘要。"""
        return {
            "id": str(run.id),
            "workflow_id": run.workflow_id,
            "workflow_title": run.workflow_title,
            "workflow_version": run.workflow_version,
            "status": run.status,
            "trigger_source": run.trigger_source,
            "created_by": run.created_by,
            "confirmed": run.confirmed,
            "idempotency_key": run.idempotency_key,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "duration_ms": run.duration_ms,
            "input_params_json": run.input_params_json,
            "output_summary_json": run.output_summary_json,
            "error_json": run.error_json,
            "metadata_json": run.metadata_json,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        }

    def _step_summary(self, step: WorkflowRunStep) -> dict[str, Any]:
        """把 workflow run step 归一化成前端可展示摘要。"""
        return {
            "id": str(step.id),
            "workflow_run_id": str(step.workflow_run_id),
            "step_id": step.step_id,
            "step_name": step.step_name,
            "step_order": step.step_order,
            "job_id": step.job_id,
            "job_type": step.job_type,
            "status": step.status,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "finished_at": step.finished_at.isoformat() if step.finished_at else None,
            "duration_ms": step.duration_ms,
            "input_json": step.input_json,
            "output_json": step.output_json,
            "error_json": step.error_json,
            "artifact_refs_json": step.artifact_refs_json,
            "metadata_json": step.metadata_json,
            "created_at": step.created_at.isoformat() if step.created_at else None,
            "updated_at": step.updated_at.isoformat() if step.updated_at else None,
        }

    def _build_run_model(
        self,
        *,
        workflow: Any,
        workflow_run: Any,
        confirmed: bool,
        audit_source: dict[str, Any] | None,
    ) -> WorkflowRun:
        """把 WorkflowRunContext 转成持久化主记录。"""
        run_context = workflow_run.run_context
        step_results = list(getattr(workflow_run, "step_results", []) or [])
        errors = list(getattr(workflow_run, "errors", []) or [])
        artifacts = list(getattr(workflow_run, "artifacts", []) or [])
        workflow_summary = workflow.summary() if hasattr(workflow, "summary") else _to_plain(workflow)
        status = str(run_context.status or "pending")
        started_at = run_context.started_at or run_context.created_at
        finished_at = run_context.finished_at
        duration_ms = None
        if started_at is not None and finished_at is not None:
            duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
        root_job_id = str(run_context.job_id or run_context.run_id)
        metadata = dict(getattr(workflow_run, "metadata", {}) or {})
        metadata.update(
            {
                "workflow_summary": workflow_summary,
                "workflow_params": _to_plain(getattr(workflow_run, "workflow_params", {}) or {}),
                "audit_source": _to_plain(audit_source or {}),
                "root_job_id": root_job_id,
                "step_count": len(step_results),
                "artifact_count": len(artifacts),
                "error_count": len(errors),
            }
        )
        output_summary = {
            "run_id": str(run_context.run_id),
            "job_id": root_job_id,
            "workflow_id": getattr(workflow, "workflow_id", None),
            "workflow_title": getattr(workflow, "title", getattr(workflow, "workflow_id", "workflow")),
            "workflow_version": getattr(workflow, "job_type", getattr(workflow, "workflow_id", "workflow")),
            "status": status,
            "step_count": len(step_results),
            "success_step_count": sum(1 for item in step_results if getattr(item, "status", None) == "success"),
            "failed_step_count": sum(1 for item in step_results if getattr(item, "status", None) == "failed"),
            "cancelled_step_count": sum(1 for item in step_results if getattr(item, "status", None) == "cancelled"),
            "artifact_count": len(artifacts),
        }
        error_json = errors[0].model_dump(mode="json") if errors else None
        return WorkflowRun(
            id=UUID(str(run_context.run_id)),
            workflow_id=getattr(workflow, "workflow_id", str(run_context.workflow_id or "workflow")),
            workflow_title=getattr(workflow, "title", getattr(workflow, "workflow_id", "workflow")),
            workflow_version=str(getattr(workflow, "job_type", getattr(workflow, "workflow_id", "workflow"))),
            status=status,
            trigger_source=str(run_context.trigger_source or (audit_source or {}).get("channel") or "system"),
            created_by=getattr(workflow_run.user_context, "user_id", None),
            confirmed=confirmed,
            idempotency_key=metadata.get("idempotency_key") if isinstance(metadata, Mapping) else None,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            input_params_json=_to_plain(getattr(workflow_run, "workflow_params", {}) or {}),
            output_summary_json=output_summary,
            error_json=error_json,
            metadata_json=metadata,
        )

    def _build_step_models(self, *, workflow: Any, workflow_run: Any) -> list[WorkflowRunStep]:
        """把 WorkflowRunContext 的 step 明细转成持久化记录。"""
        step_inputs = list(getattr(workflow_run, "step_inputs", []) or [])
        step_results = {getattr(result, "step_name", None): result for result in (getattr(workflow_run, "step_results", []) or [])}
        workflow_steps = {getattr(step, "step_id", None): step for step in getattr(workflow, "steps", []) or []}
        step_errors = list(getattr(workflow_run, "errors", []) or [])

        step_models: list[WorkflowRunStep] = []
        for order, step_input in enumerate(step_inputs, start=1):
            step_result = step_results.get(step_input.step_name)
            workflow_step = workflow_steps.get(step_input.step_name)
            step_metadata = getattr(step_input, "metadata", {})
            result_metadata = getattr(step_result, "metadata", {}) if step_result is not None else {}
            step_error = getattr(step_result, "error", None) if step_result is not None else None
            status = str(getattr(step_result, "status", None) or getattr(workflow_run.run_context, "status", "pending"))
            if step_result is None and status == "success":
                status = "failed" if step_errors else "success"
                if step_errors:
                    step_error = step_errors[0]

            started_at = getattr(step_result, "started_at", None)
            finished_at = getattr(step_result, "finished_at", None)
            duration_ms = getattr(step_result, "duration_ms", None)
            if duration_ms is None and started_at is not None and finished_at is not None:
                duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
            artifacts = [artifact.model_dump(mode="json") for artifact in getattr(step_result, "artifacts", []) or []]
            required_job_type = (
                getattr(workflow_step, "required_job_type", None)
                or (step_metadata.get("required_job_type") if isinstance(step_metadata, dict) else None)
                or "job"
            )
            job_type = (
                result_metadata.get("job_type") if isinstance(result_metadata, dict) else None
            ) or required_job_type
            step_models.append(
                WorkflowRunStep(
                    step_id=str(step_input.step_name),
                    step_name=str(getattr(workflow_step, "title", step_input.step_name)),
                    step_order=order,
                    job_id=str(result_metadata.get("job_id")) if isinstance(result_metadata, dict) and result_metadata.get("job_id") is not None else None,
                    job_type=str(job_type),
                    status=status,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                    input_json=_to_plain(getattr(step_input, "payload", {}) or {}),
                    output_json=_to_plain(getattr(step_result, "payload", {}) or {}),
                    error_json=step_error.model_dump(mode="json") if step_error is not None and hasattr(step_error, "model_dump") else (_to_plain(step_error) if step_error is not None else None),
                    artifact_refs_json=artifacts,
                    metadata_json={
                        "input_id": getattr(step_input, "input_id", None),
                        "order": step_metadata.get("order") if isinstance(step_metadata, dict) else order,
                        "required_job_type": step_metadata.get("required_job_type") if isinstance(step_metadata, dict) else None,
                        "workflow_step_id": step_input.step_name,
                        "workflow_step_title": getattr(workflow_step, "title", step_input.step_name),
                    },
                )
            )
        return step_models

    async def record_workflow_run(
        self,
        *,
        workflow: Any,
        workflow_run: Any,
        confirmed: bool,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """将一次 workflow 运行写入事实源。"""
        run = self._build_run_model(workflow=workflow, workflow_run=workflow_run, confirmed=confirmed, audit_source=audit_source)
        steps = self._build_step_models(workflow=workflow, workflow_run=workflow_run)
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    persisted = await self._repository.upsert_run(session, run, steps)
            return ServiceResult(
                status="ok",
                message="workflow run recorded",
                payload={
                    "workflow_run": self._run_summary(persisted),
                    "step_count": len(steps),
                },
            )
        except Exception as exc:  # pragma: no cover - safety net, covered by integration tests
            return ServiceResult(
                status="partial",
                message="workflow run record failed",
                warnings=[str(exc)],
                payload={
                    "workflow_run": run.to_dict(),
                    "step_count": len(steps),
                    "error": {
                        "type": "storage_failed",
                        "message": "workflow run record failed",
                        "detail": str(exc),
                        "metadata": {
                            "workflow_id": run.workflow_id,
                            "workflow_run_id": str(run.id),
                        },
                    },
                },
            )

    async def list_workflow_runs(
        self,
        *,
        workflow_id: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ServiceResult:
        """按条件查询 workflow run 列表。"""
        if limit < 1 or offset < 0:
            return ServiceResult(
                status="error",
                message="invalid pagination",
                payload={
                    "error": {
                        "type": "invalid_query",
                        "message": "invalid pagination",
                        "detail": "limit must be >= 1 and offset must be >= 0",
                        "metadata": {"limit": limit, "offset": offset},
                    }
                },
            )
        try:
            normalized_start = _coerce_date(start_date)
            normalized_end = _coerce_date(end_date)
        except ValueError as exc:
            return ServiceResult(
                status="error",
                message="invalid date",
                payload={
                    "error": {
                        "type": "invalid_query",
                        "message": "invalid date",
                        "detail": str(exc),
                        "metadata": {"start_date": start_date, "end_date": end_date},
                    }
                },
            )

        async with self._session_factory() as session:
            total = await self._repository.count_runs(
                session,
                workflow_id=workflow_id,
                status=status,
                created_by=created_by,
                start_date=normalized_start,
                end_date=normalized_end,
            )
            runs = await self._repository.list_runs(
                session,
                workflow_id=workflow_id,
                status=status,
                created_by=created_by,
                start_date=normalized_start,
                end_date=normalized_end,
                limit=limit,
                offset=offset,
            )

        return ServiceResult(
            status="ok",
            message="workflow runs listed",
            payload={
                "filters": {
                    "workflow_id": workflow_id,
                    "status": status,
                    "created_by": created_by,
                    "start_date": normalized_start.isoformat() if normalized_start else None,
                    "end_date": normalized_end.isoformat() if normalized_end else None,
                },
                "page": self._page_payload(total=total, limit=limit, offset=offset, count=len(runs)),
                "items": [self._run_summary(run) for run in runs],
            },
        )

    async def get_workflow_run(self, workflow_run_id: str) -> ServiceResult:
        """按 run_id 查询 workflow run 详情。"""
        try:
            async with self._session_factory() as session:
                run = await self._repository.get_by_run_id(session, workflow_run_id)
                if run is None:
                    return ServiceResult(
                        status="partial",
                        message="workflow run not found",
                        payload={
                            "error": {
                                "type": "workflow_run_not_found",
                                "message": "workflow run not found",
                                "detail": workflow_run_id,
                                "metadata": {"workflow_run_id": workflow_run_id},
                            }
                        },
                    )
                steps = await self._repository.list_steps_by_run_id(session, workflow_run_id)
        except ValueError as exc:
            return ServiceResult(
                status="error",
                message="invalid workflow run id",
                payload={
                    "error": {
                        "type": "invalid_query",
                        "message": "invalid workflow run id",
                        "detail": str(exc),
                        "metadata": {"workflow_run_id": workflow_run_id},
                    }
                },
            )

        return ServiceResult(
            status="ok",
            message="workflow run loaded",
            payload={
                "workflow_run": self._run_summary(run),
                "steps": [self._step_summary(step) for step in steps],
                "page": self._page_payload(total=len(steps), limit=len(steps), offset=0, count=len(steps)),
            },
        )

    async def list_workflow_run_steps(self, workflow_run_id: str, *, limit: int = 200, offset: int = 0) -> ServiceResult:
        """按 run_id 查询 workflow step 明细。"""
        if limit < 1 or offset < 0:
            return ServiceResult(
                status="error",
                message="invalid pagination",
                payload={
                    "error": {
                        "type": "invalid_query",
                        "message": "invalid pagination",
                        "detail": "limit must be >= 1 and offset must be >= 0",
                        "metadata": {"limit": limit, "offset": offset},
                    }
                },
            )

        try:
            async with self._session_factory() as session:
                run = await self._repository.get_by_run_id(session, workflow_run_id)
                if run is None:
                    return ServiceResult(
                        status="partial",
                        message="workflow run not found",
                        payload={
                            "error": {
                                "type": "workflow_run_not_found",
                                "message": "workflow run not found",
                                "detail": workflow_run_id,
                                "metadata": {"workflow_run_id": workflow_run_id},
                            }
                        },
                    )
                steps = await self._repository.list_steps_by_run_id(session, workflow_run_id)
        except ValueError as exc:
            return ServiceResult(
                status="error",
                message="invalid workflow run id",
                payload={
                    "error": {
                        "type": "invalid_query",
                        "message": "invalid workflow run id",
                        "detail": str(exc),
                        "metadata": {"workflow_run_id": workflow_run_id},
                    }
                },
            )

        paged_steps = steps[offset : offset + limit] if limit is not None else steps[offset:]
        return ServiceResult(
            status="ok",
            message="workflow run steps loaded",
            payload={
                "workflow_run_id": workflow_run_id,
                "page": self._page_payload(total=len(steps), limit=limit, offset=offset, count=len(paged_steps)),
                "items": [self._step_summary(step) for step in paged_steps],
            },
        )


def make_workflow_run_service(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    repository: WorkflowRunRepository | None = None,
) -> WorkflowRunService:
    """构造 WorkflowRunService。"""
    return WorkflowRunService(session_factory=session_factory, repository=repository)
