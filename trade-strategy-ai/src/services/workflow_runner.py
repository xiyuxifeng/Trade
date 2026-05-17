from __future__ import annotations

import os
import socket
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable

from src.services.base import BaseService, ServiceResult
from src.services.job_runner import JobRunner
from src.services.job_service import JobService
from src.services.workflow_run_service import WorkflowRunService
from src.services.runtime_contracts import (
    ArtifactRef,
    RunContext,
    StepError,
    StepErrorType,
    StepInput,
    StepResult,
    UserContext,
    WorkflowRunContext,
)


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
    if isinstance(value, Path):
        return str(value)
    return value


class WorkflowRunner(BaseService):
    """把 WorkflowDefinition 执行成一串顺序 Job。"""

    service_name = "workflow-runner"

    def __init__(
        self,
        *,
        job_service: JobService | None = None,
        job_runner_factory: Callable[[JobService], JobRunner] | None = None,
        workflow_run_service_factory: Callable[[], WorkflowRunService] | None = None,
        worker_id: str | None = None,
    ) -> None:
        self._job_service = job_service or JobService()
        self._job_runner_factory = job_runner_factory
        self._workflow_run_service_factory = workflow_run_service_factory
        self._worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:workflow"
        self._job_runner: JobRunner | None = None
        self._workflow_run_service: WorkflowRunService | None = None

    def _build_job_runner(self) -> JobRunner:
        """延迟构造 JobRunner，便于测试替身注入。"""
        if self._job_runner is not None:
            return self._job_runner
        if self._job_runner_factory is not None:
            self._job_runner = self._job_runner_factory(self._job_service)
        else:
            self._job_runner = JobRunner(job_service=self._job_service, worker_id=self._worker_id)
        return self._job_runner

    def _build_workflow_run_service(self) -> WorkflowRunService:
        """延迟构造 WorkflowRunService，便于测试替身注入。"""
        if self._workflow_run_service is not None:
            return self._workflow_run_service
        if self._workflow_run_service_factory is not None:
            self._workflow_run_service = self._workflow_run_service_factory()
        else:
            self._workflow_run_service = WorkflowRunService()
        return self._workflow_run_service

    def _step_error_type(self, status: str, error: dict[str, Any] | None) -> StepErrorType:
        """把 job 状态和错误内容映射成 StepErrorType。"""
        if status == "cancelled":
            return StepErrorType.cancelled
        if isinstance(error, dict):
            value = str(error.get("type") or "").strip().lower()
            try:
                return StepErrorType(value)
            except ValueError:
                pass
        return StepErrorType.system_error

    def _step_error(self, *, step_id: str, status: str, error: dict[str, Any] | None) -> StepError:
        """把 job 错误收敛成 runtime contract。"""
        message = "step failed"
        detail = None
        if isinstance(error, dict):
            message = str(error.get("message") or message)
            detail = str(error) if error else None
        elif error is not None:
            message = str(error)
            detail = message
        return StepError(
            type=self._step_error_type(status, error),
            message=message,
            detail=detail,
            metadata={"step_id": step_id, "status": status},
        )

    def _job_status_to_step_status(self, status: str) -> str:
        """把 Job 状态映射为 StepResult 状态。"""
        return {
            "success": "success",
            "failed": "failed",
            "cancelled": "cancelled",
            "skipped": "skipped",
        }.get(status, "success")

    def _extract_child_job(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """从 JobRunner 返回值里提取执行后的 Job。"""
        execution = payload.get("execution")
        if isinstance(execution, dict):
            job = execution.get("job")
            if isinstance(job, dict):
                return job
        job = payload.get("job")
        return job if isinstance(job, dict) else None

    def _step_params(self, workflow_params: dict[str, Any], step: Any) -> dict[str, Any]:
        """按 step 参数白名单收敛提交给子 job 的参数。"""
        allowed = list(getattr(step, "parameters", []) or [])
        if not allowed:
            return dict(workflow_params)
        return {name: workflow_params[name] for name in allowed if name in workflow_params}

    async def run_workflow(
        self,
        *,
        workflow: Any,
        params: dict[str, Any] | None = None,
        created_by: str | None = None,
        idempotency_key: str | None = None,
        audit_source: dict[str, Any] | None = None,
        confirmed: bool = False,
    ) -> ServiceResult:
        """顺序执行一个 WorkflowDefinition。"""
        runner = self._build_job_runner()
        workflow_params = dict(params or {})
        created_result = await self._job_service.create_job(
            job_type=workflow.job_type,
            params=workflow_params,
            created_by=created_by,
            idempotency_key=idempotency_key,
            audit_source=audit_source,
            confirmed=confirmed,
        )
        if created_result.status != "ok":
            return created_result

        root_job = created_result.payload["job"]
        root_job_id = root_job["id"]
        workflow_summary = workflow.summary() if hasattr(workflow, "summary") else _to_plain(workflow)
        started_result = await self._job_service.start_job(
            job_id=root_job_id,
            worker_id=self._worker_id,
            lock_token=root_job_id,
            audit_source=audit_source,
        )
        if started_result.status != "ok":
            return started_result
        root_job = started_result.payload["job"]

        run_context = RunContext(
            run_id=root_job_id,
            job_id=root_job_id,
            workflow_id=workflow.workflow_id,
            status="running",
            created_at=datetime.fromisoformat(root_job["created_at"]),
            started_at=datetime.fromisoformat(root_job["started_at"]) if root_job.get("started_at") else None,
            trigger_source=str((audit_source or {}).get("channel") or "system"),
            metadata={
                "workflow_title": getattr(workflow, "title", workflow.workflow_id),
                "workflow_job_type": workflow.job_type,
                "workflow_steps": [step.step_id for step in getattr(workflow, "steps", [])],
                "audit_source": audit_source or {},
            },
        )
        user_context = UserContext(
            user_id=created_by or "system",
            username=created_by or "system",
            roles=[getattr(workflow, "permissions", "operator")],
            metadata={"audit_source": audit_source or {}},
        )
        workflow_run = WorkflowRunContext(
            run_context=run_context,
            user_context=user_context,
            workflow_params=workflow_params,
            metadata={
                "workflow_id": workflow.workflow_id,
                "workflow_title": getattr(workflow, "title", workflow.workflow_id),
                "root_job_id": root_job_id,
                "idempotency_key": idempotency_key,
                "confirmed": confirmed,
            },
        )

        run_status = "success"
        failure_error: StepError | None = None

        for order, step in enumerate(getattr(workflow, "steps", []), start=1):
            step_params = self._step_params(workflow_params, step)
            step_input = StepInput(
                step_name=step.step_id,
                payload={
                    "workflow_id": workflow.workflow_id,
                    "workflow_job_type": workflow.job_type,
                    "params": step_params,
                },
                input_id=f"{root_job_id}:{step.step_id}",
                metadata={"order": order, "required_job_type": step.required_job_type},
            )
            workflow_run.step_inputs.append(step_input)

            submission = await runner.submit_job(
                job_type=step.required_job_type,
                params=step_params,
                created_by=created_by,
                idempotency_key=f"{root_job_id}:{step.step_id}",
                confirmed=confirmed,
            )
            child_job = self._extract_child_job(submission.payload)
            if child_job is None:
                run_status = "failed"
                failure_error = StepError(
                    type=StepErrorType.system_error,
                    message="workflow step did not return a job",
                    metadata={"step_id": step.step_id, "workflow_id": workflow.workflow_id},
                )
                workflow_run.errors.append(failure_error)
                workflow_run.step_results.append(
                    StepResult(
                        step_name=step.step_id,
                        status="failed",
                        payload={},
                        artifacts=[],
                        error=failure_error,
                        metadata={
                            "job_id": None,
                            "job_type": step.required_job_type,
                            "workflow_step_id": step.step_id,
                        },
                    )
                )
                break

            step_status = self._job_status_to_step_status(str(child_job.get("status") or "success"))
            step_error = self._step_error(step_id=step.step_id, status=step_status, error=child_job.get("error"))
            artifacts = [ArtifactRef.model_validate(item) for item in child_job.get("artifacts") or []]
            step_result = StepResult(
                step_name=step.step_id,
                status=step_status,
                payload=_to_plain(child_job.get("result") or {}),
                artifacts=artifacts,
                error=step_error if step_status in {"failed", "cancelled"} else None,
                started_at=datetime.fromisoformat(child_job["started_at"]) if child_job.get("started_at") else None,
                finished_at=datetime.fromisoformat(child_job["finished_at"]) if child_job.get("finished_at") else None,
                duration_ms=child_job.get("duration_ms"),
                metadata={
                    "job_id": child_job["id"],
                    "job_type": child_job["job_type"],
                    "workflow_step_id": step.step_id,
                },
            )
            workflow_run.step_results.append(step_result)
            workflow_run.artifacts.extend(artifacts)

            if step_status in {"failed", "cancelled"}:
                run_status = step_status
                failure_error = step_error
                workflow_run.errors.append(step_error)
                break

        workflow_run.run_context.status = run_status
        workflow_run.run_context.finished_at = datetime.now(UTC)

        if run_status == "success":
            complete_result = await self._job_service.complete_job(
                job_id=root_job_id,
                result={"workflow_run": workflow_run.model_dump(mode="json")},
                audit_source=audit_source,
            )
            if complete_result.status == "ok":
                root_job = complete_result.payload["job"]
        elif run_status == "cancelled":
            cancel_result = await self._job_service.cancel_job(
                job_id=root_job_id,
                reason=f"workflow step cancelled: {failure_error.message if failure_error else 'cancelled'}",
                audit_source=audit_source,
            )
            if cancel_result.status == "ok":
                root_job = cancel_result.payload["job"]
        else:
            fail_result = await self._job_service.fail_job(
                job_id=root_job_id,
                error={
                    "type": failure_error.type.value if failure_error is not None else "system_error",
                    "message": failure_error.message if failure_error is not None else "workflow failed",
                    "workflow_id": workflow.workflow_id,
                    "run_id": root_job_id,
                },
                audit_source=audit_source,
            )
            if fail_result.status == "ok":
                root_job = fail_result.payload["job"]

        persistence_result = await self._build_workflow_run_service().record_workflow_run(
            workflow=workflow,
            workflow_run=workflow_run,
            confirmed=confirmed,
            audit_source=audit_source,
        )
        payload_warnings: list[str] = []
        if persistence_result.status != "ok":
            payload_warnings.extend(persistence_result.warnings or [])
            if persistence_result.message:
                payload_warnings.append(persistence_result.message)

        payload = {
            "workflow": workflow_summary,
            "workflow_run": workflow_run.model_dump(mode="json"),
            "job": root_job,
            "job_dir": created_result.payload.get("job_dir"),
            "log_path": created_result.payload.get("log_path"),
            "params_path": created_result.payload.get("params_path"),
            "result_path": created_result.payload.get("result_path"),
            "artifacts_path": created_result.payload.get("artifacts_path"),
            "warnings": payload_warnings,
        }

        if run_status == "success":
            return ServiceResult(status="ok", message="workflow completed", payload=payload)
        if run_status == "cancelled":
            return ServiceResult(status="ok", message="workflow cancelled", payload=payload)
        return ServiceResult(status="ok", message="workflow failed", payload=payload)
