from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import require_role, verify_api_key
from src.services.data_audit_query_service import DataAuditQueryService, get_data_audit_query_service


router = APIRouter(prefix="/api/ui/v1/data-audits", tags=["ui-data-audits"])


@router.get("")
async def list_data_audits(
    event_type: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    source: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    query_service: DataAuditQueryService = Depends(get_data_audit_query_service),
    _: str = Depends(verify_api_key),
    _admin: Any = Depends(require_role("admin")),
) -> dict[str, Any]:
    """查询数据写入审计记录。"""
    result = await query_service.list_data_audits(
        event_type=event_type,
        actor=actor,
        source=source,
        entity_type=entity_type,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.payload.get("error") or result.message or "data audit query failed")
    return result.payload


@router.get("/{event_id}")
async def get_data_audit_detail(
    event_id: str,
    query_service: DataAuditQueryService = Depends(get_data_audit_query_service),
    _: str = Depends(verify_api_key),
    _admin: Any = Depends(require_role("admin")),
) -> dict[str, Any]:
    """查询单条数据审计记录。"""
    result = await query_service.get_data_audit(event_id)
    if result.status == "partial":
        raise HTTPException(status_code=404, detail=result.message or "data audit not found")
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.payload.get("error") or result.message or "data audit query failed")
    return result.payload

