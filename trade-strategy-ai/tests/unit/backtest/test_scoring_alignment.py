"""NTL-S6-007: 线上线下 scoring 口径一致性测试"""

from __future__ import annotations

import pytest

from src.evaluation.metrics_calculator import compute_mfe_mae_return
from src.backtest.scoring import score_backtest_trade


class TestOnlineOfflineScoringAlignment:
    """验证回测 scoring 与线上 evaluation 使用同一口径"""

    def test_same_bars_same_entry_same_result(self):
        """同一 bars + entry + target + stop，线上线下 return_pct 完全一致"""
        bars = [
            {"date": "2026-04-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2},
            {"date": "2026-04-02", "open": 10.2, "high": 10.8, "low": 10.0, "close": 10.6},
            {"date": "2026-04-03", "open": 10.6, "high": 11.0, "low": 10.4, "close": 10.8},
        ]

        # Online path
        online_result = compute_mfe_mae_return(
            bars=bars,
            entry_price=10.0,
            entry_date="2026-04-01",
            target_price=11.0,
            stop_loss_price=9.5,
            symbol="000001.SZ",
        )
        online_return = online_result[2]  # return_pct 是第3个返回值

        # Offline path
        offline_result = score_backtest_trade(
            bars=bars,
            entry_price=10.0,
            entry_date="2026-04-01",
            target_price=11.0,
            stop_loss_price=9.5,
            symbol="000001.SZ",
        )
        offline_return = offline_result["return_pct"]

        assert offline_return == pytest.approx(online_result[2])
        assert offline_return == pytest.approx(0.08)  # 10.8/10.0 - 1

    def test_same_bars_same_mfe_mae(self):
        """同一 bars，线上线下 mfe/mae 完全一致"""
        bars = [
            {"date": "2026-04-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2},
            {"date": "2026-04-02", "open": 10.2, "high": 11.0, "low": 10.0, "close": 10.8},
        ]

        online_result = compute_mfe_mae_return(
            bars=bars,
            entry_price=10.0,
            entry_date="2026-04-01",
            symbol="000001.SZ",
        )
        offline_result = score_backtest_trade(
            bars=bars,
            entry_price=10.0,
            entry_date="2026-04-01",
            symbol="000001.SZ",
        )

        # online: (mfe, mae, return_pct, ...) = (1.0, 0.0, 0.08, ...)
        assert offline_result["mfe"] == pytest.approx(online_result[0])
        assert offline_result["mae"] == pytest.approx(online_result[1])
        assert offline_result["return_pct"] == pytest.approx(online_result[2])
        assert offline_result["exit_triggered"] == online_result[3]
        assert offline_result["exit_date"] == online_result[4]

    def test_all_7_return_values_present_in_offline(self):
        """score_backtest_trade 返回值包含全部 7 个字段"""
        bars = [
            {"date": "2026-04-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2},
        ]
        result = score_backtest_trade(
            bars=bars,
            entry_price=10.0,
            entry_date="2026-04-01",
        )
        assert "mfe" in result
        assert "mae" in result
        assert "return_pct" in result
        assert "exit_triggered" in result
        assert "exit_date" in result
        assert "halted_dates" in result
        assert "eval_date" in result
