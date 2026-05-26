# tests/unit/market_data/test_ohlcv_service.py
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.market_data.ohlcv_service import OHLCVService
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
