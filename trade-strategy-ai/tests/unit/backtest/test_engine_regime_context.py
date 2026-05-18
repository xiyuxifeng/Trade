from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from src.backtest.engine import BacktestEngine
from src.backtest.schemas import BacktestRequest


class _RecordingLoader:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def load_market_context(self, *, trade_date, symbols, regime_version=None, benchmark_symbol=None):
        self.calls.append(
            {
                "trade_date": trade_date,
                "symbols": list(symbols),
                "regime_version": regime_version,
                "benchmark_symbol": benchmark_symbol,
            }
        )
        return {
            "trade_date": trade_date.isoformat(),
            "bars_by_symbol": {},
            "indicators_by_symbol": {},
            "market_universe": None,
            "benchmark_symbol": benchmark_symbol,
            "topic_snapshot": None,
            "market_regime": None,
            "market_regime_version": regime_version,
            "source_refs": [],
            "compatibility_fallback": False,
            "listing_dates": {},
        }


class _RecordingStrategyLoader:
    async def load_version_for_date(self, *, trader_id, trade_date):
        return SimpleNamespace(
            version_id=f"{trader_id}:{trade_date.isoformat()}",
            recommendations=[],
            rules_snapshot=[],
        )


@pytest.mark.asyncio()
async def test_process_single_day_forwards_market_regime_version() -> None:
    loader = _RecordingLoader()
    engine = BacktestEngine(loader=loader, strategy_loader=_RecordingStrategyLoader())
    request = BacktestRequest(
        trader_id="trader_a",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
        market_regime_version="market-regime-v1",
    )

    records = await engine._process_single_day(date(2026, 4, 1), request)

    assert loader.calls[0]["regime_version"] == "market-regime-v1"
    assert records[0].status == "skipped"
