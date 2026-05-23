from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest


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

    assert result.status in {"ok", "partial"}
    assert len(result.payload["results"]) == 3
    assert [item[0] for item in calls] == ["hot_topics", "topic_constituents", "strong_symbols"]
    assert loaded.trade_date == "2026-04-23"
    assert len(listed) == 1
    assert deleted is True


def test_market_service_crawls_and_queries_ohlcv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """MarketService 应支持 OHLCV 抓取和查询。"""
    from src.services.market_service import MarketService
    from src.services.config_profile_service import ConfigProfileService

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

    async def _fake_resolve_profile_config_path(self, profile_id: str):
        del self, profile_id
        return config_path

    monkeypatch.setattr(ConfigProfileService, "resolve_profile_config_path", _fake_resolve_profile_config_path)
    service = MarketService(ohlcv_service=_FakeOhlcv())

    crawl_result = asyncio.run(
        service.crawl_ohlcv(
            profile_id="default",
            mode="full",
            symbols=["000001.SZ", "000300.SH"],
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 28),
            limit=None,
        )
    )
    latest = asyncio.run(service.get_latest_close("000001.SZ"))
    bars = asyncio.run(service.get_bars("000001.SZ", date(2026, 4, 1), date(2026, 4, 28)))
    bars_df = asyncio.run(service.get_bars_as_df("000001.SZ", date(2026, 4, 1), date(2026, 4, 28)))

    assert crawl_result.payload["results"]["000001.SZ"] == 2
    assert crawl_result.payload["profile_id"] == "default"
    assert latest.payload["close"] == 10.5
    assert bars.payload["count"] == 1
    assert bars_df.payload["rows"] == 1
    assert service._ohlcv_service.crawl_calls[0][0] == ("000001.SZ", "000300.SH")


def test_market_service_incremental_crawl_keeps_the_requested_date_range(tmp_path: Path) -> None:
    """增量抓取应把调用方传入的起止日期原样传给底层服务。"""
    from src.services.market_service import MarketService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    class _FakeOhlcv:
        def __init__(self) -> None:
            self.crawl_calls: list[tuple[tuple[str, ...], date | None, date | None]] = []

        async def crawl_bars(self, symbols, start_date=None, end_date=None):
            self.crawl_calls.append((tuple(symbols), start_date, end_date))
            return {"000001.SZ": 2}

        async def get_latest_close(self, symbol: str):
            return 10.5

    fake_ohlcv = _FakeOhlcv()
    service = MarketService(ohlcv_service=fake_ohlcv)

    result = asyncio.run(
        service.crawl_ohlcv(
            config_path=config_path,
            mode="incremental",
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 28),
        )
    )

    assert result.status == "ok"
    assert fake_ohlcv.crawl_calls == [
        (("000001.SZ",), date(2026, 4, 1), date(2026, 4, 28))
    ]


def test_market_service_lists_symbols_and_ohlcv_from_session(tmp_path: Path) -> None:
    """MarketService 应支持行情标的和 K 线查询。"""
    from src.services.market_service import MarketService

    class _FakeRow:
        def __init__(self, symbol: str):
            self.symbol = symbol

    class _FakeBar:
        def __init__(self, symbol: str, trade_date: date):
            self.symbol = symbol
            self.trade_date = trade_date
            self.open = 1.0
            self.high = 1.2
            self.low = 0.9
            self.close = 1.1
            self.volume = 1000
            self.turnover = None

    class _FakeResult:
        def __init__(self, *, rows=None, bars=None):
            self._rows = rows or []
            self._bars = bars or []

        def all(self):
            return self._bars if self._bars else self._rows

        def scalars(self):
            return self

        def first(self):
            return self._bars[0] if self._bars else None

        def scalar(self):
            return self._bars[0] if self._bars else None

        def scalar_one_or_none(self):
            return self._bars[0] if self._bars else None

    class _FakeSession:
        def __init__(self):
            self.calls = []

        async def execute(self, stmt):
            sql = str(stmt)
            self.calls.append(sql)
            if "DISTINCT" in sql:
                return _FakeResult(rows=[("000001.SZ",), ("600000.SH",)])
            return _FakeResult(bars=[_FakeBar("000001.SZ", date(2026, 4, 1)), _FakeBar("000001.SZ", date(2026, 4, 2))])

    fake_session = _FakeSession()

    class _FakeSessionFactory:
        @asynccontextmanager
        async def begin(self):
            yield fake_session

        def __call__(self):
            return self

    service = MarketService(session_factory=_FakeSessionFactory())

    symbols = asyncio.run(service.list_symbols())
    ohlcv = asyncio.run(service.get_ohlcv("000001.SZ", date(2026, 4, 1), date(2026, 4, 30)))

    assert symbols.payload["items"] == ["000001.SZ", "600000.SH"]
    assert ohlcv.payload["count"] == 2
    assert ohlcv.payload["items"][0]["time"] == "2026-04-01"


def test_market_service_rejects_invalid_mode_and_missing_symbols(tmp_path: Path) -> None:
    """MarketService 应拒绝非法模式和缺失 symbols 的调用。"""
    from src.services.market_service import MarketService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    class _FakeOhlcv:
        async def crawl_bars(self, symbols, start_date=None, end_date=None):
            return {"000001.SZ": 2}

    service = MarketService(ohlcv_service=_FakeOhlcv())

    with pytest.raises(ValueError, match="mode must be full or incremental"):
        asyncio.run(
            service.crawl_ohlcv(
                config_path=config_path,
                mode="unsupported",
                symbols=["000001.SZ"],
            )
        )

    with pytest.raises(ValueError, match="symbols must be provided"):
        asyncio.run(
            service.crawl_ohlcv(
                config_path=config_path,
                mode="full",
                symbols=None,
            )
        )


def test_market_service_ohlcv_scheduler_status_and_toggle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """MarketService 应支持 OHLCV 调度器状态、启动与停止。"""
    from src.services import market_service as market_service_module
    from src.services.market_service import MarketService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    class _FakeOhlcv:
        def __init__(self) -> None:
            self.crawl_calls: list[tuple[tuple[str, ...], date | None, date | None, dict[str, str] | None]] = []

        async def crawl_bars(self, symbols, start_date=None, end_date=None, market_kind_by_symbol=None):
            self.crawl_calls.append((tuple(symbols), start_date, end_date, market_kind_by_symbol))
            return {"000001.SZ": 2, "000300.SH": 1}

    class _FakeExecResult:
        def __init__(self, rows=None):
            self._rows = rows or []

        def all(self):
            return self._rows

    class _FakeSession:
        async def scalar(self, stmt):
            text = str(stmt).lower()
            if "max(" in text:
                return date(2026, 4, 30)
            if "count(" in text:
                return 12
            return None

        async def execute(self, stmt):
            text = str(stmt).lower()
            if "stock_info" in text:
                return _FakeExecResult([("000001.SZ", "stock"), ("000300.SH", "index")])
            return _FakeExecResult([])

    class _FakeSessionFactory:
        @asynccontextmanager
        async def begin(self):
            yield _FakeSession()

        def __call__(self):
            return self

    class _FakeScheduler:
        def __init__(self) -> None:
            self.jobs: list[dict[str, object]] = []
            self.running = False
            self._thread = SimpleNamespace(join=lambda: None)

        def add_job(self, func, trigger, args=None, id=None, replace_existing=False):
            self.jobs.append({
                "func": func,
                "trigger": trigger,
                "args": tuple(args or []),
                "id": id,
                "replace_existing": replace_existing,
            })

        def start(self):
            self.running = True

        def shutdown(self, wait=False):
            self.running = False

    MarketService._clear_scheduler()
    monkeypatch.setattr(market_service_module, "BackgroundScheduler", _FakeScheduler)
    fake_ohlcv = _FakeOhlcv()
    service = MarketService(ohlcv_service=fake_ohlcv, session_factory=_FakeSessionFactory())

    try:
        status = asyncio.run(service.ohlcv_scheduler_status(config_path=config_path))
        assert status.status == "ok"
        assert status.payload["latest_trade_date"] == "2026-04-30"
        assert status.payload["latest_record_count"] == 12

        started = service.run_ohlcv_scheduler(config_path=config_path, start_scheduler=True, block=False)
        assert started.status == "ok"
        assert started.payload["scheduler_started"] is True
        assert started.payload["pre_market"] == "9:25"
        assert started.payload["post_close"] == "17:30"
        assert MarketService._scheduler is not None
        assert MarketService._scheduler.running is True
        assert len(MarketService._scheduler.jobs) == 2
        MarketService._scheduler.jobs[0]["func"]()
        assert fake_ohlcv.crawl_calls[0][0] == ("000001.SZ", "000300.SH")
        assert fake_ohlcv.crawl_calls[0][1] == date.today()
        assert fake_ohlcv.crawl_calls[0][2] == date.today()
        assert fake_ohlcv.crawl_calls[0][3] == {"000001.SZ": "stock", "000300.SH": "index"}

        stopped = service.stop_ohlcv_scheduler(config_path=config_path)
        assert stopped.status == "ok"
        assert stopped.payload["started"] is False
        assert MarketService._scheduler is None
    finally:
        MarketService._clear_scheduler()


def test_snapshot_service_reports_partial_failure(tmp_path: Path) -> None:
    """快照构建中部分处理器失败时应返回 partial 并保留错误信息。"""
    from src.services.snapshot_service import SnapshotService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    async def fake_hot_topics(details, *, config):
        return None

    async def fake_constituents(details, *, config):
        raise RuntimeError("constituents failed")

    async def fake_strong(details, *, config):
        return None

    service = SnapshotService(
        hot_topics_handler=fake_hot_topics,
        topic_constituents_handler=fake_constituents,
        strong_symbols_handler=fake_strong,
    )

    result = asyncio.run(
        service.build_snapshot(
            config_path=config_path,
            date="2026-04-23",
            snapshot_type="all",
        )
    )

    assert result.status == "partial"
    assert result.payload["failure_count"] == 1
    assert result.payload["success_count"] == 2
    assert result.warnings == ["constituents failed"]
    assert any(item["status"] == "error" for item in result.payload["results"])


def test_snapshot_service_build_market_snapshot_uses_profile_default_benchmark(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Market Snapshot 构建应优先使用 Profile 的 benchmark 默认值。"""
    from src.services import snapshot_service as snapshot_service_module
    from src.services.base import ServiceResult
    from src.services.snapshot_service import SnapshotService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "timezone: Asia/Shanghai\nmarket_state_benchmark_symbol: 510300.SH\ntraders: []\n",
        encoding="utf-8",
    )

    calls: dict[str, object] = {}

    class _FakeMarketSnapshotService:
        def __init__(self, storage_service=None):
            self.storage_service = storage_service

        async def build_market_snapshot(self, **kwargs):
            calls.update(kwargs)
            return ServiceResult(status="ok", message="market snapshot built", payload={"snapshot_path": "snapshot.json"})

    class _FakeProfile:
        def __init__(self, profile_id: str, benchmark_symbol: str | None):
            self.profile_id = profile_id
            self.sections = {"market_state_benchmark_symbol": benchmark_symbol} if benchmark_symbol else {}

    class _FakeProfileService:
        async def get_profile(self, profile_id: str):
            if profile_id == "default":
                return _FakeProfile(profile_id="default", benchmark_symbol="000300.SH")
            if profile_id == "missing":
                return _FakeProfile(profile_id="missing", benchmark_symbol=None)
            return None

    monkeypatch.setattr(snapshot_service_module, "MarketSnapshotService", _FakeMarketSnapshotService)
    monkeypatch.setattr(snapshot_service_module, "ConfigProfileService", lambda: _FakeProfileService())

    service = SnapshotService()
    result = asyncio.run(
        service.build_market_snapshot(
            config_path=config_path,
            trade_date="2026-05-16",
            profile_id="default",
        )
    )

    assert result.status == "ok"
    assert calls["benchmark_symbol"] == "000300.SH"
    assert calls["profile_id"] == "default"
    assert calls["trade_date"] == "2026-05-16"


def test_snapshot_service_build_market_snapshot_requires_profile_benchmark(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """当 Web 只传 profile_id 时，Profile 没有 benchmark 默认值应明确报错。"""
    from src.services import snapshot_service as snapshot_service_module
    from src.services.snapshot_service import SnapshotService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "timezone: Asia/Shanghai\nmarket_state_benchmark_symbol: 510300.SH\ntraders: []\n",
        encoding="utf-8",
    )

    class _FakeProfile:
        def __init__(self):
            self.sections = {}

    class _FakeProfileService:
        async def get_profile(self, profile_id: str):
            if profile_id == "missing":
                return _FakeProfile()
            return None

    monkeypatch.setattr(snapshot_service_module, "ConfigProfileService", lambda: _FakeProfileService())

    service = SnapshotService()

    with pytest.raises(ValueError, match="benchmark_symbol is required"):
        asyncio.run(
            service.build_market_snapshot(
                config_path=config_path,
                trade_date="2026-05-16",
                profile_id="missing",
            )
        )
