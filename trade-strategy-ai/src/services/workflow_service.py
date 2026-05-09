from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.services.base import BaseService, ServiceResult
from src.services.job_registry import get_job_definition, validate_job_submission
from src.services.job_service import JobService


@dataclass(frozen=True)
class WorkflowStep:
    """单个 Workflow 步骤定义。"""

    step_id: str
    title: str
    description: str
    required_job_type: str
    parameters: list[str] = field(default_factory=list)
    risk: str = "medium"
    requires_confirmation: bool = False


@dataclass(frozen=True)
class WorkflowDefinition:
    """Workflow 的 UI 展示定义。"""

    workflow_id: str
    title: str
    description: str
    job_type: str
    steps: list[WorkflowStep]
    permissions: str = "operator"

    def summary(self) -> dict[str, Any]:
        """返回 UI 可直接展示的摘要。"""
        job_definition = get_job_definition(self.job_type)
        return {
            "workflow_id": self.workflow_id,
            "title": self.title,
            "description": self.description,
            "job_type": self.job_type,
            "permissions": self.permissions,
            "job_definition": job_definition.summary() if job_definition is not None else None,
            "steps": [
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "description": step.description,
                    "required_job_type": step.required_job_type,
                    "parameters": step.parameters,
                    "risk": step.risk,
                    "requires_confirmation": step.requires_confirmation,
                }
                for step in self.steps
            ],
        }


def _workflow(
    workflow_id: str,
    title: str,
    description: str,
    job_type: str,
    *,
    steps: list[WorkflowStep],
    permissions: str = "operator",
) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=workflow_id,
        title=title,
        description=description,
        job_type=job_type,
        steps=steps,
        permissions=permissions,
    )


DEFAULT_WORKFLOWS: tuple[WorkflowDefinition, ...] = (
    _workflow(
        "pre-market",
        "盘前流程",
        "执行盘前日报生成并输出结果。",
        "run-pre-market",
        steps=[
            WorkflowStep(
                step_id="run-pre-market",
                title="盘前执行",
                description="生成盘前日报和可选 HTML。",
                required_job_type="run-pre-market",
                parameters=["config_path", "as_of_date", "force", "export_html"],
                risk="medium",
            )
        ],
    ),
    _workflow(
        "after-close",
        "盘后流程",
        "执行盘后考核生成并输出结果。",
        "run-after-close",
        steps=[
            WorkflowStep(
                step_id="run-after-close",
                title="盘后执行",
                description="生成盘后考核和可选 HTML。",
                required_job_type="run-after-close",
                parameters=["config_path", "as_of_date", "force", "export_html"],
                risk="medium",
            )
        ],
    ),
    _workflow(
        "pipeline-run",
        "完整 Pipeline",
        "从抓取到清洗、验证和导出的完整链路。",
        "pipeline-run",
        steps=[
            WorkflowStep(
                step_id="pipeline-run",
                title="执行完整链路",
                description="运行完整 pipeline。",
                required_job_type="pipeline-run",
                parameters=["config_path", "max_articles", "force", "skip_crawl", "from_step", "use_db", "new_version"],
                risk="medium",
            )
        ],
    ),
    _workflow(
        "pipeline-step",
        "Pipeline 单步",
        "从指定步骤开始执行 pipeline。",
        "pipeline-step",
        steps=[
            WorkflowStep(
                step_id="pipeline-step",
                title="执行单步",
                description="从指定步骤开始运行 pipeline。",
                required_job_type="pipeline-step",
                parameters=["step", "config_path", "max_articles", "force", "use_db", "new_version"],
                risk="medium",
            )
        ],
    ),
)

_WORKFLOW_MAP: dict[str, WorkflowDefinition] = {item.workflow_id: item for item in DEFAULT_WORKFLOWS}


class WorkflowService(BaseService):
    """Workflow API 的 UI 服务。"""

    service_name = "workflow"

    def __init__(self, *, job_service: JobService | None = None) -> None:
        self._job_service = job_service or JobService()

    async def list_workflows(self) -> ServiceResult:
        """列出默认工作流定义。"""
        return ServiceResult(
            status="ok",
            message="workflows listed",
            payload={
                "count": len(DEFAULT_WORKFLOWS),
                "items": [workflow.summary() for workflow in DEFAULT_WORKFLOWS],
            },
        )

    async def get_workflow(self, workflow_id: str) -> ServiceResult:
        """按 workflow_id 查询定义。"""
        workflow = _WORKFLOW_MAP.get(workflow_id)
        if workflow is None:
            return ServiceResult(status="partial", message="workflow not found", payload={"workflow_id": workflow_id})
        return ServiceResult(status="ok", message="workflow loaded", payload={"workflow": workflow.summary()})

    async def run_workflow(
        self,
        *,
        workflow_id: str,
        params: dict[str, Any] | None = None,
        created_by: str | None = None,
        idempotency_key: str | None = None,
    ) -> ServiceResult:
        """将工作流运行映射到对应 Job。"""
        workflow = _WORKFLOW_MAP.get(workflow_id)
        if workflow is None:
            return ServiceResult(status="partial", message="workflow not found", payload={"workflow_id": workflow_id})

        validation = validate_job_submission(
            job_type=workflow.job_type,
            params=params,
            created_by=created_by,
        )
        if validation.status != "ok":
            return ServiceResult(status="error", message=validation.message or "invalid workflow params", payload=validation.payload)

        created = await self._job_service.create_job(
            job_type=workflow.job_type,
            params=validation.payload["params"],
            created_by=created_by,
            idempotency_key=idempotency_key,
        )
        if created.status != "ok":
            return created

        return ServiceResult(
            status="ok",
            message="workflow started",
            payload={
                "workflow": workflow.summary(),
                "job": created.payload["job"],
                "job_dir": created.payload.get("job_dir"),
                "log_path": created.payload.get("log_path"),
                "params_path": created.payload.get("params_path"),
                "result_path": created.payload.get("result_path"),
                "artifacts_path": created.payload.get("artifacts_path"),
            },
        )


def make_workflow_service(job_service: JobService | None = None) -> WorkflowService:
    """构造 WorkflowService 实例，供 API 层依赖注入复用。"""
    return WorkflowService(job_service=job_service)
