from __future__ import annotations

from typing import Any

from src.pipelines.article_pipeline_spec import ARTICLE_PIPELINE_SPECS, PipelineSpec
from src.pipelines.backtest_pipeline_spec import BACKTEST_PIPELINE_SPECS
from src.pipelines.strategy_pipeline_spec import STRATEGY_PIPELINE_SPECS
from src.services.job_registry import JOB_DEFINITIONS, JobDefinition
from src.services.workflow_service import DEFAULT_WORKFLOWS, WorkflowDefinition, WorkflowStep


def _job_contract(definition: JobDefinition) -> dict[str, Any]:
    """把 JobDefinition 归一化成 canonical contract。"""
    payload = definition.model_dump(mode="json")
    return {
        "job_type": payload["job_type"],
        "title": payload["title"],
        "description": payload["description"],
        "permission": payload["permission"],
        "risk": payload["risk"],
        "can_retry": payload["can_retry"],
        "can_run_concurrently": payload["can_run_concurrently"],
        "concurrency_group": payload["concurrency_group"],
        "requires_confirmation": payload["requires_confirmation"],
        "runnable": payload["runnable"],
        "param_schema": payload["param_schema"],
        "metadata": {
            "source": "job_registry",
            "service_name": payload["service_name"],
            "handler_name": payload["handler_name"],
        },
    }


def _workflow_step_contract(step: WorkflowStep) -> dict[str, Any]:
    """把 WorkflowStep 归一化成 canonical contract。"""
    return {
        "step_id": step.step_id,
        "title": step.title,
        "description": step.description,
        "required_job_type": step.required_job_type,
        "parameters": list(step.parameters),
        "param_schema": step.param_schema,
        "risk": step.risk,
        "requires_confirmation": step.requires_confirmation,
    }


def _workflow_contract(definition: WorkflowDefinition) -> dict[str, Any]:
    """把 WorkflowDefinition 归一化成 canonical contract。"""
    return {
        "workflow_id": definition.workflow_id,
        "title": definition.title,
        "description": definition.description,
        "job_type": definition.job_type,
        "permissions": definition.permissions,
        "steps": [_workflow_step_contract(step) for step in definition.steps],
        "metadata": {
            "source": "workflow_service",
        },
    }


def list_job_contracts() -> list[dict[str, Any]]:
    """列出所有 Job canonical contract。"""
    return [_job_contract(definition) for definition in JOB_DEFINITIONS]


def get_job_contract(job_type: str) -> dict[str, Any] | None:
    """按 job_type 获取 Job canonical contract。"""
    for definition in JOB_DEFINITIONS:
        if definition.job_type == job_type:
            return _job_contract(definition)
    return None


def list_workflow_contracts() -> list[dict[str, Any]]:
    """列出所有 Workflow canonical contract。"""
    return [_workflow_contract(definition) for definition in DEFAULT_WORKFLOWS]


def get_workflow_contract(workflow_id: str) -> dict[str, Any] | None:
    """按 workflow_id 获取 Workflow canonical contract。"""
    for definition in DEFAULT_WORKFLOWS:
        if definition.workflow_id == workflow_id:
            return _workflow_contract(definition)
    return None


def _pipeline_contract(definition: PipelineSpec) -> dict[str, Any]:
    """把 PipelineSpec 归一化成 canonical contract。"""
    return definition.summary()


def list_pipeline_contracts() -> list[dict[str, Any]]:
    """列出所有 Pipeline canonical contract。"""
    return [_pipeline_contract(definition) for definition in (*ARTICLE_PIPELINE_SPECS, *BACKTEST_PIPELINE_SPECS, *STRATEGY_PIPELINE_SPECS)]


def get_pipeline_contract(pipeline_id: str) -> dict[str, Any] | None:
    """按 pipeline_id 获取 Pipeline canonical contract。"""
    for definition in (*ARTICLE_PIPELINE_SPECS, *BACKTEST_PIPELINE_SPECS, *STRATEGY_PIPELINE_SPECS):
        if definition.pipeline_id == pipeline_id:
            return _pipeline_contract(definition)
    return None
