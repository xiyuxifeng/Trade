from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from src.common.config import load_app_config
from src.pipelines.article_pipeline_spec import ARTICLE_PIPELINE_SPEC
from src.services.base import BaseService, ServiceResult
from src.services.job_registry import get_job_definition
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

    step_parameters = {
        "crawl": ["config_path", "max_articles"],
        "pipeline-run": [
            "config_path",
            "max_articles",
            "force",
            "skip_crawl",
            "from_step",
            "use_db",
            "new_version",
            "retry_failed",
        ],
    }.get(step.job_type, list(job_definition.param_schema.fields.keys()))

    return WorkflowStep(
        step_id=step.step_id,
        title=step.title,
        description=step.description,
        required_job_type=step.job_type,
        parameters=step_parameters,
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
        workflow_runner: WorkflowRunner | None = None,
    ) -> None:
        self._job_service = job_service or JobService()
        self._workflow_runner = workflow_runner or WorkflowRunner(job_service=self._job_service)

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

        runtime_config = resolve_runtime_config(params)
        normalized_params = dict(params or {})
        loaded = load_app_config((params or {}).get("config_path", "config/app.yaml"))
        normalized_params["config_path"] = str(loaded.config_path)
        normalized_params.pop("profile_id", None)

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
            if key in {
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
            and key != "cleanup"
            and key != "rebuild_pending"
        }

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
        payload["config_path"] = str(loaded.config_path)
        if runtime_config.profile_id is not None:
            payload["profile_id"] = runtime_config.profile_id
        return ServiceResult(status=result.status, message=result.message, payload=payload)


def make_pipeline_application_service(
    *,
    job_service: JobService | None = None,
    workflow_runner: WorkflowRunner | None = None,
) -> PipelineApplicationService:
    """工厂函数，方便 DI 和测试替换。"""
    return PipelineApplicationService(job_service=job_service, workflow_runner=workflow_runner)
