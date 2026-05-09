from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import verify_api_key
from src.services.market_service import MarketService


router = APIRouter(prefix="/api/ui/v1/market", tags=["ui-market"])


def get_market_service() -> MarketService:
    """获取 MarketService 实例，便于测试覆盖。"""
    return MarketService()


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

