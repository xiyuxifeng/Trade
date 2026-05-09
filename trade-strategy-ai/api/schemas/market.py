from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class MarketResponse(BaseModel):
    id: UUID
    symbol: str
    market: str
    timeframe: str
    traded_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    turnover: Decimal
    source: str

    class Config:
        from_attributes = True


class MarketFilter(BaseModel):
    symbol: str
    timeframe: str = "1d"
    market: str | None = None
