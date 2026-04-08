"""
交易特征集计算模块。

计算交易策略的核心统计指标：
- 总收益率
- 夏普比
- 最大回撤
- 胜率
- 期望值
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TradeStats:
    """交易特征集 dataclass。"""
    # 总收益率（百分比，如 0.15 表示 15%）
    total_return: float
    # 夏普比（年化）
    sharpe_ratio: float
    # 最大回撤（百分比，如 -0.20 表示 20% 回撤）
    max_drawdown: float
    # 胜率（0-1，如 0.6 表示 60% 胜率）
    win_rate: float
    # 期望值（每次交易平均收益）
    expected_value: float


def max_drawdown(returns: np.ndarray) -> float:
    """计算最大回撤。

    Args:
        returns: 收益率序列（如 [0.01, -0.02, 0.03, ...]）

    Returns:
        最大回撤值（负数），如 -0.20 表示 20% 最大回撤
    """
    if len(returns) < 1:
        return 0.0

    # 累计收益曲线（从初始资金 1.0 开始）
    cumulative = np.cumprod(1 + returns)
    # 插入初始资金 1.0 作为起点，确保初始高点被记录
    cumulative = np.concatenate([[1.0], cumulative])
    # 截至当前的历史最高点
    running_max = np.maximum.accumulate(cumulative)
    # 回撤 = (当前值 - 历史最高) / 历史最高
    drawdowns = (cumulative - running_max) / running_max

    return float(np.min(drawdowns))


def compute_trade_stats(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> TradeStats:
    """计算交易特征集。

    Args:
        returns: 收益率序列（如日收益率），支持负数
        risk_free_rate: 年化无风险利率（默认 0）
        periods_per_year: 年化交易日数（默认 252）

    Returns:
        TradeStats dataclass
    """
    if len(returns) < 1:
        return TradeStats(
            total_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            expected_value=0.0,
        )

    # 总收益率 = 累计收益 - 1
    cumulative_return = np.cumprod(1 + returns)
    total_return = float(cumulative_return[-1] - 1)

    # 夏普比
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=0)  # 总体标准差
    if std_return == 0 or np.isnan(std_return):
        sharpe_ratio = 0.0
    else:
        # 年化夏普比
        annualized_return = mean_return * periods_per_year
        annualized_std = std_return * np.sqrt(periods_per_year)
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_std

    # 最大回撤
    max_dd = max_drawdown(returns)

    # 胜率（正收益次数 / 总次数）
    winning_trades = np.sum(returns > 0)
    win_rate = float(winning_trades / len(returns))

    # 期望值（平均收益）
    expected_value = float(np.mean(returns))

    return TradeStats(
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_dd,
        win_rate=win_rate,
        expected_value=expected_value,
    )
