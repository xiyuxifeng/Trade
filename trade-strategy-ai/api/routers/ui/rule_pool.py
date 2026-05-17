"""Rule Pool UI API 路由。

这是正式 Web 入口的 canonical rule-pool 路由，legacy `strategy-studio`
仍保留兼容路径，但不再作为正式导航入口。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select

from api.dependencies import verify_api_key
from api.routers.ui.strategy_studio import (
    RulePoolBatchReviewRequest,
    RulePoolDetailResponse,
    RulePoolListResponse,
    RulePoolReviewRequest,
    _has_mapped_condition,
    _parse_date,
    _serialize_rule_detail,
    _serialize_rule_summary,
    get_rule_pool_service,
    get_session_scope_factory,
)
from src.rule_pool.models import RulePool

router = APIRouter(prefix="/api/ui/v1/rule-pool", tags=["ui-rule-pool"])


@router.get("", response_model=RulePoolListResponse)
async def list_rules(
    status_filter: str | None = Query(default=None, alias="status"),
    rule_type: str | None = Query(default=None),
    mapping_status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    instrument_focus: str | None = Query(default=None),
    skip_no_mapped: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    session_scope_factory: Callable[[], Any] = Depends(get_session_scope_factory),
    _: str = Depends(verify_api_key),
) -> RulePoolListResponse:
    """列出规则池条目。"""
    conditions = []
    if status_filter:
        conditions.append(RulePool.review_status == status_filter)
    if rule_type:
        conditions.append(RulePool.rule_type == rule_type)
    if mapping_status:
        conditions.append(RulePool.mapping_status == mapping_status)
    if source_type:
        conditions.append(RulePool.source_type == source_type)
    if instrument_focus:
        conditions.append(RulePool.instrument_focus == instrument_focus)

    async with session_scope_factory() as session:
        stmt = select(RulePool)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(RulePool.created_at.desc(), RulePool.rule_id.desc())
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

    if status_filter:
        rows = [row for row in rows if getattr(row, "review_status", None) == status_filter]
    if rule_type:
        rows = [row for row in rows if getattr(row, "rule_type", None) == rule_type]
    if mapping_status:
        rows = [row for row in rows if getattr(row, "mapping_status", None) == mapping_status]
    if source_type:
        rows = [row for row in rows if getattr(row, "source_type", None) == source_type]
    if instrument_focus:
        rows = [row for row in rows if getattr(row, "instrument_focus", None) == instrument_focus]
    if skip_no_mapped:
        rows = [row for row in rows if _has_mapped_condition(row)]

    items = [_serialize_rule_summary(row) for row in rows]
    paginated = items[skip : skip + limit]
    return RulePoolListResponse(count=len(paginated), total=len(items), skip=skip, limit=limit, items=paginated)


@router.get("/{rule_id}", response_model=RulePoolDetailResponse)
async def get_rule(
    rule_id: str,
    session_scope_factory: Callable[[], Any] = Depends(get_session_scope_factory),
    _: str = Depends(verify_api_key),
) -> RulePoolDetailResponse:
    """读取单条规则详情。"""
    async with session_scope_factory() as session:
        stmt = select(RulePool).where(RulePool.rule_id == rule_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则未找到")

    return RulePoolDetailResponse(item=_serialize_rule_detail(row))


@router.post("/{rule_id}/review")
async def review_rule(
    rule_id: str,
    request: RulePoolReviewRequest,
    rule_pool_service=Depends(get_rule_pool_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """审核单条规则。"""
    try:
        result = await rule_pool_service.review_rule(
            rule_id,
            decision=request.decision,
            force=request.force,
            reviewed_by=request.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result.status == "partial":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message or "rule not found")
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message or "rule review failed")
    return result.payload


@router.post("/review-batch")
async def review_batch(
    request: RulePoolBatchReviewRequest,
    rule_pool_service=Depends(get_rule_pool_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """批量审核规则。"""
    try:
        result = await rule_pool_service.review_batch(
            decision=request.decision,
            status=request.status,
            limit=request.limit,
            force=request.force,
            reviewed_by=request.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message or "rule batch review failed")
    return result.payload
