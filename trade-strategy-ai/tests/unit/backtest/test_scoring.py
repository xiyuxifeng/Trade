"""NTL-S6-003: 回测评分模块单元测试"""

from __future__ import annotations

from datetime import date

import pytest

from src.evaluation.metrics_calculator import (
    TradeConstraint,
    compute_mfe_mae_return,
    _infer_board_type,
    _get_limit_pct,
    _resolve_constraint,
)


class TestScoreBacktestTrade:
    """回测交易评分测试（复用 Stage 5 评分口径）"""

    def test_score_backtest_trade_uses_stage5_metrics(self):
        """给定 bars 和入场/目标/止损价，返回与 Stage 5 一致的指标"""
        from src.backtest.scoring import score_backtest_trade

        result = score_backtest_trade(
            bars=[
                {"date": "2026-04-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2},
                {"date": "2026-04-02", "open": 10.2, "high": 10.8, "low": 10.0, "close": 10.6},
            ],
            entry_price=10.0,
            entry_date="2026-04-01",
            target_price=11.0,
            stop_loss_price=9.5,
        )
        # entry=10.0, close=10.6 → return_pct = 0.06
        assert result["return_pct"] == pytest.approx(0.06)
        assert "mfe" in result
        assert "mae" in result
        assert "exit_triggered" in result
        assert "exit_date" in result
        assert "halted_dates" in result
        assert "eval_date" in result

    def test_score_backtest_trade_stop_loss_triggered(self):
        """止损触发场景"""
        from src.backtest.scoring import score_backtest_trade

        result = score_backtest_trade(
            bars=[
                {"date": "2026-04-01", "open": 10.0, "high": 10.2, "low": 9.4, "close": 9.5},
                {"date": "2026-04-02", "open": 9.5, "high": 9.8, "low": 9.3, "close": 9.4},
            ],
            entry_price=10.0,
            entry_date="2026-04-01",
            target_price=11.0,
            stop_loss_price=9.5,
        )
        assert result["exit_triggered"] == "stop_loss"
        assert result["return_pct"] < 0  # 止损亏损

    def test_score_backtest_trade_target_triggered(self):
        """止盈触发场景"""
        from src.backtest.scoring import score_backtest_trade

        result = score_backtest_trade(
            bars=[
                {"date": "2026-04-01", "open": 10.0, "high": 10.2, "low": 9.8, "close": 10.1},
                {"date": "2026-04-02", "open": 10.1, "high": 11.2, "low": 10.5, "close": 11.0},
            ],
            entry_price=10.0,
            entry_date="2026-04-01",
            target_price=11.0,
            stop_loss_price=9.5,
        )
        assert result["exit_triggered"] == "target"

    def test_score_backtest_trade_no_bars(self):
        """无 bars 数据时返回零值"""
        from src.backtest.scoring import score_backtest_trade

        result = score_backtest_trade(
            bars=[],
            entry_price=10.0,
            entry_date="2026-04-01",
            target_price=11.0,
            stop_loss_price=9.5,
        )
        assert result["return_pct"] == 0.0
        assert result["mfe"] == 0.0
        assert result["mae"] == 0.0


class TestSTRuleDateSwitching:
    """ST 规则日期切换测试（NTL-S6-003 Step 6 新增）"""

    def test_shanghai_st_before_2026_07_06_limit_5_percent(self):
        """2026-07-05 沪市 ST，涨跌幅限制 5%"""
        # 沪市 ST（6开头）
        constraint = TradeConstraint(
            board_type="st",
            market="SH",
            trade_date=date(2026, 7, 5),
        )
        resolved = _resolve_constraint(constraint, "600001.SH")
        assert resolved.limit_up_pct == 0.05
        assert resolved.limit_down_pct == 0.05

    def test_shanghai_st_on_2026_07_06_limit_10_percent(self):
        """2026-07-06 沪市 ST，涨跌幅限制调整为 10%（规则切换日）"""
        constraint = TradeConstraint(
            board_type="st",
            market="SH",
            trade_date=date(2026, 7, 6),
        )
        resolved = _resolve_constraint(constraint, "600001.SH")
        assert resolved.limit_up_pct == 0.10
        assert resolved.limit_down_pct == 0.10

    def test_shenzhen_st_unchanged_after_2026_07_06(self):
        """2026-07-06 深市 ST，维持 5%（规则未变）"""
        constraint = TradeConstraint(
            board_type="st",
            market="SZ",
            trade_date=date(2026, 7, 6),
        )
        resolved = _resolve_constraint(constraint, "000001.SZ")
        assert resolved.limit_up_pct == 0.05
        assert resolved.limit_down_pct == 0.05

    def test_non_st_unchanged_after_rule_switch(self):
        """非 ST 股票规则不受影响"""
        for board_type in ["main", "chinext", "star"]:
            constraint = TradeConstraint(
                board_type=board_type,
                trade_date=date(2026, 7, 6),
            )
            resolved = _resolve_constraint(constraint, "600001.SH")
            if board_type == "main":
                assert resolved.limit_up_pct == 0.10
            elif board_type == "chinext" or board_type == "star":
                assert resolved.limit_up_pct == 0.20

    def test_infer_board_type_st(self):
        """ST 股票识别"""
        assert _infer_board_type("ST600001") == "st"
        assert _infer_board_type("ST000001") == "st"

    def test_infer_board_type_non_st(self):
        """非 ST 股票识别"""
        assert _infer_board_type("600001.SH") == "main"
        assert _infer_board_type("688001.SH") == "star"
        assert _infer_board_type("300001.SZ") == "chinext"
        assert _infer_board_type("000001.SZ") == "main"

    def test_trade_constraint_market_field(self):
        """TradeConstraint 支持 market 字段（沪市/深市区分）"""
        constraint = TradeConstraint(
            board_type="st",
            market="SH",
            trade_date=date(2026, 7, 6),
            t_plus_one=True,
        )
        assert constraint.market == "SH"
        assert constraint.trade_date == date(2026, 7, 6)
        assert constraint.t_plus_one is True

    def test_trade_constraint_trade_date_field(self):
        """TradeConstraint 支持 trade_date 字段"""
        constraint = TradeConstraint(
            board_type="st",
            trade_date=date(2026, 7, 6),
        )
        assert constraint.trade_date == date(2026, 7, 6)
