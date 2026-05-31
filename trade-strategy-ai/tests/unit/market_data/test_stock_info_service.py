from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.market_data import stock_info_service as mod
from src.market_data.stock_info_service import get_stock_info_status, refresh_stock_info
from src.models.stock_info import StockInfo


@pytest.fixture
async def stock_info_session_scope(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stock_info.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: StockInfo.__table__.create(sync_conn, checkfirst=True))

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            yield session

    try:
        yield _session_scope, session_factory, engine
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_stock_info_status_reports_freshness_and_benchmark_coverage(monkeypatch: pytest.MonkeyPatch, stock_info_session_scope):
    session_scope, session_factory, engine = stock_info_session_scope
    monkeypatch.setattr(mod, "session_scope", session_scope)

    now = datetime.now(UTC)
    async with session_factory() as session:
        session.add(
            StockInfo(
                symbol="000001.SZ",
                code="000001",
                market="SZ",
                name="平安银行",
                security_type="stock",
                updated_at=now,
            )
        )
        for item in mod.COMMON_MARKET_INDICES:
            session.add(
                StockInfo(
                    symbol=item["symbol"],
                    code=item["code"],
                    market=item["market"],
                    name=item["name"],
                    security_type="index",
                    updated_at=now,
                )
            )
        await session.commit()

    status = await get_stock_info_status(max_age_days=7)

    assert status["total"] == len(mod.COMMON_MARKET_INDICES) + 1
    assert status["stock_count"] == 1
    assert status["index_count"] == len(mod.COMMON_MARKET_INDICES)
    assert status["benchmark_count"] == len(mod.COMMON_MARKET_INDICES)
    assert status["expected_benchmark_count"] == len(mod.COMMON_MARKET_INDICES)
    assert status["missing_benchmark_symbols"] == []
    assert status["is_fresh"] is True
    assert status["needs_refresh"] is False
    assert status["latest_updated_at"] is not None
    assert "已就绪" in status["message"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_stock_info_status_marks_missing_and_stale_data(monkeypatch: pytest.MonkeyPatch, stock_info_session_scope):
    session_scope, session_factory, engine = stock_info_session_scope
    monkeypatch.setattr(mod, "session_scope", session_scope)

    stale_time = datetime.now(UTC) - timedelta(days=30)
    async with session_factory() as session:
        session.add(
            StockInfo(
                symbol="000001.SZ",
                code="000001",
                market="SZ",
                name="平安银行",
                security_type="stock",
                updated_at=stale_time,
            )
        )
        await session.commit()

    status = await get_stock_info_status(max_age_days=7)

    assert status["total"] == 1
    assert status["stock_count"] == 1
    assert status["index_count"] == 0
    assert status["benchmark_count"] == 0
    assert status["missing_benchmark_symbols"]
    assert status["is_fresh"] is False
    assert status["needs_refresh"] is True
    assert "刷新" in status["message"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_stock_info_combines_seed_and_refresh(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    async def fake_seed_common_market_indices():
        calls.append("seed")
        return {"total": 10, "inserted": 10, "updated": 0, "skipped": 0}

    async def fake_fetch_and_store_stock_list():
        calls.append("refresh")
        return {"total": 1_000, "inserted": 1, "updated": 999, "skipped": 0}

    async def fake_get_stock_info_status(*, max_age_days: int = 7):
        calls.append(f"status:{max_age_days}")
        return {
            "total": 1_010,
            "stock_count": 1_000,
            "index_count": 10,
            "benchmark_count": 10,
            "expected_benchmark_count": 10,
            "missing_benchmark_symbols": [],
            "latest_updated_at": "2026-05-30T10:00:00+00:00",
            "is_fresh": True,
            "needs_refresh": False,
            "message": "stock_info 已就绪，可直接用于 OHLCV 抓取",
            "max_age_days": max_age_days,
        }

    monkeypatch.setattr(mod, "seed_common_market_indices", fake_seed_common_market_indices)
    monkeypatch.setattr(mod, "fetch_and_store_stock_list", fake_fetch_and_store_stock_list)
    monkeypatch.setattr(mod, "get_stock_info_status", fake_get_stock_info_status)

    result = await refresh_stock_info(max_age_days=5)

    assert calls == ["seed", "refresh", "status:5"]
    assert result["stock_stats"]["total"] == 1_000
    assert result["index_stats"]["total"] == 10
    assert result["status"]["max_age_days"] == 5
