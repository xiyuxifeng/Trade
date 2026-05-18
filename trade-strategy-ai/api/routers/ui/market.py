from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.dependencies import verify_api_key
from api.schemas.market import (
    MarketBenchmarkOptionListResponse,
    MarketRegimeDetailResponse,
    MarketRegimeListResponse,
    MarketDatasetDetailResponse,
    MarketDatasetListResponse,
    MarketRegimeFeatureDetailResponse,
    MarketRegimeFeatureListResponse,
    MarketSnapshotDetailResponse,
    MarketSnapshotListResponse,
    MarketSnapshotQualityResponse,
    MarketSnapshotSectionListResponse,
    MarketSnapshotSectionResponse,
)
from src.market_data.stock_info_service import COMMON_MARKET_INDICES, list_index_stock_infos
from src.services import MarketRegimeFeatureService, MarketRegimeService, MarketService, MarketSnapshotQueryService


router = APIRouter(prefix="/api/ui/v1/market", tags=["ui-market"])


def get_market_service() -> MarketService:
    """获取 MarketService 实例，便于测试覆盖。"""
    return MarketService()


def get_market_snapshot_query_service() -> MarketSnapshotQueryService:
    """获取 MarketSnapshotQueryService 实例，便于测试覆盖。"""
    return MarketSnapshotQueryService()


def get_market_regime_feature_service() -> MarketRegimeFeatureService:
    """获取 MarketRegimeFeatureService 实例，便于测试覆盖。"""
    return MarketRegimeFeatureService()


def get_market_regime_service() -> MarketRegimeService:
    """获取 MarketRegimeService 实例，便于测试覆盖。"""
    return MarketRegimeService()


def _structured_error(error_type: str, message: str, detail: str | None = None, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """构造统一的结构化错误。"""
    return {
        "type": error_type,
        "message": message,
        "detail": detail,
        "metadata": metadata or {},
    }


def _raise_query_error(result: Any) -> None:
    """把服务层错误映射到 HTTPException。"""
    error = (result.payload or {}).get("error") if hasattr(result, "payload") else None
    if not isinstance(error, dict):
        raise HTTPException(status_code=400, detail=_structured_error("query_failed", result.message or "query failed"))

    error_type = str(error.get("type") or "query_failed")
    message = str(error.get("message") or result.message or "query failed")
    status_code = 400
    if error_type in {"snapshot_not_found", "dataset_not_found", "section_not_found", "quality_report_not_found", "feature_not_found"}:
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


@router.get("/symbols")
async def list_symbols(
    q: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    market_service: MarketService = Depends(get_market_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """列出行情标的。"""
    result = await market_service.list_symbols(q=q, limit=limit)
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "symbol listing failed")
    return result.payload


@router.get("/benchmark-options", response_model=MarketBenchmarkOptionListResponse)
async def list_benchmark_options(
    limit: int = Query(default=50, ge=1, le=200),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """列出可用于 benchmark 的常用指数。"""
    items = await list_index_stock_infos()
    if not items:
        payload = [
            {
                "symbol": item["symbol"],
                "code": item["code"],
                "market": item["market"],
                "name": item["name"],
                "security_type": "index",
            }
            for item in COMMON_MARKET_INDICES[:limit]
        ]
        return {"count": len(payload), "items": payload}
    payload = [
        {
            "symbol": item.symbol,
            "code": item.code,
            "market": item.market,
            "name": item.name,
            "security_type": item.security_type,
        }
        for item in items[:limit]
    ]
    return {"count": len(payload), "items": payload}


@router.get("/ohlcv")
async def get_ohlcv(
    symbol: str = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    market_service: MarketService = Depends(get_market_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """按 symbol 和日期范围返回 K 线数据。"""
    result = await market_service.get_ohlcv(symbol=symbol, start_date=start_date, end_date=end_date)
    if result.status != "ok":
        raise HTTPException(status_code=400, detail=result.message or "ohlcv query failed")
    return result.payload


@router.get("/snapshots", response_model=MarketSnapshotListResponse)
async def list_market_snapshots(
    trade_date: date | None = Query(default=None),
    market: str | None = Query(default=None),
    section: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    quality_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    query_service: MarketSnapshotQueryService = Depends(get_market_snapshot_query_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询 Market Snapshot 列表。"""
    result = await query_service.list_snapshots(
        trade_date=trade_date,
        market=market,
        section=section,
        symbol=symbol,
        topic=topic,
        quality_status=quality_status,
        limit=limit,
        offset=offset,
    )
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/snapshots/{snapshot_id}", response_model=MarketSnapshotDetailResponse)
async def get_market_snapshot(
    snapshot_id: str,
    query_service: MarketSnapshotQueryService = Depends(get_market_snapshot_query_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询单个 Market Snapshot 详情。"""
    result = await query_service.get_snapshot_detail(snapshot_id)
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/snapshots/{snapshot_id}/sections", response_model=MarketSnapshotSectionListResponse)
async def list_market_snapshot_sections(
    snapshot_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    query_service: MarketSnapshotQueryService = Depends(get_market_snapshot_query_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询 snapshot 的 sections。"""
    result = await query_service.list_snapshot_sections(snapshot_id, limit=limit, offset=offset)
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/snapshots/{snapshot_id}/sections/{section}", response_model=MarketSnapshotSectionResponse)
async def get_market_snapshot_section(
    snapshot_id: str,
    section: str,
    symbol: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    query_service: MarketSnapshotQueryService = Depends(get_market_snapshot_query_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询 snapshot 内单个 section 的明细。"""
    result = await query_service.get_snapshot_section(
        snapshot_id,
        section,
        symbol=symbol,
        topic=topic,
        limit=limit,
        offset=offset,
    )
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/datasets", response_model=MarketDatasetListResponse)
async def list_market_datasets(
    trade_date: date | None = Query(default=None),
    market: str | None = Query(default=None),
    dataset_type: str | None = Query(default=None),
    quality_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    query_service: MarketSnapshotQueryService = Depends(get_market_snapshot_query_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询 Market Dataset 列表。"""
    result = await query_service.list_datasets(
        trade_date=trade_date,
        market=market,
        dataset_type=dataset_type,
        quality_status=quality_status,
        limit=limit,
        offset=offset,
    )
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/datasets/{dataset_id}", response_model=MarketDatasetDetailResponse)
async def get_market_dataset(
    dataset_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    query_service: MarketSnapshotQueryService = Depends(get_market_snapshot_query_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询单个 Market Dataset 详情。"""
    result = await query_service.get_dataset_detail(dataset_id, limit=limit, offset=offset)
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/snapshots/{snapshot_id}/quality", response_model=MarketSnapshotQualityResponse)
async def get_market_snapshot_quality(
    snapshot_id: str,
    query_service: MarketSnapshotQueryService = Depends(get_market_snapshot_query_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询单个 Market Snapshot 的质量报告。"""
    result = await query_service.get_quality_report(snapshot_id)
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/regime-features", response_model=MarketRegimeFeatureListResponse)
async def list_market_regime_features(
    response: Response,
    trade_date: date | None = Query(default=None),
    snapshot_id: str | None = Query(default=None),
    market: str | None = Query(default=None),
    feature_version: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    feature_service: MarketRegimeFeatureService = Depends(get_market_regime_feature_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询 market regime features 列表。"""
    result = await feature_service.list_features(
        trade_date=trade_date,
        snapshot_id=snapshot_id,
        market=market,
        feature_version=feature_version,
        limit=limit,
        offset=offset,
    )
    if result.status == "partial":
        if response is not None:
            response.status_code = 206
        return result.payload
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/snapshots/{snapshot_id}/regime-features", response_model=MarketRegimeFeatureDetailResponse)
async def get_market_regime_feature(
    response: Response,
    snapshot_id: str,
    feature_version: str | None = Query(default=None),
    feature_service: MarketRegimeFeatureService = Depends(get_market_regime_feature_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询单个 market regime feature 详情。"""
    result = await feature_service.get_feature_detail(snapshot_id, feature_version=feature_version)
    if result.status == "partial":
        if response is not None:
            response.status_code = 206
        return result.payload
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/regimes", response_model=MarketRegimeListResponse)
async def list_market_regimes(
    response: Response,
    trade_date: date | None = Query(default=None),
    snapshot_id: str | None = Query(default=None),
    market: str | None = Query(default=None),
    regime_version: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    regime_service: MarketRegimeService = Depends(get_market_regime_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询 market regime 列表。"""
    result = await regime_service.list_regimes(
        trade_date=trade_date,
        snapshot_id=snapshot_id,
        market=market,
        regime_version=regime_version,
        limit=limit,
        offset=offset,
    )
    if result.status == "partial":
        if response is not None:
            response.status_code = 206
        return result.payload
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload


@router.get("/snapshots/{snapshot_id}/regime", response_model=MarketRegimeDetailResponse)
async def get_market_regime(
    response: Response,
    snapshot_id: str,
    regime_version: str | None = Query(default=None),
    regime_service: MarketRegimeService = Depends(get_market_regime_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """查询单个 market regime 详情。"""
    result = await regime_service.get_regime_detail(snapshot_id, regime_version=regime_version)
    if result.status == "partial":
        if response is not None:
            response.status_code = 206
        return result.payload
    if result.status != "ok":
        _raise_query_error(result)
    return result.payload
