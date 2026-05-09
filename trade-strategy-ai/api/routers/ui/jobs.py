from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.dependencies import verify_api_key
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


class JobCancelRequest(BaseModel):
    """Job 取消请求体。"""

    reason: str | None = None

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
    job_service: JobService = Depends(get_job_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """创建一个新的 Job。"""
    validation = validate_job_submission(
        job_type=request.job_type,
        params=request.params,
        created_by=request.created_by,
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


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    request: JobCancelRequest,
    job_service: JobService = Depends(get_job_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """请求取消 Job。"""
    result = await job_service.cancel_job(job_id=job_id, reason=request.reason)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "job cancel failed")
    return result.payload
