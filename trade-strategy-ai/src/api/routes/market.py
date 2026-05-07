from __future__ import annotations

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
from src.models.ohlcv_bar import OHLCVBar

router = APIRouter(prefix="/market", tags=["market"])


def _bar_to_response(bar: OHLCVBar) -> dict[str, Any]:
    """将 OHLCVBar 转为 API 兼容的 dict。"""
    return {
        "symbol": bar.symbol,
        "traded_at": bar.trade_date.isoformat(),
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": float(bar.volume),
        "turnover": bar.turnover,
    }


@router.get("/latest", response_model=MarketResponse | None)
async def get_latest_market(
    symbol: str = Query(...),
    _: str = Depends(verify_api_key),
):
    """Get latest market data for a symbol from ohlcv_bars."""
    async with async_session_factory() as session:
        query = (
            select(OHLCVBar)
            .where(OHLCVBar.symbol == symbol)
            .order_by(OHLCVBar.trade_date.desc())
            .limit(1)
        )
        result = await session.execute(query)
        bar = result.scalar_one_or_none()

        if bar is None:
            raise HTTPException(status_code=404, detail="Market data not found")

        return MarketResponse.model_validate(_bar_to_response(bar))


@router.get("/export")
async def export_market(
    format: str = Query(default="csv", pattern="^(csv|json|parquet)$"),
    symbol: str | None = None,
    _: str = Depends(verify_api_key),
):
    """Export OHLCV data to CSV/JSON/Parquet from ohlcv_bars."""
    async with async_session_factory() as session:
        query = select(OHLCVBar)
        count_query = select(func.count(OHLCVBar.id))

        if symbol:
            query = query.where(OHLCVBar.symbol == symbol)
            count_query = count_query.where(OHLCVBar.symbol == symbol)

        query = query.order_by(OHLCVBar.trade_date.desc())

        result = await session.execute(query)
        records = result.scalars().all()

        items = [_bar_to_response(r) for r in records]

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
