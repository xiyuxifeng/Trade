from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import require_role, verify_api_key
from src.services.job_audit_query_service import JobAuditQueryService


router = APIRouter(prefix="/api/ui/v1/job-audits", tags=["ui-job-audits"])


def get_job_audit_query_service() -> JobAuditQueryService:
    """构建 Job 审计查询服务。"""
    return JobAuditQueryService()


@router.get("")
async def list_job_audits(
    actor: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    operation: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    confirmed: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    query_service: JobAuditQueryService = Depends(get_job_audit_query_service),
    _: str = Depends(verify_api_key),
    _admin: Any = Depends(require_role("admin")),
) -> dict[str, Any]:
    """查询 Job 审计记录。"""
    result = await query_service.list_job_audits(
        actor=actor,
        job_type=job_type,
        operation=operation,
        start_date=start_date,
        end_date=end_date,
        confirmed=confirmed,
        skip=skip,
        limit=limit,
    )
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.payload.get("error") or result.message or "job audit query failed")
    return result.payload


@router.get("/{job_id}")
async def get_job_audit_detail(
    job_id: str,
    query_service: JobAuditQueryService = Depends(get_job_audit_query_service),
    _: str = Depends(verify_api_key),
    _admin: Any = Depends(require_role("admin")),
) -> dict[str, Any]:
    """查询单个 Job 的审计详情。"""
    result = await query_service.get_job_audit_detail(job_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "job not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.payload.get("error") or result.message or "job audit query failed")
    return result.payload
