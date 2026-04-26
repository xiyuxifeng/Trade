"""NTL-S6-013: 回测复现验证测试"""

from __future__ import annotations

from datetime import date

from src.backtest.engine import BacktestEngine
from src.backtest.reproducibility import fingerprint_result
from src.backtest.schemas import BacktestRequest


def test_fingerprint_same_request_idempotent():
    """相同请求的两次运行应产生相同 fingerprint"""
    engine = BacktestEngine()
    req = BacktestRequest(
        trader_id="trader_a",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
    )
    result_a = engine.run_sync(req)
    result_b = engine.run_sync(req)

    fp_a = fingerprint_result(result_a)
    fp_b = fingerprint_result(result_b)
    assert fp_a == fp_b, "相同请求两次运行应产生相同 fingerprint"
