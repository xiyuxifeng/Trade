"""Legacy strategy-studio UI API 路由。

这是兼容层：正式入口已经拆分到 `/api/ui/v1/optimize` 和
`/api/ui/v1/rule-pool`，这里继续保留旧组合路由，避免一次性切断旧页面。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select

from api.dependencies import verify_api_key
from src.backtest.schemas import BacktestResult, BacktestSummary, RuleValidationResult
from src.models.trader_strategy_version import TraderStrategyVersion
from src.optimization.config import ActiveTraderFilterConfig
from src.rule_pool.models import RulePool
from src.services.optimize_service import OptimizeService
from src.services.rule_pool_service import RulePoolService
from src.strategy_library.schemas import (
    StrategyAdjustment,
    StrategyRecommendation,
    StrategyVersion,
)
from src.strategy_library.service import StrategyLibraryService

router = APIRouter(prefix="/api/ui/v1/strategy-studio", tags=["ui-strategy-studio"])


class VersionSummaryItem(BaseModel):
    """策略版本摘要。"""

    version_id: str
    trader_id: str
    strategy_date: str
    status: str
    version_type: str
    parent_version_id: str | None = None
    recommendations_count: int
    source_article_ids_count: int
    released_at: str | None = None
    has_rules_snapshot: bool


class StrategyRecommendationPayload(BaseModel):
    """前端友好的策略建议。"""

    symbol: str
    decision: str
    confidence: float
    entry_price: float | None = None
    target_price: float | None = None
    stop_loss_price: float | None = None
    volume: int | None = None
    rationale: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class VersionDetailItem(BaseModel):
    """策略版本详情。"""

    version_id: str
    trader_id: str
    strategy_date: str
    status: str
    version_type: str
    parent_version_id: str | None = None
    recommendations: list[StrategyRecommendationPayload] = Field(default_factory=list)
    source_article_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str | None = None
    released_at: str | None = None
    rules_snapshot: list[dict[str, Any]] = Field(default_factory=list)


class VersionListResponse(BaseModel):
    """策略版本列表响应。"""

    status: str = "success"
    count: int
    total: int
    skip: int
    limit: int
    items: list[VersionSummaryItem]


class VersionDetailResponse(BaseModel):
    """策略版本详情响应。"""

    status: str = "success"
    item: VersionDetailItem


class RuleValidationInput(BaseModel):
    """优化建议输入。"""

    trader_id: str
    strategy_version_id: str
    rule_id: str
    rule_text: str
    programmable: bool
    validation_status: Literal[
        "validated",
        "unsupported_rule",
        "missing_field",
        "missing_snapshot",
        "invalid_rule",
    ]
    hit_count: int = 0
    sample_count: int = 0
    hit_rate: float | None = None
    posterior_return_mean: float | None = None
    posterior_return_median: float | None = None
    notes: list[str] = Field(default_factory=list)
    result_version: str = "1.0"


class BacktestSummaryInput(BaseModel):
    """筛选活跃 trader 所需的回测摘要。"""

    total_days: int = 0
    total_trades: int = 0
    valid_trades: int = 0
    skipped_trades: int = 0
    win_rate: float | None = None
    avg_return_pct: float | None = None


class BacktestResultInput(BaseModel):
    """筛选活跃 trader 所需的回测结果。"""

    trader_id: str
    date_from: date
    date_to: date
    summary: BacktestSummaryInput


class ActiveTraderFilterInput(BaseModel):
    """活跃 trader 筛选配置。"""

    min_win_rate: float = 0.40
    min_trades: int = 10
    bayesian_alpha: float = 10.0
    baseline_win_rate: float = 0.50
    min_rule_hit_rate: float | None = None
    min_score: float = 0.30


class ActiveTraderFilterRequest(BaseModel):
    """活跃 trader 筛选请求。"""

    backtest_results: list[BacktestResultInput] = Field(default_factory=list)
    rule_validations: dict[str, list[RuleValidationInput]] = Field(default_factory=dict)
    config: ActiveTraderFilterInput | None = None


class CandidateRecommendationInput(BaseModel):
    """候选版本建议输入。"""

    symbol: str
    decision: str
    confidence: float
    entry_price: float | None = None
    target_price: float | None = None
    stop_loss_price: float | None = None
    volume: int | None = None
    rationale: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class CandidateAdjustmentInput(BaseModel):
    """候选版本调整输入。"""

    trader_id: str
    rule_id: str
    current_status: str
    suggestion: str
    confidence: float
    basis: str


class CandidateCreateRequest(BaseModel):
    """候选版本创建请求。"""

    parent_version_id: str
    trader_id: str
    strategy_date: date
    adjustments: list[CandidateAdjustmentInput] = Field(default_factory=list)
    recommendations: list[CandidateRecommendationInput] = Field(default_factory=list)
    notes: str | None = None


class CandidateCreateResponse(BaseModel):
    """候选版本创建响应。"""

    status: str = "success"
    item: VersionDetailItem


class RuleSummaryItem(BaseModel):
    """规则池摘要。"""

    rule_id: str
    source_type: str
    rule_type: str
    instrument_focus: str
    mapping_status: str
    review_status: str
    initial_confidence: float
    validated_confidence: float | None = None
    backtest_result: dict[str, Any] | None = None
    backtest_hits: int
    backtest_misses: int
    backtest_samples: int
    mapped: bool
    created_at: str | None = None


class RuleDetailItem(RuleSummaryItem):
    """规则池详情。"""

    id: str | None = None
    source_article_ids: list[str] = Field(default_factory=list)
    extraction_layer: dict[str, Any] = Field(default_factory=dict)
    mapped_by: str | None = None
    mapped_at: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    backtest_triggered_at: str | None = None
    used_in_prediction: bool
    prediction_count: int
    last_used_at: str | None = None
    updated_at: str | None = None


class RulePoolListResponse(BaseModel):
    """规则池列表响应。"""

    status: str = "success"
    count: int
    total: int
    skip: int
    limit: int
    items: list[RuleSummaryItem]


class RulePoolDetailResponse(BaseModel):
    """规则池详情响应。"""

    status: str = "success"
    item: RuleDetailItem


class RulePoolReviewRequest(BaseModel):
    """规则单条审核请求。"""

    decision: Literal["approve", "reject", "pending"]
    force: bool = False
    reviewed_by: str = "web"


class RulePoolBatchReviewRequest(BaseModel):
    """规则批量审核请求。"""

    decision: Literal["approve", "reject", "pending"]
    status: Literal["pending", "approved", "rejected"] = "pending"
    limit: int = 50
    force: bool = False
    reviewed_by: str = "web"


def get_session_scope_factory() -> Callable[[], Any]:
    """获取数据库 session_scope 工厂，便于测试覆盖。"""
    from src.db.session import session_scope

    return session_scope


def get_strategy_library_service() -> StrategyLibraryService:
    """获取策略库服务实例，便于测试覆盖。"""
    return StrategyLibraryService()


def get_optimize_service() -> OptimizeService:
    """获取优化服务实例，便于测试覆盖。"""
    return OptimizeService()


def get_rule_pool_service() -> RulePoolService:
    """获取规则池服务实例，便于测试覆盖。"""
    return RulePoolService()


def _parse_date(date_str: str | None) -> date | None:
    """解析 YYYY-MM-DD 日期。"""
    if date_str is None:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的日期格式: {date_str}，请使用 YYYY-MM-DD 格式",
        ) from exc


def _float_or_none(value: Any) -> float | None:
    """把 Numeric / Decimal 之类的值转成 float。"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _serialize_recommendation(raw: Any) -> StrategyRecommendationPayload:
    """把 recommendation dict 转成前端 payload。"""
    def _pick(name: str, default: Any = None) -> Any:
        if isinstance(raw, dict):
            return raw.get(name, default)
        return getattr(raw, name, default)

    return StrategyRecommendationPayload(
        symbol=_pick("symbol", ""),
        decision=_pick("decision", ""),
        confidence=_float_or_none(_pick("confidence")) or 0.0,
        entry_price=_float_or_none(_pick("entry_price")),
        target_price=_float_or_none(_pick("target_price")),
        stop_loss_price=_float_or_none(_pick("stop_loss_price")),
        volume=_pick("volume"),
        rationale=_pick("rationale"),
        evidence_refs=list(_pick("evidence_refs", []) or []),
    )


def _serialize_version_summary(row: TraderStrategyVersion) -> VersionSummaryItem:
    """序列化策略版本摘要。"""
    payload = row.strategy_payload or {}
    recommendations = payload.get("recommendations", []) or []
    rules_snapshot = payload.get("rules_snapshot", []) or []
    return VersionSummaryItem(
        version_id=row.version_name,
        trader_id=row.trader_id,
        strategy_date=row.strategy_date.isoformat(),
        status=row.status,
        version_type=getattr(row, "version_type", "manual"),
        parent_version_id=getattr(row, "parent_version_id", None),
        recommendations_count=len(recommendations),
        source_article_ids_count=len(row.source_article_ids or []),
        released_at=row.released_at.isoformat() if row.released_at else None,
        has_rules_snapshot=bool(rules_snapshot),
    )


def _serialize_version_detail(row: TraderStrategyVersion) -> VersionDetailItem:
    """序列化策略版本详情。"""
    payload = row.strategy_payload or {}
    recommendations = payload.get("recommendations", []) or []
    rules_snapshot = payload.get("rules_snapshot", []) or []
    return VersionDetailItem(
        version_id=row.version_name,
        trader_id=row.trader_id,
        strategy_date=row.strategy_date.isoformat(),
        status=row.status,
        version_type=getattr(row, "version_type", "manual"),
        parent_version_id=getattr(row, "parent_version_id", None),
        recommendations=[_serialize_recommendation(item) for item in recommendations],
        source_article_ids=list(row.source_article_ids or []),
        evidence_refs=list(row.evidence_refs or []),
        notes=row.notes,
        released_at=row.released_at.isoformat() if row.released_at else None,
        rules_snapshot=list(rules_snapshot),
    )


def _serialize_strategy_version(version: StrategyVersion) -> VersionDetailItem:
    """序列化 StrategyVersion dataclass。"""
    return VersionDetailItem(
        version_id=version.version_id,
        trader_id=version.trader_id,
        strategy_date=version.strategy_date.isoformat(),
        status=version.status.value,
        version_type=version.version_type.value,
        parent_version_id=version.parent_version_id,
        recommendations=[_serialize_recommendation(item) for item in version.recommendations],
        source_article_ids=list(version.source_article_ids or []),
        evidence_refs=list(version.evidence_refs or []),
        notes=version.notes,
        released_at=version.released_at.isoformat() if version.released_at else None,
        rules_snapshot=list(version.rules_snapshot or []),
    )


def _has_mapped_condition(row: RulePool) -> bool:
    """判断规则是否已经完成映射。"""
    extraction_layer = row.extraction_layer or {}
    return bool(extraction_layer.get("mapped_condition"))


def _serialize_rule_summary(row: RulePool) -> RuleSummaryItem:
    """序列化规则池摘要。"""
    confidence = row.validated_confidence if row.validated_confidence is not None else row.initial_confidence
    return RuleSummaryItem(
        rule_id=row.rule_id,
        source_type=row.source_type,
        rule_type=row.rule_type,
        instrument_focus=row.instrument_focus,
        mapping_status=row.mapping_status,
        review_status=row.review_status,
        initial_confidence=_float_or_none(row.initial_confidence) or 0.0,
        validated_confidence=_float_or_none(row.validated_confidence),
        backtest_result=row.backtest_result,
        backtest_hits=row.backtest_hits,
        backtest_misses=row.backtest_misses,
        backtest_samples=row.backtest_samples,
        mapped=_has_mapped_condition(row),
        created_at=row.created_at.isoformat() if getattr(row, "created_at", None) else None,
    )


def _serialize_rule_detail(row: RulePool) -> RuleDetailItem:
    """序列化规则池详情。"""
    summary = _serialize_rule_summary(row)
    return RuleDetailItem(
        **summary.model_dump(),
        id=str(row.id) if row.id else None,
        source_article_ids=list(row.source_article_ids or []),
        extraction_layer=row.extraction_layer or {},
        mapped_by=row.mapped_by,
        mapped_at=row.mapped_at.isoformat() if row.mapped_at else None,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at.isoformat() if row.reviewed_at else None,
        backtest_triggered_at=row.backtest_triggered_at.isoformat() if row.backtest_triggered_at else None,
        used_in_prediction=row.used_in_prediction,
        prediction_count=row.prediction_count,
        last_used_at=row.last_used_at.isoformat() if row.last_used_at else None,
        updated_at=row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    )


def _to_backtest_result(item: BacktestResultInput) -> BacktestResult:
    """把 UI 请求转换成 BacktestResult。"""
    summary = BacktestSummary(
        total_days=item.summary.total_days,
        total_trades=item.summary.total_trades,
        valid_trades=item.summary.valid_trades,
        skipped_trades=item.summary.skipped_trades,
        win_rate=item.summary.win_rate,
        avg_return_pct=item.summary.avg_return_pct,
    )
    return BacktestResult(
        request_trader_id=item.trader_id,
        request_date_from=item.date_from,
        request_date_to=item.date_to,
        summary=summary,
        records=[],
    )


def _to_rule_validation(item: RuleValidationInput) -> RuleValidationResult:
    """把 UI 请求转换成 RuleValidationResult。"""
    return RuleValidationResult(
        trader_id=item.trader_id,
        strategy_version_id=item.strategy_version_id,
        rule_id=item.rule_id,
        rule_text=item.rule_text,
        programmable=item.programmable,
        validation_status=item.validation_status,
        hit_count=item.hit_count,
        sample_count=item.sample_count,
        hit_rate=item.hit_rate,
        posterior_return_mean=item.posterior_return_mean,
        posterior_return_median=item.posterior_return_median,
        notes=item.notes,
        result_version=item.result_version,
    )


def _to_strategy_adjustment(item: CandidateAdjustmentInput) -> StrategyAdjustment:
    """把 UI 调整建议转换成 StrategyAdjustment。"""
    return StrategyAdjustment(
        trader_id=item.trader_id,
        rule_id=item.rule_id,
        current_status=item.current_status,
        suggestion=item.suggestion,
        confidence=item.confidence,
        依据=item.basis,
    )


def _to_strategy_recommendation(item: CandidateRecommendationInput) -> StrategyRecommendation:
    """把 UI 推荐项转换成 StrategyRecommendation。"""
    return StrategyRecommendation(
        symbol=item.symbol,
        decision=item.decision,
        confidence=item.confidence,
        entry_price=item.entry_price,
        target_price=item.target_price,
        stop_loss_price=item.stop_loss_price,
        volume=item.volume,
        rationale=item.rationale,
        evidence_refs=item.evidence_refs,
    )


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
    """列出策略版本。"""
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
    """读取单个策略版本详情。"""
    async with session_scope_factory() as session:
        stmt = select(TraderStrategyVersion).where(TraderStrategyVersion.version_name == version_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="策略版本未找到")

    return VersionDetailResponse(item=_serialize_version_detail(row))


@router.post("/optimize/advise-rule-validations")
async def advise_rule_validations(
    request: list[RuleValidationInput],
    optimize_service: OptimizeService = Depends(get_optimize_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """基于规则验真结果生成优化建议。"""
    result = optimize_service.advise_rule_validations([_to_rule_validation(item) for item in request])
    return result.payload


@router.post("/optimize/filter-active-traders")
async def filter_active_traders(
    request: ActiveTraderFilterRequest,
    optimize_service: OptimizeService = Depends(get_optimize_service),
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


@router.post("/optimize/create-candidate", response_model=CandidateCreateResponse)
async def create_candidate(
    request: CandidateCreateRequest,
    strategy_service: StrategyLibraryService = Depends(get_strategy_library_service),
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


@router.get("/rule-pool", response_model=RulePoolListResponse)
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


@router.get("/rule-pool/{rule_id}", response_model=RulePoolDetailResponse)
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


@router.post("/rule-pool/{rule_id}/review")
async def review_rule(
    rule_id: str,
    request: RulePoolReviewRequest,
    rule_pool_service: RulePoolService = Depends(get_rule_pool_service),
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


@router.post("/rule-pool/review-batch")
async def review_batch(
    request: RulePoolBatchReviewRequest,
    rule_pool_service: RulePoolService = Depends(get_rule_pool_service),
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
