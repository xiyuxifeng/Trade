"""
Mock OHLCV Data Source — for testing and development.

Produces synthetic K-line data that mimics real market behavior.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from src.persona.pattern_matcher import OHLCV, OHLCVDataSource


class MockOHLCVSource:
    """Generate synthetic OHLCV data for testing."""

    def __init__(
        self,
        *,
        symbol: str = "000001.SZ",
        start_price: float = 10.0,
        days: int = 120,
        volatility: float = 0.02,
        trend: float = 0.0002,
        seed: int | None = None,
    ) -> None:
        self.symbol = symbol
        self.start_price = start_price
        self.days = days
        self.volatility = volatility
        self.trend = trend
        self.seed = seed

    def bars(self, symbol: str | None = None, limit: int | None = None) -> list[OHLCV]:
        """Generate a list of synthetic OHLCV bars."""
        if self.seed is not None:
            random.seed(self.seed)

        sym = symbol or self.symbol
        n = self.days
        if limit is not None:
            n = min(n, limit)

        bars: list[OHLCV] = []
        price = self.start_price
        d = date.today() - timedelta(days=n)

        for i in range(n):
            day = d + timedelta(days=i)
            # skip weekends
            if day.weekday() >= 5:
                continue

            open_ = price * (1 + random.uniform(-self.volatility, self.volatility))
            change = random.normalvariate(self.trend, self.volatility)
            close = open_ * (1 + change)
            high = max(open_, close) * (1 + abs(random.uniform(0, self.volatility * 0.5)))
            low = min(open_, close) * (1 - abs(random.uniform(0, self.volatility * 0.5)))
            volume = random.uniform(1_000_000, 10_000_000)

            bars.append(OHLCV(
                symbol=sym,
                date=day.isoformat(),
                open=round(open_, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=round(volume),
            ))
            price = close

        return bars


def create_double_bottom_bars() -> list[OHLCV]:
    """Create mock bars with a clear double-bottom pattern."""
    bars: list[OHLCV] = []
    d = date.today() - timedelta(days=30)
    sym = "TEST.SZ"
    base = 10.0

    for i in range(30):
        day = d + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        # First leg down
        if i < 10:
            price = base - i * 0.3
        elif i < 13:
            # Recovery
            price = base - 3 + (i - 10) * 0.8
        elif i < 18:
            # Second leg down (roughly same low as first)
            price = base - 3.2 + (i - 13) * 0.1
        else:
            # Breakout
            price = base - 3 + (i - 18) * 0.6

        open_ = price * 0.99
        close = price
        high = price * 1.01
        low = price * 0.98
        bars.append(OHLCV(sym, day.isoformat(), open_, high, low, close, 5_000_000))
    return bars
