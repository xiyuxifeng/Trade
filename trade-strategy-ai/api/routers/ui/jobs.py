from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from api.dependencies import CurrentPrincipal, require_role, verify_api_key
from src.services.job_registry import get_job_definition, list_job_definitions, validate_job_submission
from src.services.job_service import JobService, get_job_service


router = APIRouter(prefix="/api/ui/v1/jobs", tags=["ui-jobs"])


class JobSubmissionRequest(BaseModel):
    """UI 提交 Job 的请求体。"""

    job_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    idempotency_key: str | None = None
    max_retries: int = 3
    retry_backoff_seconds: int = 0
    timeout_seconds: int | None = None
    confirmed: bool = False


class JobCancelRequest(BaseModel):
    """Job 取消请求体。"""

    reason: str | None = None


class JobControlRequest(BaseModel):
    """Job 控制请求体。"""

    reason: str | None = None


def _audit_source_from_request(request: Request) -> dict[str, Any]:
    """提取请求来源，写入 Job 审计记录。"""
    client_host = request.client.host if request.client is not None else None
    forwarded_for = request.headers.get("x-forwarded-for")
    return {
        "channel": "ui",
        "path": request.url.path,
        "method": request.method,
        "client_host": client_host,
        "user_agent": request.headers.get("user-agent"),
        "forwarded_for": forwarded_for,
    }

@router.get("/definitions")
async def list_definitions(_: str = Depends(verify_api_key)) -> list[dict[str, Any]]:
    """返回所有 Job 白名单定义。"""
    return [definition.summary() for definition in list_job_definitions()]


@router.get("/definitions/{job_type}")
async def get_definition(job_type: str, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    """返回单个 Job 定义。"""
    definition = get_job_definition(job_type)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"unknown job type: {job_type}")
    return definition.summary()


@router.post("")
async def create_job(
    request: JobSubmissionRequest,
    http_request: Request,
    job_service: JobService = Depends(get_job_service),
    _role_principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """创建一个新的 Job。"""
    validation = validate_job_submission(
        job_type=request.job_type,
        params=request.params,
        created_by=request.created_by,
        confirmed=request.confirmed,
    )
    if validation.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=validation.message or "invalid job submission")

    result = await job_service.create_job(
        job_type=request.job_type,
        params=validation.payload["params"],
        created_by=request.created_by,
        idempotency_key=request.idempotency_key,
        max_retries=request.max_retries,
        retry_backoff_seconds=request.retry_backoff_seconds,
        timeout_seconds=request.timeout_seconds,
        confirmed=request.confirmed,
        audit_source=_audit_source_from_request(http_request),
    )
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job creation failed")
    return result.payload


@router.post("/validate")
async def validate_submission(
    request: JobSubmissionRequest,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """校验 UI 提交的 Job 参数。"""
    result = validate_job_submission(job_type=request.job_type, params=request.params, created_by=request.created_by)
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "invalid job submission")
    return result.payload


@router.get("")
async def list_jobs(
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    created_by: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    job_service: JobService = Depends(get_job_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """列出 Job。"""
    result = await job_service.list_jobs(status=status, job_type=job_type, created_by=created_by, skip=skip, limit=limit)
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job listing failed")
    return result.payload


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回单个 Job 详情。"""
    result = await job_service.get_job(job_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job load failed")
    return result.payload


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回 Job 日志行。"""
    result = await job_service.get_job(job_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job load failed")

    log_path = Path(result.payload["log_path"])
    items = log_path.read_text(encoding="utf-8").splitlines() if log_path.exists() else []
    return {"job_id": job_id, "log_path": str(log_path), "count": len(items), "items": items}


@router.get("/{job_id}/timeline")
async def get_job_timeline(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回 Job 时间线事件。"""
    result = await job_service.get_job_timeline(job_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail="job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job load failed")

    return result.payload


@router.get("/{job_id}/artifacts")
async def get_job_artifacts(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """返回 Job 绑定的产物引用。"""
    result = await job_service.get_job(job_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail="job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job load failed")

    job = result.payload["job"]
    items = job.get("artifacts") or []
    return {"job_id": job_id, "count": len(items), "items": items}


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    request: JobCancelRequest,
    http_request: Request,
    job_service: JobService = Depends(get_job_service),
    _role_principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """请求取消 Job。"""
    result = await job_service.cancel_job(job_id=job_id, reason=request.reason, audit_source=_audit_source_from_request(http_request))
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job cancel failed")
    return result.payload


@router.post("/{job_id}/pause")
async def pause_job(
    job_id: str,
    request: JobControlRequest,
    http_request: Request,
    job_service: JobService = Depends(get_job_service),
    principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """请求暂停 Job。"""
    result = await job_service.pause_job(
        job_id=job_id,
        actor=principal.api_key_label or principal.role,
        reason=request.reason,
        audit_source=_audit_source_from_request(http_request),
    )
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job pause failed")
    return result.payload


@router.post("/{job_id}/resume")
async def resume_job(
    job_id: str,
    http_request: Request,
    job_service: JobService = Depends(get_job_service),
    principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """请求恢复 paused Job。"""
    result = await job_service.resume_job(
        job_id=job_id,
        actor=principal.api_key_label or principal.role,
        audit_source=_audit_source_from_request(http_request),
    )
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job resume failed")
    return result.payload


@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    request: JobControlRequest,
    http_request: Request,
    job_service: JobService = Depends(get_job_service),
    principal: CurrentPrincipal = Depends(require_role("operator")),
) -> dict[str, Any]:
    """请求重试 failed Job。"""
    result = await job_service.retry_job(
        job_id=job_id,
        actor=principal.api_key_label or principal.role,
        audit_source=_audit_source_from_request(http_request),
    )
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job retry failed")
    return result.payload
