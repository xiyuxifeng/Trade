from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.services.job_service import JobService, get_job_service
from src.services.workflow_service import WorkflowService, make_workflow_service


router = APIRouter(prefix="/api/ui/v1/workflows", tags=["ui-workflows"])


class WorkflowRunRequest(BaseModel):
    """Workflow 运行请求体。"""

    params: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    idempotency_key: str | None = None
    confirmed: bool = False


def _audit_source_from_request(request: Request) -> dict[str, Any]:
    """提取工作流运行的请求来源。"""
    client_host = request.client.host if request.client is not None else None
    return {
        "channel": "ui",
        "path": request.url.path,
        "method": request.method,
        "client_host": client_host,
        "user_agent": request.headers.get("user-agent"),
        "forwarded_for": request.headers.get("x-forwarded-for"),
    }


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
    http_request: Request,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    _role_principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """运行一个 Workflow 并创建 Job。"""
    result = await workflow_service.run_workflow(
        workflow_id=workflow_id,
        params=request.params,
        created_by=request.created_by,
        idempotency_key=request.idempotency_key,
        confirmed=request.confirmed,
        audit_source=_audit_source_from_request(http_request),
    )
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "workflow not found")
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message or "workflow run failed")
    return result.payload
