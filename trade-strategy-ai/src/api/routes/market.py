from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import verify_api_key
from src.api.schemas import MarketResponse
from src.db.session import get_session_factory as async_session_factory
from src.models.market_data import MarketData

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/latest", response_model=MarketResponse | None)
async def get_latest_market(
    symbol: str = Query(...),
    timeframe: str = Query(default="1d"),
    market: str | None = None,
    _: str = Depends(verify_api_key),
):
    """Get latest market data for a symbol."""
    async with async_session_factory() as session:
        query = (
            select(MarketData)
            .where(MarketData.symbol == symbol)
            .where(MarketData.timeframe == timeframe)
        )
        if market:
            query = query.where(MarketData.market == market)

        query = query.order_by(MarketData.traded_at.desc()).limit(1)

        result = await session.execute(query)
        market_data = result.scalar_one_or_none()

        if market_data is None:
            raise HTTPException(status_code=404, detail="Market data not found")

        return MarketResponse.model_validate(market_data)


@router.get("/export")
async def export_market(
    format: str = Query(default="csv", pattern="^(csv|json|parquet)$"),
    symbol: str | None = None,
    timeframe: str = Query(default="1d"),
    market: str | None = None,
    _: str = Depends(verify_api_key),
):
    """Export market data to CSV/JSON/Parquet."""
    return {"message": f"Export to {format} not yet implemented"}
