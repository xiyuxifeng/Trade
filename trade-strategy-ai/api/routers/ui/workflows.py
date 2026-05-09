from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import verify_api_key
from src.services.job_service import JobService, get_job_service
from src.services.workflow_service import WorkflowService, make_workflow_service


router = APIRouter(prefix="/api/ui/v1/workflows", tags=["ui-workflows"])


class WorkflowRunRequest(BaseModel):
    """Workflow 运行请求体。"""

    params: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    idempotency_key: str | None = None


def get_workflow_service(job_service: JobService = Depends(get_job_service)) -> WorkflowService:
    """获取 WorkflowService 实例，便于测试覆盖。"""
    return make_workflow_service(job_service=job_service)


@router.get("")
async def list_workflows(
    workflow_service: WorkflowService = Depends(get_workflow_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """列出 Workflow 定义。"""
    result = await workflow_service.list_workflows()
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "workflow listing failed")
    return result.payload


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回单个 Workflow 定义。"""
    result = await workflow_service.get_workflow(workflow_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "workflow not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "workflow load failed")
    return result.payload


@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    request: WorkflowRunRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """运行一个 Workflow 并创建 Job。"""
    result = await workflow_service.run_workflow(
        workflow_id=workflow_id,
        params=request.params,
        created_by=request.created_by,
        idempotency_key=request.idempotency_key,
    )
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "workflow not found")
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message or "workflow run failed")
    return result.payload
