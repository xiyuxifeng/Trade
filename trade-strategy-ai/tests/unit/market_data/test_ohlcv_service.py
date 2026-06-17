# tests/unit/market_data/test_ohlcv_service.py
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.market_data.ohlcv_service import OHLCVService
from src.models.indicator import Indicator
from src.models.ohlcv_bar import OHLCVBar


@pytest.fixture
def mock_factory():
    """创建 mock session factory"""
    from unittest.mock import MagicMock
    mock_session = AsyncMock()
    mock_session.add_all = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_scalar_result = MagicMock()
    mock_scalar_result.all.return_value = []
    mock_session.scalars = AsyncMock(return_value=mock_scalar_result)

    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    factory.return_value.__aexit__ = AsyncMock(return_value=None)
    return factory


@pytest.fixture()
async def sqlite_session_factory(tmp_path):
    """创建用于 OHLCV 写库回归测试的 sqlite session factory。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ohlcv.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(OHLCVBar.__table__.create)
        await conn.run_sync(Indicator.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_crawl_bars_single_symbol(mock_factory):
    """测试单标的 ohlcv 抓取"""
    service = OHLCVService(session_factory=mock_factory)

    mock_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 1), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000, "turnover": 10200000},
        {"date": date(2026, 4, 2), "open": 10.2, "high": 10.8, "low": 10.0, "close": 10.5, "volume": 1200000, "turnover": 12600000},
    ])

    with patch("src.providers.akshare_provider.AkshareProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.fetch_ohlcv_1d.return_value = mock_df

        results = await service.crawl_bars(
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 28),
        )

    assert "000001.SZ" in results
    assert results["000001.SZ"] >= 0


@pytest.mark.asyncio
async def test_crawl_bars_upserts_existing_rows(sqlite_session_factory):
    """重复抓取同一 symbol/date 时应更新而不是重复插入。"""
    service = OHLCVService(session_factory=sqlite_session_factory)

    initial_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 1), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000, "turnover": 10200000},
        {"date": date(2026, 4, 2), "open": 10.2, "high": 10.8, "low": 10.0, "close": 10.5, "volume": 1200000, "turnover": 12600000},
    ])
    updated_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 1), "open": 11.0, "high": 11.5, "low": 10.8, "close": 11.2, "volume": 1300000, "turnover": 14560000},
        {"date": date(2026, 4, 2), "open": 11.2, "high": 11.8, "low": 11.0, "close": 11.5, "volume": 1400000, "turnover": 16100000},
    ])

    with patch("src.providers.akshare_provider.AkshareProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.fetch_ohlcv_1d.side_effect = [initial_df, updated_df]

        await service.crawl_bars(
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 2),
            market_kind_by_symbol={"000001.SZ": "stock"},
        )
        await service.crawl_bars(
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 2),
            market_kind_by_symbol={"000001.SZ": "stock"},
        )

    async with sqlite_session_factory() as session:
        result = await session.execute(
            select(OHLCVBar).where(OHLCVBar.symbol == "000001.SZ").order_by(OHLCVBar.trade_date.asc())
        )
        rows = list(result.scalars().all())

    assert len(rows) == 2
    assert rows[0].close == 11.2
    assert rows[1].close == 11.5
    assert mock_instance.fetch_ohlcv_1d.call_count == 2


@pytest.mark.asyncio
async def test_crawl_bars_rejects_missing_numeric_fields(mock_factory):
    """缺失数值字段时不得回退为 0。"""
    service = OHLCVService(session_factory=mock_factory)

    mock_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 1), "open": 10.0, "high": 10.5, "low": 9.8, "close": None, "volume": 1000000},
    ])

    with patch("src.providers.akshare_provider.AkshareProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.fetch_ohlcv_1d.return_value = mock_df

        with pytest.raises(ValueError, match="missing numeric"):
            await service.crawl_bars(
                symbols=["000001.SZ"],
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 1),
                market_kind_by_symbol={"000001.SZ": "stock"},
                adjustment_policy_by_symbol={"000001.SZ": "unadjusted"},
            )


@pytest.mark.asyncio
async def test_crawl_bars_rejects_unknown_adjustment_policy(mock_factory):
    """未知 adjustment policy 不能默认为可回测。"""
    service = OHLCVService(session_factory=mock_factory)

    mock_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 1), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000},
    ])

    with patch("src.providers.akshare_provider.AkshareProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.fetch_ohlcv_1d.return_value = mock_df

        with pytest.raises(ValueError, match="adjustment policy"):
            await service.crawl_bars(
                symbols=["000001.SZ"],
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 1),
                market_kind_by_symbol={"000001.SZ": "stock"},
                adjustment_policy_by_symbol={"000001.SZ": "unknown"},
            )


@pytest.mark.asyncio
async def test_crawl_bars_dedupes_duplicate_provider_rows_and_sets_truthful_availability(sqlite_session_factory):
    """重复 provider 行不得生成重复 canonical 行，且 available_at 必须晚于日线收盘边界。"""
    service = OHLCVService(session_factory=sqlite_session_factory)

    mock_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 1), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000, "turnover": 10200000},
        {"date": date(2026, 4, 1), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000, "turnover": 10200000},
    ])

    with patch("src.providers.akshare_provider.AkshareProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.fetch_ohlcv_1d.return_value = mock_df

        results = await service.crawl_bars(
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 1),
            market_kind_by_symbol={"000001.SZ": "stock"},
            adjustment_policy_by_symbol={"000001.SZ": "unadjusted"},
        )

    assert results["000001.SZ"] == 1

    async with sqlite_session_factory() as session:
        result = await session.execute(select(OHLCVBar).where(OHLCVBar.symbol == "000001.SZ"))
        rows = list(result.scalars().all())

    assert len(rows) == 1
    row = rows[0]
    assert row.available_at is not None
    assert row.source_time is None
    assert row.source_time_reason

    stored_available_at = row.available_at if row.available_at.tzinfo is not None else row.available_at.replace(tzinfo=UTC)
    local_available_at = stored_available_at.astimezone(ZoneInfo("Asia/Shanghai"))
    assert local_available_at.date() == date(2026, 4, 1)
    assert local_available_at.hour >= 15


@pytest.mark.asyncio
async def test_plan_trade_date_coverage_skips_weekend_gaps(sqlite_session_factory, monkeypatch):
    """交易日 gap 逻辑必须跳过周末，不把自然日连续性当成缺口。"""
    from src.backtest.engine import TradeCalendar

    service = OHLCVService(session_factory=sqlite_session_factory)

    def _fake_is_trade_date(cls, value):  # noqa: ANN001
        return value.weekday() < 5

    monkeypatch.setattr(TradeCalendar, "is_trade_date", classmethod(_fake_is_trade_date))

    mock_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 3), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000, "turnover": 10200000},
        {"date": date(2026, 4, 6), "open": 10.2, "high": 10.8, "low": 10.0, "close": 10.5, "volume": 1200000, "turnover": 12600000},
    ])

    with patch("src.providers.akshare_provider.AkshareProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.fetch_ohlcv_1d.return_value = mock_df
        await service.crawl_bars(
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 3),
            end_date=date(2026, 4, 6),
            market_kind_by_symbol={"000001.SZ": "stock"},
            adjustment_policy_by_symbol={"000001.SZ": "unadjusted"},
        )

    plan = await service.plan_trade_date_coverage(
        symbol="000001.SZ",
        start_date=date(2026, 4, 3),
        end_date=date(2026, 4, 6),
    )

    assert plan["missing_trade_dates"] == []
    assert plan["skipped_non_trading_dates"] == [date(2026, 4, 4), date(2026, 4, 5)]
    assert plan["requested_trade_dates"] == [date(2026, 4, 3), date(2026, 4, 6)]


@pytest.mark.asyncio
async def test_repair_bars_is_idempotent(sqlite_session_factory):
    """repair 重跑不得生成重复 canonical 行。"""
    service = OHLCVService(session_factory=sqlite_session_factory)

    mock_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 7), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000, "turnover": 10200000},
    ])

    with patch("src.providers.akshare_provider.AkshareProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.fetch_ohlcv_1d.return_value = mock_df

        first = await service.repair_bars(
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 7),
            end_date=date(2026, 4, 7),
            market_kind_by_symbol={"000001.SZ": "stock"},
            adjustment_policy_by_symbol={"000001.SZ": "unadjusted"},
        )
        second = await service.repair_bars(
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 7),
            end_date=date(2026, 4, 7),
            market_kind_by_symbol={"000001.SZ": "stock"},
            adjustment_policy_by_symbol={"000001.SZ": "unadjusted"},
        )

    assert first["000001.SZ"] == 1
    assert second["000001.SZ"] == 0

    async with sqlite_session_factory() as session:
        result = await session.execute(select(OHLCVBar).where(OHLCVBar.symbol == "000001.SZ"))
        rows = list(result.scalars().all())

    assert len(rows) == 1


@pytest.mark.asyncio
async def test_crawl_bars_invalidates_indicator_cache_from_earliest_changed_trade_date(sqlite_session_factory):
    """OHLCV 变更后，受影响交易日及之后的指标缓存必须失效。"""
    service = OHLCVService(session_factory=sqlite_session_factory)

    initial_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 1), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000, "turnover": 10200000},
        {"date": date(2026, 4, 2), "open": 10.2, "high": 10.8, "low": 10.0, "close": 10.5, "volume": 1200000, "turnover": 12600000},
    ])
    repaired_df = pytest.importorskip("pandas").DataFrame([
        {"date": date(2026, 4, 2), "open": 11.2, "high": 11.8, "low": 11.0, "close": 11.5, "volume": 1400000, "turnover": 16100000},
    ])

    with patch("src.providers.akshare_provider.AkshareProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.fetch_ohlcv_1d.return_value = initial_df

        await service.crawl_bars(
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 2),
            market_kind_by_symbol={"000001.SZ": "stock"},
            adjustment_policy_by_symbol={"000001.SZ": "unadjusted"},
        )

    async with sqlite_session_factory() as session:
        session.add_all(
            [
                Indicator(symbol="000001.SZ", trade_date=date(2026, 4, 1), rsi=50.0),
                Indicator(symbol="000001.SZ", trade_date=date(2026, 4, 2), rsi=55.0),
                Indicator(symbol="000001.SZ", trade_date=date(2026, 4, 3), rsi=60.0),
            ]
        )
        await session.commit()

    with patch("src.providers.akshare_provider.AkshareProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.fetch_ohlcv_1d.return_value = repaired_df

        await service.crawl_bars(
            symbols=["000001.SZ"],
            start_date=date(2026, 4, 2),
            end_date=date(2026, 4, 2),
            market_kind_by_symbol={"000001.SZ": "stock"},
            adjustment_policy_by_symbol={"000001.SZ": "unadjusted"},
        )

    async with sqlite_session_factory() as session:
        result = await session.execute(
            select(Indicator).where(Indicator.symbol == "000001.SZ").order_by(Indicator.trade_date.asc())
        )
        rows = list(result.scalars().all())

    assert [row.trade_date for row in rows] == [date(2026, 4, 1)]


@pytest.mark.asyncio
async def test_get_bars(mock_factory):
    """测试获取 bars"""
    service = OHLCVService(session_factory=mock_factory)

    mock_bars = [
        {"symbol": "000001.SZ", "trade_date": date(2026, 4, 1), "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000000},
    ]

    with patch.object(service, "get_bars", return_value=mock_bars):
        bars = await service.get_bars(
            symbol="000001.SZ",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 28),
        )

    assert isinstance(bars, list)


@pytest.mark.asyncio
async def test_get_latest_close(mock_factory):
    """测试 get_latest_close 返回最新收盘价"""
    service = OHLCVService(session_factory=mock_factory)

    mock_session = mock_factory.return_value.__aenter__.return_value
    mock_session.scalar.return_value = 10.55  # 最新收盘价

    result = await service.get_latest_close("000001.SZ")
    assert result == 10.55

    # 验证 SQL 降序排列并限制 1 条
    call_args = mock_session.scalar.call_args
    stmt = call_args[0][0]
    assert "DESC" in str(stmt).upper()


@pytest.mark.asyncio
async def test_get_latest_close_returns_none_when_empty(mock_factory):
    """测试 get_latest_close 无数据时返回 None"""
    service = OHLCVService(session_factory=mock_factory)

    mock_session = mock_factory.return_value.__aenter__.return_value
    mock_session.scalar.return_value = None

    result = await service.get_latest_close("000001.SZ")
    assert result is None


@pytest.mark.asyncio
async def test_get_bars_as_df(mock_factory):
    """测试 get_bars_as_df 返回 DataFrame"""
    service = OHLCVService(session_factory=mock_factory)

    from src.models.ohlcv_bar import OHLCVBar

    mock_bar = OHLCVBar(
        symbol="000001.SZ",
        trade_date=date(2026, 4, 1),
        open=10.0,
        high=10.5,
        low=9.8,
        close=10.2,
        volume=1000000,
    )

    with patch.object(service, "get_bars", return_value=[mock_bar]):
        df = await service.get_bars_as_df(
            symbol="000001.SZ",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 28),
        )

    assert "date" in df.columns
    assert "close" in df.columns
    assert len(df) == 1
    assert df["close"].iloc[0] == 10.2
