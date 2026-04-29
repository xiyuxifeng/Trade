# tests/integration/test_backtest_with_ohlcv.py
import pytest
from datetime import date
from src.backtest.engine import BacktestEngine
from src.backtest.schemas import BacktestRequest


def test_backtest_runs_with_real_data():
    """集成测试：回测使用真实数据"""
    engine = BacktestEngine()

    request = BacktestRequest(
        trader_id="trader_a",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 10),
    )

    result = engine.run_sync(request)

    # 如果有数据，应该有非 skipped 记录
    traded = [r for r in result.records if r.status == "traded"]
    skipped = [r for r in result.records if r.status == "skipped"]

    print(f"Total: {len(result.records)}, Traded: {len(traded)}, Skipped: {len(skipped)}")

    # 至少应该有尝试加载数据
    assert len(result.records) > 0
