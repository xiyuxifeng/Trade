from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
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
    async with async_session_factory() as session:
        query = select(MarketData)
        count_query = select(func.count(MarketData.id))

        if symbol:
            query = query.where(MarketData.symbol == symbol)
            count_query = count_query.where(MarketData.symbol == symbol)
        query = query.where(MarketData.timeframe == timeframe)
        count_query = count_query.where(MarketData.timeframe == timeframe)
        if market:
            query = query.where(MarketData.market == market)
            count_query = count_query.where(MarketData.market == market)

        query = query.order_by(MarketData.traded_at.desc())

        result = await session.execute(query)
        records = result.scalars().all()

        items = [MarketResponse.model_validate(r).model_dump(mode="json") for r in records]

        df = pd.DataFrame(items)

        buffer = BytesIO()
        filename = f"market_export.{format}"

        if format == "csv":
            df.to_csv(buffer, index=False)
            media_type = "text/csv"
        elif format == "json":
            df.to_json(buffer, orient="records", force_ascii=False, indent=2)
            media_type = "application/json"
        else:  # parquet
            df.to_parquet(buffer, index=False)
            media_type = "application/octet-stream"

        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
