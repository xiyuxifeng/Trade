"""
时间序列特征模块 — P2-018。

计算时间序列相关特征：
  - 趋势（线性回归斜率）
  - 波动性（历史波动率）
  - 自相关（滞后相关性）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class TimeSeriesFeatures:
    """时间序列特征 dataclass。"""
    # 趋势：线性回归斜率（单位时间价格变化）
    trend_slope: float | None = None
    # 趋势：R²（决定系数，0-1）
    trend_r_squared: float | None = None
    # 历史波动率（日收益率标准差年化）
    historical_volatility: float | None = None
    # 偏度（收益率分布偏斜）
    skewness: float | None = None
    # 峰度（收益率分布尖峰）
    kurtosis: float | None = None
    # 自相关系数（lag 1）
    autocorrelation_lag1: float | None = None
    # 自相关系数（lag 5）
    autocorrelation_lag5: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def to_array(self) -> np.ndarray:
        """转换为 numpy 数组。"""
        values = []
        defaults = [
            ("trend_slope", 0.0),
            ("trend_r_squared", 0.0),
            ("historical_volatility", 0.0),
            ("skewness", 0.0),
            ("kurtosis", 0.0),
            ("autocorrelation_lag1", 0.0),
            ("autocorrelation_lag5", 0.0),
        ]
        for name, default in defaults:
            val = getattr(self, name, None)
            values.append(val if val is not None else default)
        return np.array(values, dtype=np.float64)


def compute_trend(closes: np.ndarray, window: int = 20) -> tuple[float | None, float | None]:
    """计算趋势（线性回归）。

    Args:
        closes: 收盘价数组
        window: 计算窗口

    Returns:
        (slope, r_squared)，数据不足时返回 (None, None)
    """
    n = len(closes)
    if n < window:
        return None, None

    prices = closes[-window:]
    x = np.arange(window, dtype=np.float64)
    y = prices

    # 线性回归：y = a * x + b
    x_mean = np.mean(x)
    y_mean = np.mean(y)

    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    if denominator == 0:
        return None, None

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # R²
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)

    if ss_tot == 0:
        r_squared = 0.0
    else:
        r_squared = 1 - (ss_res / ss_tot)

    return float(slope), float(r_squared)


def compute_historical_volatility(
    closes: np.ndarray,
    window: int = 20,
    periods_per_year: int = 252,
) -> float | None:
    """计算历史波动率。

    Args:
        closes: 收盘价数组
        window: 计算窗口
        periods_per_year: 年化周期数

    Returns:
        年化波动率，数据不足时返回 None
    """
    n = len(closes)
    if n < window + 1:
        return None

    prices = closes[-window:]
    # 日收益率
    returns = np.diff(prices) / prices[:-1]

    if len(returns) < 2:
        return None

    # 标准差（年化）
    std_daily = np.std(returns, ddof=0)
    volatility = std_daily * np.sqrt(periods_per_year)

    return float(volatility)


def compute_skewness(closes: np.ndarray, window: int = 20) -> float | None:
    """计算收益率偏度。

    Args:
        closes: 收盘价数组
        window: 计算窗口

    Returns:
        偏度，数据不足时返回 None
    """
    n = len(closes)
    if n < window + 1:
        return None

    prices = closes[-window:]
    returns = np.diff(prices) / prices[:-1]

    if len(returns) < 2:
        return None

    mean = np.mean(returns)
    std = np.std(returns, ddof=0)

    if std == 0:
        return None

    # 偏度公式：E[(X - μ)³] / σ³
    skew = np.mean(((returns - mean) / std) ** 3)
    return float(skew)


def compute_kurtosis(closes: np.ndarray, window: int = 20) -> float | None:
    """计算收益率峰度。

    Args:
        closes: 收盘价数组
        window: 计算窗口

    Returns:
        峰度（超量峰度），数据不足时返回 None
    """
    n = len(closes)
    if n < window + 1:
        return None

    prices = closes[-window:]
    returns = np.diff(prices) / prices[:-1]

    if len(returns) < 2:
        return None

    mean = np.mean(returns)
    std = np.std(returns, ddof=0)

    if std == 0:
        return None

    # 峰度公式：E[(X - μ)⁴] / σ⁴ - 3（超量峰度）
    kurt = np.mean(((returns - mean) / std) ** 4) - 3
    return float(kurt)


def compute_autocorrelation(
    closes: np.ndarray,
    lags: list[int] | None = None,
    window: int = 20,
) -> dict[int, float | None]:
    """计算自相关系数。

    Args:
        closes: 收盘价数组
        lags: 滞后阶数列表，如 [1, 5]
        window: 计算窗口

    Returns:
        {lag: autocorrelation} 字典
    """
    if lags is None:
        lags = [1, 5]

    n = len(closes)
    if n < window + max(lags) if lags else window:
        return {lag: None for lag in lags}

    prices = closes[-window:]
    returns = np.diff(prices) / prices[:-1]

    result = {}
    for lag in lags:
        if len(returns) <= lag:
            result[lag] = None
            continue

        r_t = returns[:-lag] if lag > 0 else returns
        r_t_lag = returns[lag:] if lag > 0 else returns

        r_mean = np.mean(r_t)
        r_mean_lag = np.mean(r_t_lag)

        numerator = np.sum((r_t - r_mean) * (r_t_lag - r_mean_lag))
        denominator = np.sqrt(
            np.sum((r_t - r_mean) ** 2) * np.sum((r_t_lag - r_mean_lag) ** 2)
        )

        if denominator == 0:
            result[lag] = None
        else:
            result[lag] = float(numerator / denominator)

    return result


def compute_timeseries_features(
    closes: np.ndarray,
    window: int = 20,
) -> TimeSeriesFeatures:
    """计算时间序列特征。

    Args:
        closes: 收盘价数组
        window: 计算窗口

    Returns:
        TimeSeriesFeatures
    """
    features = TimeSeriesFeatures()

    # 趋势
    slope, r2 = compute_trend(closes, window)
    features.trend_slope = slope
    features.trend_r_squared = r2

    # 波动率
    features.historical_volatility = compute_historical_volatility(closes, window)

    # 偏度
    features.skewness = compute_skewness(closes, window)

    # 峰度
    features.kurtosis = compute_kurtosis(closes, window)

    # 自相关
    autocorr = compute_autocorrelation(closes, lags=[1, 5], window=window)
    features.autocorrelation_lag1 = autocorr.get(1)
    features.autocorrelation_lag5 = autocorr.get(5)

    return features
