from __future__ import annotations

from dataclasses import asdict, is_dataclass
from types import SimpleNamespace
from pathlib import Path
from typing import Any

from src.common.config import load_app_config
from src.pipelines.article_pipeline_spec import ARTICLE_PIPELINE_SPEC
from src.services.base import BaseService, ServiceResult
from src.services.config_profile_service import ConfigProfileService
from src.services.job_registry import get_job_definition
from src.services.job_runner import JobRunner
from src.services.job_service import JobService
from src.services.workflow_runner import WorkflowRunner
from src.services.workflow_service import WorkflowDefinition, WorkflowStep
from src.services.runtime_config import resolve_runtime_config


ARTICLE_PIPELINE_ID = "article_pipeline"
ARTICLE_PIPELINE_JOB_TYPE = "pipeline-run"


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
    return value


def _workflow_step(step: Any) -> WorkflowStep:
    """把 article_pipeline 的 step 归一化成 WorkflowStep。"""
    job_definition = get_job_definition(step.job_type)
    if job_definition is None:
        raise ValueError(f"unknown job type for article pipeline step: {step.job_type}")

    return WorkflowStep(
        step_id=step.step_id,
        title=step.title,
        description=step.description,
        required_job_type=step.job_type,
        parameters=list(job_definition.param_schema.fields.keys()),
        param_schema=job_definition.param_schema.model_dump(mode="json"),
        risk=job_definition.risk.value,
        requires_confirmation=job_definition.requires_confirmation,
    )


def _build_article_workflow() -> WorkflowDefinition:
    """把 article_pipeline spec 映射成可执行 WorkflowDefinition。"""
    return WorkflowDefinition(
        workflow_id=ARTICLE_PIPELINE_ID,
        title=ARTICLE_PIPELINE_SPEC.title,
        description=ARTICLE_PIPELINE_SPEC.description,
        job_type=ARTICLE_PIPELINE_JOB_TYPE,
        steps=[_workflow_step(step) for step in ARTICLE_PIPELINE_SPEC.steps],
        permissions="operator",
    )


class PipelineApplicationService(BaseService):
    """article_pipeline 的专用应用服务。"""

    service_name = "pipeline-application"

    def __init__(
        self,
        *,
        job_service: JobService | None = None,
        job_runner: JobRunner | None = None,
        workflow_runner: WorkflowRunner | None = None,
    ) -> None:
        self._job_service = job_service or JobService()
        self._job_runner = job_runner or JobRunner(job_service=self._job_service)
        self._workflow_runner = workflow_runner or WorkflowRunner(job_service=self._job_service)

    async def _normalize_params(self, params: dict[str, Any] | None) -> tuple[Any, dict[str, Any], Any]:
        """统一解析 article_pipeline 的运行参数。"""
        runtime_config = resolve_runtime_config(params)
        normalized_params = dict(params or {})

        if runtime_config.profile_id:
            runtime = await ConfigProfileService().load_profile_runtime_config(runtime_config.profile_id)
            loaded = SimpleNamespace(config=runtime.config, config_path=Path(f"profile:{runtime.profile_id}"))
            normalized_params["profile_id"] = runtime_config.profile_id
            normalized_params.pop("config_path", None)
        elif runtime_config.config_path:
            loaded = load_app_config(runtime_config.config_path)
            normalized_params["config_path"] = str(loaded.config_path)
        else:
            loaded = load_app_config("config/app.yaml")
            normalized_params["config_path"] = str(loaded.config_path)

        if normalized_params.get("cleanup"):
            normalized_params["from_step"] = "cleanup"
        if normalized_params.get("rebuild_pending"):
            normalized_params["from_step"] = "process"
            normalized_params["force"] = True
            normalized_params["skip_crawl"] = True
            normalized_params["use_db"] = True
            normalized_params.pop("rebuild_pending", None)
        if normalized_params.get("retry_failed"):
            normalized_params["from_step"] = "process"
            normalized_params["force"] = True
            normalized_params["skip_crawl"] = True
            normalized_params["use_db"] = True

        normalized_params = {
            key: value
            for key, value in normalized_params.items()
            if key
            in {
                "profile_id",
                "config_path",
                "max_articles",
                "force",
                "skip_crawl",
                "from_step",
                "use_db",
                "new_version",
                "retry_failed",
            }
            and value is not None
            and key not in {"cleanup", "rebuild_pending"}
        }
        return loaded, normalized_params, runtime_config

    @staticmethod
    def _job_matches_runtime_context(job: dict[str, Any], runtime_config: Any, loaded: Any) -> bool:
        """判断历史 Job 是否属于当前 Profile / config 上下文。"""
        params = job.get("params") if isinstance(job.get("params"), dict) else {}
        if runtime_config.profile_id:
            return str(params.get("profile_id") or "").strip() == str(runtime_config.profile_id).strip()

        runtime_config_path = str(getattr(loaded, "config_path", "") or "").strip()
        if not runtime_config_path:
            return False
        return str(params.get("config_path") or "").strip() == runtime_config_path

    async def _has_successful_job_for_context(
        self,
        *,
        job_type: str,
        runtime_config: Any,
        loaded: Any,
        page_size: int = 200,
    ) -> bool:
        """分页查询是否存在当前上下文对应的成功 Job。"""
        skip = 0
        while True:
            result = await self._job_service.list_jobs(status="success", job_type=job_type, skip=skip, limit=page_size)
            if result.status != "ok":
                return False
            items = result.payload.get("items", []) if isinstance(result.payload, dict) else []
            if not items:
                return False
            for item in items:
                if self._job_matches_runtime_context(item, runtime_config, loaded):
                    return True
            if len(items) < page_size:
                return False
            skip += page_size

    def _article_step_by_id(self, step_id: str) -> Any | None:
        """按 step_id 查找 article_pipeline 的 step 定义。"""
        return next((step for step in ARTICLE_PIPELINE_SPEC.steps if step.step_id == step_id), None)

    async def _ensure_step_prerequisites(
        self,
        *,
        step_id: str,
        loaded: Any,
        runtime_config: Any,
        base_dir: Path,
        force: bool,
        use_db: bool = False,
    ) -> None:
        """检查单步执行所需的上一步产物是否存在。"""
        if step_id == "crawl":
            return

        if step_id == "clean":
            if use_db:
                return
            if not await self._has_successful_job_for_context(job_type="crawl", runtime_config=runtime_config, loaded=loaded):
                raise ValueError("请先执行 crawl")
            return

        if step_id == "validate":
            if not await self._has_successful_job_for_context(job_type="clean", runtime_config=runtime_config, loaded=loaded):
                raise ValueError("请先执行 clean")
            return

        if step_id == "store":
            if not await self._has_successful_job_for_context(job_type="validate", runtime_config=runtime_config, loaded=loaded):
                raise ValueError("请先执行 validate")
            return

        if step_id == "process":
            if force:
                return
            pending_path = base_dir / "data" / "processed" / "pipeline" / "pending_tasks.jsonl"
            if not pending_path.exists() or not await self._has_successful_job_for_context(job_type="store", runtime_config=runtime_config, loaded=loaded):
                raise ValueError("请先执行 store")

    def _pipeline_summary(self) -> dict[str, Any]:
        """返回 canonical article_pipeline 摘要。"""
        summary = ARTICLE_PIPELINE_SPEC.summary()
        summary["workflow_id"] = ARTICLE_PIPELINE_ID
        summary["workflow"] = _build_article_workflow().summary()
        summary["metadata"] = {
            "source": "article_pipeline_spec",
            "legacy_workflow_id": ARTICLE_PIPELINE_SPEC.workflow_id,
            "root_job_type": ARTICLE_PIPELINE_JOB_TYPE,
        }
        return summary

    async def list_pipelines(self) -> ServiceResult:
        """列出可供 Web 使用的 Pipeline。"""
        return ServiceResult(
            status="ok",
            message="pipelines listed",
            payload={
                "count": 1,
                "items": [self._pipeline_summary()],
            },
        )

    async def get_pipeline(self, pipeline_id: str) -> ServiceResult:
        """返回指定 Pipeline 定义。"""
        if pipeline_id != ARTICLE_PIPELINE_ID:
            return ServiceResult(status="partial", message="pipeline not found", payload={"pipeline_id": pipeline_id})
        return ServiceResult(
            status="ok",
            message="pipeline loaded",
            payload={"pipeline": self._pipeline_summary()},
        )

    async def run_pipeline(
        self,
        *,
        pipeline_id: str,
        params: dict[str, Any] | None = None,
        created_by: str | None = None,
        idempotency_key: str | None = None,
        confirmed: bool = False,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """运行 article_pipeline。"""
        if pipeline_id != ARTICLE_PIPELINE_ID:
            return ServiceResult(status="partial", message="pipeline not found", payload={"pipeline_id": pipeline_id})

        loaded, normalized_params, runtime_config = await self._normalize_params(params)

        workflow = _build_article_workflow()
        if workflow.requires_confirmation() and not confirmed:
            return ServiceResult(
                status="error",
                message="confirmation required for high-risk pipeline",
                payload={
                    "pipeline_id": pipeline_id,
                    "workflow_id": workflow.workflow_id,
                    "requires_confirmation": True,
                },
            )

        result = await self._workflow_runner.run_workflow(
            workflow=workflow,
            params=normalized_params,
            created_by=created_by,
            idempotency_key=idempotency_key,
            audit_source=audit_source,
            confirmed=confirmed,
        )
        payload = dict(result.payload)
        payload["pipeline"] = self._pipeline_summary()
        payload["params"] = _to_plain(normalized_params)
        if runtime_config.source == "config_path":
            payload["config_path"] = str(loaded.config_path)
        if runtime_config.profile_id is not None:
            payload["profile_id"] = runtime_config.profile_id
        return ServiceResult(status=result.status, message=result.message, payload=payload)

    async def run_pipeline_step(
        self,
        *,
        pipeline_id: str,
        step_id: str,
        params: dict[str, Any] | None = None,
        created_by: str | None = None,
        idempotency_key: str | None = None,
        confirmed: bool = False,
        audit_source: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """运行 article_pipeline 的单个 step，并映射到对应的 Job。"""
        if pipeline_id != ARTICLE_PIPELINE_ID:
            return ServiceResult(status="partial", message="pipeline not found", payload={"pipeline_id": pipeline_id})

        step_spec = self._article_step_by_id(step_id)
        if step_spec is None:
            return ServiceResult(status="partial", message="step not found", payload={"pipeline_id": pipeline_id, "step_id": step_id})

        loaded, normalized_params, runtime_config = await self._normalize_params(params)
        job_definition = get_job_definition(step_spec.job_type)
        if job_definition is None:
            return ServiceResult(
                status="partial",
                message="job definition not found",
                payload={"pipeline_id": pipeline_id, "step_id": step_id, "job_type": step_spec.job_type},
            )
        await self._ensure_step_prerequisites(
            step_id=step_spec.step_id,
            loaded=loaded,
            runtime_config=runtime_config,
            base_dir=Path(loaded.config_path).parent.parent if Path(loaded.config_path).parent.name == "config" else Path(loaded.config_path).parent,
            force=bool(normalized_params.get("force")),
            use_db=bool(normalized_params.get("use_db")),
        )

        allowed_params = set(job_definition.param_schema.fields.keys())
        normalized_params = {key: value for key, value in normalized_params.items() if key in allowed_params and value is not None}

        result = await self._job_runner.submit_job(
            job_type=step_spec.job_type,
            params=normalized_params,
            created_by=created_by,
            idempotency_key=idempotency_key,
            confirmed=confirmed,
        )
        if result.status != "ok":
            return result

        payload = dict(result.payload)
        execution = payload.get("execution") if isinstance(payload.get("execution"), dict) else {}
        job = {}
        if isinstance(execution, dict) and isinstance(execution.get("job"), dict):
            job = execution["job"]
        elif isinstance(payload.get("job"), dict):
            job = payload["job"]

        payload["pipeline"] = self._pipeline_summary()
        payload["step"] = _to_plain(step_spec)
        payload["params"] = _to_plain(normalized_params)
        if runtime_config.source == "config_path":
            payload["config_path"] = str(loaded.config_path)
        if runtime_config.profile_id is not None:
            payload["profile_id"] = runtime_config.profile_id
        if job:
            payload["job"] = job
        return ServiceResult(
            status=result.status,
            message=result.message,
            payload=payload,
            warnings=getattr(result, "warnings", []) or [],
        )


def make_pipeline_application_service(
    *,
    job_service: JobService | None = None,
    job_runner: JobRunner | None = None,
    workflow_runner: WorkflowRunner | None = None,
) -> PipelineApplicationService:
    """工厂函数，方便 DI 和测试替换。"""
    return PipelineApplicationService(job_service=job_service, job_runner=job_runner, workflow_runner=workflow_runner)
