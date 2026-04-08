"""
交易特征集单元测试。
"""

from __future__ import annotations

import numpy as np
import pytest

from src.features.trade_stats import (
    TradeStats,
    compute_trade_stats,
    max_drawdown,
)


class TestMaxDrawdown:
    """max_drawdown 函数测试。"""

    def test_empty_returns(self):
        """空序列返回 0。"""
        assert max_drawdown(np.array([])) == 0.0

    def test_single_positive(self):
        """单笔正收益无回撤。"""
        returns = np.array([0.05])
        assert max_drawdown(returns) == 0.0

    def test_single_negative(self):
        """单笔负收益回撤为负。"""
        returns = np.array([-0.05])
        # 最大回撤是负数
        assert max_drawdown(returns) < 0.0

    def test_no_drawdown(self):
        """持续上涨无回撤。"""
        returns = np.array([0.01, 0.02, 0.03, 0.01])
        assert max_drawdown(returns) == 0.0

    def test_simple_drawdown(self):
        """简单回撤场景。"""
        # 涨 50%，跌 30%，再涨 10%
        returns = np.array([0.50, -0.30, 0.10])
        # 累计: 1.0 -> 1.5 -> 1.05 -> 1.155
        # 回撤: (1.05 - 1.5) / 1.5 = -0.30
        assert max_drawdown(returns) == pytest.approx(-0.30, rel=1e-10)

    def test_deep_drawdown(self):
        """深度回撤场景。"""
        returns = np.array([0.10, 0.10, -0.50, 0.10])
        # 累计: 1.0 -> 1.1 -> 1.21 -> 0.605 -> 0.6655
        # 最大回撤发生在 0.605 / 1.21 - 1 = -0.50
        assert max_drawdown(returns) == pytest.approx(-0.50, rel=1e-10)


class TestComputeTradeStats:
    """compute_trade_stats 函数测试。"""

    def test_empty_returns(self):
        """空序列返回零值。"""
        stats = compute_trade_stats(np.array([]))
        assert stats.total_return == 0.0
        assert stats.sharpe_ratio == 0.0
        assert stats.max_drawdown == 0.0
        assert stats.win_rate == 0.0
        assert stats.expected_value == 0.0

    def test_zero_returns(self):
        """零收益序列。"""
        returns = np.array([0.0, 0.0, 0.0])
        stats = compute_trade_stats(returns)
        assert stats.total_return == 0.0
        assert stats.sharpe_ratio == 0.0
        assert stats.win_rate == 0.0
        assert stats.expected_value == 0.0

    def test_single_trade_profit(self):
        """单笔盈利交易。"""
        returns = np.array([0.10])
        stats = compute_trade_stats(returns)
        assert stats.total_return == pytest.approx(0.10, rel=1e-9)
        assert stats.win_rate == 1.0
        assert stats.expected_value == pytest.approx(0.10, rel=1e-9)

    def test_single_trade_loss(self):
        """单笔亏损交易。"""
        returns = np.array([-0.10])
        stats = compute_trade_stats(returns)
        assert stats.total_return == pytest.approx(-0.10, rel=1e-9)
        assert stats.win_rate == 0.0
        assert stats.expected_value == pytest.approx(-0.10, rel=1e-9)

    def test_win_rate(self):
        """胜率计算。"""
        # 3胜 2负
        returns = np.array([0.05, -0.02, 0.03, 0.01, -0.01])
        stats = compute_trade_stats(returns)
        assert stats.win_rate == pytest.approx(0.60, rel=1e-9)

    def test_expected_value(self):
        """期望值计算。"""
        returns = np.array([0.10, -0.05, 0.05, -0.05])
        stats = compute_trade_stats(returns)
        # (0.10 - 0.05 + 0.05 - 0.05) / 4 = 0.0125
        assert stats.expected_value == pytest.approx(0.0125, rel=1e-9)

    def test_sharpe_ratio_zero_std(self):
        """标准差为零时夏普比为 0。"""
        returns = np.array([0.01, 0.01, 0.01, 0.01])
        stats = compute_trade_stats(returns, risk_free_rate=0.0)
        # 标准差为0，夏普比应为0
        assert stats.sharpe_ratio == 0.0

    def test_sharpe_ratio_positive(self):
        """正夏普比计算。"""
        # 日收益率: mean=0.001, std=0.01
        # 年化: return=0.252, std=0.1587
        # 夏普比 = 0.252 / 0.1587 ≈ 1.588
        returns = np.array([0.01, 0.005, -0.005, 0.008, -0.003, 0.012, 0.002, -0.002, 0.009, -0.001])
        stats = compute_trade_stats(returns, risk_free_rate=0.0)
        assert stats.sharpe_ratio > 0.0

    def test_total_return_compounding(self):
        """累计收益率计算（复利）。"""
        returns = np.array([0.10, 0.10])  # 各涨 10%
        # (1 + 0.10) * (1 + 0.10) - 1 = 0.21
        stats = compute_trade_stats(returns)
        assert stats.total_return == pytest.approx(0.21, rel=1e-9)

    def test_negative_total_return(self):
        """负总收益率。"""
        returns = np.array([-0.10, -0.10])
        # (1 - 0.10) * (1 - 0.10) - 1 = -0.19
        stats = compute_trade_stats(returns)
        assert stats.total_return == pytest.approx(-0.19, rel=1e-9)

    def test_max_drawdown_in_stats(self):
        """stats 中的最大回撤。"""
        returns = np.array([0.50, -0.30, 0.10])
        stats = compute_trade_stats(returns)
        assert stats.max_drawdown == pytest.approx(-0.30, rel=1e-10)

    def test_all_winning_trades(self):
        """全胜交易。"""
        returns = np.array([0.01, 0.02, 0.03, 0.01, 0.02])
        stats = compute_trade_stats(returns)
        assert stats.win_rate == 1.0
        assert stats.total_return > 0.0

    def test_all_losing_trades(self):
        """全败交易。"""
        returns = np.array([-0.01, -0.02, -0.03, -0.01, -0.02])
        stats = compute_trade_stats(returns)
        assert stats.win_rate == 0.0
        assert stats.total_return < 0.0

    def test_sharpe_ratio_with_risk_free(self):
        """有无风险利率的夏普比。"""
        returns = np.array([0.02, 0.01, -0.01, 0.015])
        # 无风险利率会降低夏普比
        stats_with_rf = compute_trade_stats(returns, risk_free_rate=0.02)
        stats_no_rf = compute_trade_stats(returns, risk_free_rate=0.0)
        # 夏普比应该因无风险利率而降低
        assert stats_with_rf.sharpe_ratio < stats_no_rf.sharpe_ratio

    def test_returns_dataclass_fields(self):
        """验证 TradeStats 所有字段。"""
        returns = np.array([0.05, -0.02, 0.03])
        stats = compute_trade_stats(returns)
        assert isinstance(stats.total_return, float)
        assert isinstance(stats.sharpe_ratio, float)
        assert isinstance(stats.max_drawdown, float)
        assert isinstance(stats.win_rate, float)
        assert isinstance(stats.expected_value, float)
