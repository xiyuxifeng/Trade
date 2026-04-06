from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from src.market_data.service import MarketDataCache, MarketDataSyncService


class _FakeAkshareTool:
    def fetch_stock_daily_a(self, req):
        del req
        return pd.DataFrame(
            [
                {"date": date(2026, 4, 5), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000},
                {"date": date(2026, 4, 6), "open": 10.2, "high": 12.6, "low": 10.1, "close": 12.3, "volume": 2000},
            ]
        )

    def fetch_etf_daily_em(self, req):
        del req
        return self.fetch_stock_daily_a(req)

    def fetch_index_daily_em(self, req):
        del req
        return pd.DataFrame(
            [
                {"date": date(2026, 4, 5), "open": 3000.0, "high": 3050.0, "low": 2990.0, "close": 3040.0, "volume": 10},
                {"date": date(2026, 4, 6), "open": 3040.0, "high": 3090.0, "low": 3030.0, "close": 3080.0, "volume": 11},
            ]
        )

    def fetch_board_industry_hist_em(self, req):
        del req
        return pd.DataFrame(
            [
                {"date": date(2026, 4, 5), "open": 1000.0, "high": 1010.0, "low": 995.0, "close": 1005.0, "volume": 20},
                {"date": date(2026, 4, 6), "open": 1005.0, "high": 1020.0, "low": 1000.0, "close": 1018.0, "volume": 25},
            ]
        )


def test_market_data_sync_service_writes_cache_and_latest_close(tmp_path: Path) -> None:
    service = MarketDataSyncService(cache_dir=tmp_path / "market", tool=_FakeAkshareTool())

    result = service.sync_symbol("000001.SZ")

    assert result.symbol == "000001.SZ"
    assert result.rows_written == 2
    assert result.latest_close == 12.3
    assert result.cache_path.exists()
    cached = MarketDataCache(tmp_path / "market").load_daily_frame("000001.SZ")
    assert list(cached["close"]) == [10.2, 12.3]
    assert list(cached["date"].astype(str)) == ["2026-04-05", "2026-04-06"]


def test_market_data_cache_latest_close_reads_written_csv(tmp_path: Path) -> None:
    cache = MarketDataCache(tmp_path / "market")
    df = pd.DataFrame(
        [
            {"date": date(2026, 4, 5), "close": 10.2},
            {"date": date(2026, 4, 6), "close": 12.3},
        ]
    )
    cache.write_daily_frame(symbol="000001.SZ", df=df, source="akshare")

    assert cache.latest_close("000001.SZ") == 12.3


def test_market_data_sync_service_writes_index_cache(tmp_path: Path) -> None:
    service = MarketDataSyncService(cache_dir=tmp_path / "market", tool=_FakeAkshareTool())

    result = service.sync_index("sz399001")

    assert result.symbol == "sz399001"
    assert result.rows_written == 2
    assert result.latest_close == 3080.0
    assert result.cache_path.exists()


def test_market_data_sync_service_writes_sector_cache(tmp_path: Path) -> None:
    service = MarketDataSyncService(cache_dir=tmp_path / "market", tool=_FakeAkshareTool())

    result = service.sync_industry_board("半导体")

    assert result.symbol == "industry:半导体"
    assert result.rows_written == 2
    assert result.latest_close == 1018.0
    assert result.cache_path.exists()
