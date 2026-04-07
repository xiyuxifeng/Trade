from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import verify_api_key
from src.api.schemas import TradeResponse
from src.db.session import get_session_factory as async_session_factory
from src.models.trade_log import TradeLog

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=dict[str, Any])
async def list_trades(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    symbol: str | None = None,
    account_id: str | None = None,
    side: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    _: str = Depends(verify_api_key),
):
    """List trades with pagination and filters."""
    offset = (page - 1) * page_size

    async with async_session_factory() as session:
        query = select(TradeLog)
        count_query = select(func.count(TradeLog.id))

        if symbol:
            query = query.where(TradeLog.symbol == symbol)
            count_query = count_query.where(TradeLog.symbol == symbol)
        if account_id:
            query = query.where(TradeLog.account_id == account_id)
            count_query = count_query.where(TradeLog.account_id == account_id)
        if side:
            query = query.where(TradeLog.side == side)
            count_query = count_query.where(TradeLog.side == side)
        if start_date:
            query = query.where(TradeLog.executed_at >= start_date)
            count_query = count_query.where(TradeLog.executed_at >= start_date)
        if end_date:
            query = query.where(TradeLog.executed_at <= end_date)
            count_query = count_query.where(TradeLog.executed_at <= end_date)
        if min_amount is not None:
            query = query.where(TradeLog.amount >= min_amount)
            count_query = count_query.where(TradeLog.amount >= min_amount)
        if max_amount is not None:
            query = query.where(TradeLog.amount <= max_amount)
            count_query = count_query.where(TradeLog.amount <= max_amount)

        query = query.order_by(TradeLog.executed_at.desc()).offset(offset).limit(page_size)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        result = await session.execute(query)
        trades = result.scalars().all()

        items = [TradeResponse.model_validate(t).model_dump(mode="json") for t in trades]

        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }


@router.get("/export")
async def export_trades(
    format: str = Query(default="csv", pattern="^(csv|json|parquet)$"),
    symbol: str | None = None,
    account_id: str | None = None,
    side: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    _: str = Depends(verify_api_key),
):
    """Export trades to CSV/JSON/Parquet."""
    return {"message": f"Export to {format} not yet implemented"}