"""Rule Pool UI API 路由。

这是正式 Web 入口的 canonical rule-pool 路由，legacy `strategy-studio`
仍保留兼容路径，但不再作为正式导航入口。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
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
from src.services.rule_applicability_service import (
    DEFAULT_MIN_SAMPLE_COUNT,
    DEFAULT_PROFILE_VERSION,
    RuleApplicabilityService,
)

router = APIRouter(prefix="/api/ui/v1/rule-pool", tags=["ui-rule-pool"])


class RuleApplicabilityRegimeItem(BaseModel):
    """Rule 适用性 regime 记录。"""

    regime_label: str
    decision: str
    score: float
    sample_count: int
    win_rate: float | None = None
    avg_return: float | None = None
    avg_win_return: float | None = None
    avg_loss_return: float | None = None
    max_drawdown: float | None = None
    profit_factor: float | None = None
    confidence: float
    low_sample: bool
    reason: str
    evidence: list[str] = Field(default_factory=list)


class RuleApplicabilityProfileItem(BaseModel):
    """Rule 适用性画像详情。"""

    profile_id: str
    rule_id: str
    profile_version: str
    source_backtest_id: str
    source_rule_version: str | None = None
    market_regime_version: str | None = None
    source_feature_version: str | None = None
    review_status: str
    min_sample_count: int
    confidence: float
    applicable_regimes: list[RuleApplicabilityRegimeItem] = Field(default_factory=list)
    blocked_regimes: list[RuleApplicabilityRegimeItem] = Field(default_factory=list)
    neutral_regimes: list[RuleApplicabilityRegimeItem] = Field(default_factory=list)
    best_market_conditions: dict[str, Any] = Field(default_factory=dict)
    worst_market_conditions: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    storage_ref: dict[str, Any] = Field(default_factory=dict)
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RuleApplicabilityListResponse(BaseModel):
    """Rule 适用性画像列表响应。"""

    status: str = "success"
    count: int
    total: int
    skip: int
    limit: int
    items: list[RuleApplicabilityProfileItem]


class RuleApplicabilityDetailResponse(BaseModel):
    """Rule 适用性画像详情响应。"""

    status: str = "success"
    item: RuleApplicabilityProfileItem


class RuleApplicabilityGenerateRequest(BaseModel):
    """生成 Rule 适用性画像请求。"""

    source_backtest_id: str
    profile_version: str = DEFAULT_PROFILE_VERSION
    min_sample_count: int = DEFAULT_MIN_SAMPLE_COUNT
    review_status: str = "draft"
    reviewed_by: str = "web"


class RuleApplicabilityReviewRequest(BaseModel):
    """审核 Rule 适用性画像请求。"""

    review_status: str
    reviewed_by: str = "web"


class RulePoolFilterOptionsResponse(BaseModel):
    """规则池筛选选项响应。"""

    status: str = "success"
    review_statuses: list[str] = Field(default_factory=list)
    mapping_statuses: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    rule_types: list[str] = Field(default_factory=list)
    instrument_focuses: list[str] = Field(default_factory=list)


def get_rule_applicability_service() -> RuleApplicabilityService:
    """获取 Rule 适用性画像服务实例。"""
    return RuleApplicabilityService()


def _serialize_applicability_item(value: Any) -> RuleApplicabilityProfileItem:
    """把 service payload 转成前端响应。"""
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if isinstance(value, dict) and isinstance(value.get("profile_id"), UUID):
        value = {**value, "profile_id": str(value["profile_id"])}
    return RuleApplicabilityProfileItem.model_validate(value)


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


@router.get("/filter-options", response_model=RulePoolFilterOptionsResponse)
async def list_filter_options(
    rule_pool_service=Depends(get_rule_pool_service),
    _: str = Depends(verify_api_key),
) -> RulePoolFilterOptionsResponse:
    """列出规则池筛选下拉选项。"""
    result = await rule_pool_service.list_filter_options()
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message or "rule pool filter options failed")
    payload = result.payload or {}
    return RulePoolFilterOptionsResponse(
        review_statuses=list(payload.get("review_statuses", [])),
        mapping_statuses=list(payload.get("mapping_statuses", [])),
        source_types=list(payload.get("source_types", [])),
        rule_types=list(payload.get("rule_types", [])),
        instrument_focuses=list(payload.get("instrument_focuses", [])),
    )


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


@router.get("/{rule_id}/applicability-profiles", response_model=RuleApplicabilityListResponse)
async def list_rule_applicability_profiles(
    rule_id: str,
    review_status: str | None = Query(default=None),
    profile_version: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    rule_applicability_service: RuleApplicabilityService = Depends(get_rule_applicability_service),
    _: str = Depends(verify_api_key),
) -> RuleApplicabilityListResponse:
    """列出指定规则的适用性画像。"""
    result = await rule_applicability_service.list_profiles(
        rule_id=rule_id,
        review_status=review_status,
        profile_version=profile_version,
        limit=limit,
        offset=skip,
    )
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message or "rule applicability list failed")
    items = [_serialize_applicability_item(item) for item in result.payload.get("items", [])]
    return RuleApplicabilityListResponse(
        count=result.payload.get("count", len(items)),
        total=result.payload.get("total", len(items)),
        skip=result.payload.get("skip", skip),
        limit=result.payload.get("limit", limit),
        items=items,
    )


@router.get("/{rule_id}/applicability-profiles/{profile_id}", response_model=RuleApplicabilityDetailResponse)
async def get_rule_applicability_profile(
    rule_id: str,
    profile_id: UUID,
    rule_applicability_service: RuleApplicabilityService = Depends(get_rule_applicability_service),
    _: str = Depends(verify_api_key),
) -> RuleApplicabilityDetailResponse:
    """读取单条适用性画像。"""
    result = await rule_applicability_service.get_profile(profile_id)
    if result.status == "partial":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message or "profile not found")
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message or "profile load failed")
    item = _serialize_applicability_item(result.payload["profile"])
    if item.rule_id != rule_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则画像未找到")
    return RuleApplicabilityDetailResponse(item=item)


@router.post("/{rule_id}/applicability-profiles/generate", response_model=RuleApplicabilityDetailResponse)
async def generate_rule_applicability_profile(
    rule_id: str,
    request: RuleApplicabilityGenerateRequest,
    rule_applicability_service: RuleApplicabilityService = Depends(get_rule_applicability_service),
    _: str = Depends(verify_api_key),
) -> RuleApplicabilityDetailResponse:
    """从回测结果生成 Rule 适用性画像。"""
    result = await rule_applicability_service.build_profile(
        rule_id=rule_id,
        source_backtest_id=request.source_backtest_id,
        profile_version=request.profile_version,
        min_sample_count=request.min_sample_count,
        review_status=request.review_status,
        reviewed_by=request.reviewed_by,
    )
    if result.status not in {"ok", "partial"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.payload.get("error", {}).get("message") or result.message or "profile generation failed")
    return RuleApplicabilityDetailResponse(item=_serialize_applicability_item(result.payload["profile"]))


@router.post("/{rule_id}/applicability-profiles/{profile_id}/review", response_model=RuleApplicabilityDetailResponse)
async def review_rule_applicability_profile(
    rule_id: str,
    profile_id: UUID,
    request: RuleApplicabilityReviewRequest,
    rule_applicability_service: RuleApplicabilityService = Depends(get_rule_applicability_service),
    _: str = Depends(verify_api_key),
) -> RuleApplicabilityDetailResponse:
    """更新 Rule 适用性画像审核状态。"""
    result = await rule_applicability_service.review_profile(
        profile_id=profile_id,
        review_status=request.review_status,
        reviewed_by=request.reviewed_by,
    )
    if result.status == "partial":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message or "profile not found")
    if result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.payload.get("error", {}).get("message") or result.message or "profile review failed")
    profile_result = await rule_applicability_service.get_profile(profile_id)
    if profile_result.status != "ok":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=profile_result.message or "profile reload failed")
    item = _serialize_applicability_item(profile_result.payload["profile"])
    if item.rule_id != rule_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则画像未找到")
    return RuleApplicabilityDetailResponse(item=item)


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
