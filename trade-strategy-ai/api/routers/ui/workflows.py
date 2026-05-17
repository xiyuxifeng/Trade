from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from api.schemas.workflow import WorkflowRunDetailResponse, WorkflowRunListResponse, WorkflowRunStepListResponse
from src.services.job_service import JobService, get_job_service
from src.services.workflow_run_service import WorkflowRunService, make_workflow_run_service
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


def get_workflow_run_service() -> WorkflowRunService:
    """获取 WorkflowRunService 实例，便于测试覆盖。"""
    return make_workflow_run_service()


def _structured_error(error_type: str, message: str, detail: str | None = None, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """构造统一的结构化错误。"""
    return {
        "type": error_type,
        "message": message,
        "detail": detail,
        "metadata": metadata or {},
    }


def _raise_run_query_error(result: Any) -> None:
    """把 workflow run service 的错误映射成 HTTPException。"""
    error = (result.payload or {}).get("error") if hasattr(result, "payload") else None
    if not isinstance(error, dict):
        raise HTTPException(status_code=400, detail=_structured_error("query_failed", result.message or "query failed"))

    error_type = str(error.get("type") or "query_failed")
    message = str(error.get("message") or result.message or "query failed")
    status_code = 400
    if error_type == "workflow_run_not_found":
        status_code = 404
    elif error_type == "permission_denied":
        status_code = 403
    elif error_type == "invalid_query":
        status_code = 422
    elif error_type == "partial_data":
        status_code = 206
    elif error_type == "api_unavailable":
        status_code = 503
    elif error_type == "empty_data":
        status_code = 404

    raise HTTPException(status_code=status_code, detail=_structured_error(error_type, message, error.get("detail"), metadata=error.get("metadata") or {}))


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


@router.get("/runs", response_model=WorkflowRunListResponse)
async def list_workflow_runs(
    workflow_id: str | None = None,
    status: str | None = None,
    created_by: str | None = None,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    workflow_run_service: WorkflowRunService = Depends(get_workflow_run_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询 workflow runs 列表。"""
    result = await workflow_run_service.list_workflow_runs(
        workflow_id=workflow_id,
        status=status,
        created_by=created_by,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    if result.status != "ok":
        _raise_run_query_error(result)
    return result.payload


@router.get("/runs/{workflow_run_id}", response_model=WorkflowRunDetailResponse)
async def get_workflow_run(
    workflow_run_id: str,
    workflow_run_service: WorkflowRunService = Depends(get_workflow_run_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询单个 workflow run 详情。"""
    result = await workflow_run_service.get_workflow_run(workflow_run_id)
    if result.status != "ok":
        _raise_run_query_error(result)
    return result.payload


@router.get("/runs/{workflow_run_id}/steps", response_model=WorkflowRunStepListResponse)
async def list_workflow_run_steps(
    workflow_run_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    workflow_run_service: WorkflowRunService = Depends(get_workflow_run_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询单个 workflow run 的 step 明细。"""
    result = await workflow_run_service.list_workflow_run_steps(workflow_run_id, limit=limit, offset=offset)
    if result.status != "ok":
        _raise_run_query_error(result)
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
