from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import CurrentPrincipal, require_role
from src.services.security_audit_query_service import SecurityAuditQueryService


router = APIRouter(prefix="/api/ui/v1/security", tags=["ui-security-audit"])


def get_security_audit_query_service() -> SecurityAuditQueryService:
    """构建安全审计查询服务。"""
    return SecurityAuditQueryService()


@router.get("/permission-denied")
async def list_permission_denied_logs(
    actor: str | None = Query(default=None),
    source: str | None = Query(default=None),
    path: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    query_service: SecurityAuditQueryService = Depends(get_security_audit_query_service),
    _admin: CurrentPrincipal = Depends(require_role("admin")),
) -> dict[str, Any]:
    """查询权限拒绝日志。"""
    result = await query_service.list_permission_denied_logs(
        actor=actor,
        source=source,
        path=path,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.payload.get("error") or result.message or "permission denied log query failed")
    return result.payload


@router.get("/permission-denied/{event_id}")
async def get_permission_denied_log(
    event_id: str,
    query_service: SecurityAuditQueryService = Depends(get_security_audit_query_service),
    _admin: CurrentPrincipal = Depends(require_role("admin")),
) -> dict[str, Any]:
    """查询单条权限拒绝日志。"""
    result = await query_service.get_permission_denied_log(event_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "permission denied log not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.payload.get("error") or result.message or "permission denied log query failed")
    return result.payload
