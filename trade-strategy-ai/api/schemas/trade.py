from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    external_id: str | None
    account_id: str
    symbol: str
    market: str
    side: str
    position_side: str
    executed_at: datetime
    quantity: Decimal
    price: Decimal
    amount: Decimal
    fee: Decimal
    strategy_tag: str | None
    rationale: str | None


class TradeFilter(BaseModel):
    symbol: str | None = None
    account_id: str | None = None
    side: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_amount: float | None = None
    max_amount: float | None = None
