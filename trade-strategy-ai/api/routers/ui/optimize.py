"""Optimize UI API 路由。

这是正式 Web 入口的 canonical optimize 路由，legacy `strategy-studio`
仍保留兼容路径，但不再作为正式导航入口。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select

from api.dependencies import verify_api_key
from api.routers.ui.strategy_studio import (
    ActiveTraderFilterConfig,
    ActiveTraderFilterRequest,
    CandidateCreateRequest,
    CandidateCreateResponse,
    RuleValidationInput,
    VersionDetailResponse,
    VersionListResponse,
    _parse_date,
    _serialize_strategy_version,
    _serialize_version_detail,
    _serialize_version_summary,
    _to_backtest_result,
    _to_rule_validation,
    _to_strategy_adjustment,
    _to_strategy_recommendation,
    get_optimize_service,
    get_session_scope_factory,
    get_strategy_library_service,
)
from src.models.trader_strategy_version import TraderStrategyVersion

router = APIRouter(prefix="/api/ui/v1/optimize", tags=["ui-optimize"])


@router.get("/versions", response_model=VersionListResponse)
async def list_versions(
    trader_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    version_type: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    session_scope_factory: Callable[[], Any] = Depends(get_session_scope_factory),
    _: str = Depends(verify_api_key),
) -> VersionListResponse:
    """列出候选/正式版本。"""
    conditions = []
    if trader_id:
        conditions.append(TraderStrategyVersion.trader_id == trader_id)
    if status_filter:
        conditions.append(TraderStrategyVersion.status == status_filter)
    if date_from:
        conditions.append(TraderStrategyVersion.strategy_date >= _parse_date(date_from))
    if date_to:
        conditions.append(TraderStrategyVersion.strategy_date <= _parse_date(date_to))

    async with session_scope_factory() as session:
        stmt = select(TraderStrategyVersion)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(TraderStrategyVersion.strategy_date.desc(), TraderStrategyVersion.version_name.desc())
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

    if version_type:
        rows = [row for row in rows if getattr(row, "version_type", "manual") == version_type]

    items = [_serialize_version_summary(row) for row in rows]
    paginated = items[skip : skip + limit]
    return VersionListResponse(count=len(paginated), total=len(items), skip=skip, limit=limit, items=paginated)


@router.get("/versions/{version_id}", response_model=VersionDetailResponse)
async def get_version(
    version_id: str,
    session_scope_factory: Callable[[], Any] = Depends(get_session_scope_factory),
    _: str = Depends(verify_api_key),
) -> VersionDetailResponse:
    """读取单个版本详情。"""
    async with session_scope_factory() as session:
        stmt = select(TraderStrategyVersion).where(TraderStrategyVersion.version_name == version_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="策略版本未找到")

    return VersionDetailResponse(item=_serialize_version_detail(row))


@router.post("/advise-rule-validations")
async def advise_rule_validations(
    request: list[RuleValidationInput],
    optimize_service=Depends(get_optimize_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """基于规则验真结果生成优化建议。"""
    result = optimize_service.advise_rule_validations([_to_rule_validation(item) for item in request])
    return result.payload


@router.post("/filter-active-traders")
async def filter_active_traders(
    request: ActiveTraderFilterRequest,
    optimize_service=Depends(get_optimize_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """筛选活跃 trader。"""
    config = ActiveTraderFilterConfig(**request.config.model_dump()) if request.config else None
    backtest_results = {item.trader_id: _to_backtest_result(item) for item in request.backtest_results}
    rule_validations = {
        trader_id: [_to_rule_validation(item) for item in items]
        for trader_id, items in request.rule_validations.items()
    }
    result = optimize_service.filter_active_traders(
        backtest_results=backtest_results,
        config=config,
        rule_validations=rule_validations or None,
    )
    return result.payload


@router.post("/create-candidate", response_model=CandidateCreateResponse)
async def create_candidate(
    request: CandidateCreateRequest,
    strategy_service=Depends(get_strategy_library_service),
    session_scope_factory: Callable[[], Any] = Depends(get_session_scope_factory),
    _: str = Depends(verify_api_key),
) -> CandidateCreateResponse:
    """创建候选版本。"""
    adjustments = [_to_strategy_adjustment(item) for item in request.adjustments]
    recommendations = [_to_strategy_recommendation(item) for item in request.recommendations]

    async with session_scope_factory() as session:
        parent = await strategy_service.get_version(session=session, version_id=request.parent_version_id)
        if parent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="父版本未找到")

        candidate = await strategy_service.create_candidate_version(
            session=session,
            trader_id=request.trader_id,
            strategy_date=request.strategy_date,
            parent_version_id=request.parent_version_id,
            adjustments=adjustments,
            recommendations=recommendations,
            notes=request.notes,
        )
        await session.commit()

    return CandidateCreateResponse(item=_serialize_strategy_version(candidate))
