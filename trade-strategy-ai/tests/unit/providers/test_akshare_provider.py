from __future__ import annotations

from datetime import date

import pandas as pd

from src.providers.akshare_provider import AkshareProvider
from src.providers.base import ProviderStatus


class FakeAkshareTool:
    def fetch_stock_daily_a(self, req):
        self.last_request = req
        return pd.DataFrame(
            [
                {"date": date(2026, 4, 5), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000},
                {"date": date(2026, 4, 6), "open": 10.2, "high": 12.6, "low": 10.1, "close": 12.3, "volume": 2000},
            ]
        )


def test_akshare_provider_normalizes_stock_ohlcv_1d() -> None:
    provider = AkshareProvider(tool=FakeAkshareTool())

    result = provider.run(
        "ohlcv_1d",
        request={"symbol": "000001.SZ", "start_date": "2026-04-05", "end_date": "2026-04-06"},
    )

    assert result.status == ProviderStatus.ok
    assert result.payload["dataset"] == "ohlcv_1d"
    assert result.payload["symbol"] == "000001.SZ"
    assert result.payload["rows"] == 2
    assert result.payload["bars"][0]["date"] == "2026-04-05"
    assert result.payload["bars"][1]["close"] == 12.3


def test_akshare_provider_exposes_raw_daily_frame() -> None:
    provider = AkshareProvider(tool=FakeAkshareTool())

    frame = provider.fetch_ohlcv_1d(symbol="000001.SZ")

    assert list(frame["close"]) == [10.2, 12.3]
