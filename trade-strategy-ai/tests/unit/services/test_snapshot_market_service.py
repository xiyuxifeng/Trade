from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class _FakeMarketUniverse:
    trade_date: str
    slot: str


def test_snapshot_service_build_and_query(tmp_path: Path) -> None:
    """SnapshotService 应支持构建与查询快照。"""
    from src.services.snapshot_service import SnapshotService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    calls: list[tuple[str, str]] = []

    async def fake_hot_topics(details, *, config):
        calls.append(("hot_topics", details["trade_date"]))

    async def fake_constituents(details, *, config):
        calls.append(("topic_constituents", details["trade_date"]))

    async def fake_strong(details, *, config):
        calls.append(("strong_symbols", details["trade_date"]))

    class _FakeBackend:
        def __init__(self):
            self.saved = []

        def save(self, market_universe):
            self.saved.append(market_universe)

        def load(self, trade_date: str, slot: str):
            return _FakeMarketUniverse(trade_date=trade_date, slot=slot)

        def list_snapshots(self, trade_date_start: str, trade_date_end: str):
            return [_FakeMarketUniverse(trade_date=trade_date_start, slot="17-30")]

        def delete(self, trade_date: str, slot: str):
            return True

    service = SnapshotService(
        backend=_FakeBackend(),
        hot_topics_handler=fake_hot_topics,
        topic_constituents_handler=fake_constituents,
        strong_symbols_handler=fake_strong,
    )

    result = asyncio.run(
        service.build_snapshot(
            config_path=config_path,
            date="2026-04-23",
            slot="17-30",
            snapshot_type="all",
            force=True,
            offline=True,
        )
    )
    loaded = service.load_snapshot("2026-04-23", "17-30")
    listed = service.list_snapshots("2026-04-20", "2026-04-23")
    deleted = service.delete_snapshot("2026-04-23", "17-30")

    assert result.status == "ok"
    assert result.payload["success_count"] == 3
    assert [item[0] for item in calls] == ["hot_topics", "topic_constituents", "strong_symbols"]
    assert loaded.trade_date == "2026-04-23"
    assert len(listed) == 1
    assert deleted is True


def test_market_service_crawls_and_queries_ohlcv(tmp_path: Path) -> None:
    """MarketService 应支持 OHLCV 抓取和查询。"""
    from src.services.market_service import MarketService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    class _FakeOhlcv:
        def __init__(self):
            self.crawl_calls = []

        async def crawl_bars(self, symbols, start_date=None, end_date=None):
            self.crawl_calls.append((tuple(symbols), start_date, end_date))
            return {"000001.SZ": 2}

        async def get_latest_close(self, symbol: str):
            return 10.5

        async def get_bars(self, symbol: str, start_date: date, end_date: date):
            return [type("Bar", (), {"symbol": symbol, "trade_date": start_date, "close": 10.5})()]

        async def get_bars_as_df(self, symbol: str, start_date: date, end_date: date):
            import pandas as pd

            return pd.DataFrame([{"date": start_date, "close": 10.5}])

    service = MarketService(ohlcv_service=_FakeOhlcv())

    crawl_result = asyncio.run(
        service.crawl_ohlcv(
            config_path=config_path,
            mode="full",
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 28),
        )
    )
    latest = asyncio.run(service.get_latest_close("000001.SZ"))
    bars = asyncio.run(service.get_bars("000001.SZ", date(2026, 4, 1), date(2026, 4, 28)))
    bars_df = asyncio.run(service.get_bars_as_df("000001.SZ", date(2026, 4, 1), date(2026, 4, 28)))

    assert crawl_result.payload["results"]["000001.SZ"] == 2
    assert latest.payload["close"] == 10.5
    assert bars.payload["count"] == 1
    assert bars_df.payload["rows"] == 1
