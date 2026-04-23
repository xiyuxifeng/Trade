from __future__ import annotations

from datetime import date

import pandas as pd

from src.providers.base import ProviderStatus
from src.providers.market_data_provider import MarketDataProvider


class FakeMarketBackend:
    def fetch_ohlcv_1d(
        self,
        *,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        market_kind: str = "stock",
        adjust: str = "",
    ) -> pd.DataFrame:
        del start_date, end_date, market_kind, adjust
        return pd.DataFrame(
            [
                {
                    "date": date(2026, 4, 5),
                    "open": 10.0,
                    "high": 10.5,
                    "low": 9.8,
                    "close": 10.2,
                    "volume": 1000,
                    "turnover": 2000,
                    "symbol": symbol,
                    "market": "CN",
                    "timeframe": "1d",
                    "source": "fake",
                },
                {
                    "date": date(2026, 4, 6),
                    "open": 10.2,
                    "high": 12.6,
                    "low": 10.1,
                    "close": 12.3,
                    "volume": 2000,
                    "turnover": 3000,
                    "symbol": symbol,
                    "market": "CN",
                    "timeframe": "1d",
                    "source": "fake",
                },
            ]
        )


def test_market_data_provider_normalizes_ohlcv_1d_from_backend() -> None:
    provider = MarketDataProvider(backend=FakeMarketBackend())

    result = provider.run(
        "ohlcv_1d",
        request={"symbol": "000001.SZ", "start_date": "2026-04-05", "end_date": "2026-04-06"},
    )

    assert result.status == ProviderStatus.ok
    assert result.payload["dataset"] == "ohlcv_1d"
    assert result.payload["symbol"] == "000001.SZ"
    assert result.payload["timeframe"] == "1d"
    assert result.payload["rows"] == 2
    assert result.payload["bars"][0]["date"] == "2026-04-05"
    assert result.payload["bars"][1]["close"] == 12.3


def test_market_data_provider_requires_symbol() -> None:
    provider = MarketDataProvider(backend=FakeMarketBackend())

    result = provider.run("ohlcv_1d")

    assert result.status == ProviderStatus.error
    assert result.errors == ["symbol is required"]
