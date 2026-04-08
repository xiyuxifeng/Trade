"""
时间序列特征单元测试 — P2-018。
"""

from __future__ import annotations

import numpy as np
import pytest

from src.features.timeseries import (
    TimeSeriesFeatures,
    compute_autocorrelation,
    compute_historical_volatility,
    compute_kurtosis,
    compute_skewness,
    compute_timeseries_features,
    compute_trend,
)


class TestComputeTrend:
    """趋势计算测试。"""

    def test_uptrend(self):
        """上涨趋势。"""
        # 线性上涨：价格从 10 涨到 20
        closes = np.linspace(10, 20, 20)
        slope, r2 = compute_trend(closes, window=20)
        assert slope is not None
        assert slope > 0  # 上涨
        assert r2 is not None
        assert r2 > 0.9  # 线性拟合良好

    def test_downtrend(self):
        """下跌趋势。"""
        # 线性下跌：价格从 20 跌到 10
        closes = np.linspace(20, 10, 20)
        slope, r2 = compute_trend(closes, window=20)
        assert slope is not None
        assert slope < 0  # 下跌

    def test_no_trend(self):
        """无趋势（震荡）。"""
        # 震荡：价格围绕 15 波动
        closes = np.array([15.0, 16.0, 14.0, 16.0, 15.0, 14.0, 16.0, 15.0] * 3)
        slope, r2 = compute_trend(closes[-20:], window=20)
        assert slope is not None
        assert abs(slope) < 0.1  # 斜率接近 0

    def test_insufficient_data(self):
        """数据不足。"""
        closes = np.array([10.0, 11.0, 12.0])
        slope, r2 = compute_trend(closes, window=20)
        assert slope is None
        assert r2 is None


class TestComputeHistoricalVolatility:
    """历史波动率测试。"""

    def test_volatility(self):
        """波动率计算。"""
        # 高波动：随机游走，需要 window+1 个价格数据
        np.random.seed(42)
        closes = 10 * np.exp(np.cumsum(np.random.randn(31) * 0.02))
        vol = compute_historical_volatility(closes, window=30)
        assert vol is not None
        assert vol > 0  # 应该有波动

    def test_zero_volatility(self):
        """零波动。"""
        closes = np.linspace(10, 10, 31)  # 固定价格，需要 window+1
        vol = compute_historical_volatility(closes, window=30)
        assert vol is not None
        assert vol == pytest.approx(0.0, abs=1e-6)

    def test_insufficient_data(self):
        """数据不足。"""
        closes = np.array([10.0, 11.0, 12.0])
        vol = compute_historical_volatility(closes, window=20)
        assert vol is None


class TestComputeSkewness:
    """偏度计算测试。"""

    def test_skewness(self):
        """偏度计算。"""
        np.random.seed(42)
        # 生成右偏分布（正收益更频繁，小亏损偶尔大）
        returns = np.random.randn(101) * 0.01 + 0.005
        closes = 10 * np.exp(np.cumsum(returns))
        skew = compute_skewness(closes, window=100)
        assert skew is not None
        # 右偏（正收益偏离多于负收益）

    def test_symmetric_distribution(self):
        """对称分布偏度接近 0。"""
        np.random.seed(42)
        returns = np.random.randn(101) * 0.01
        closes = 10 * np.exp(np.cumsum(returns))
        skew = compute_skewness(closes, window=100)
        assert skew is not None
        assert abs(skew) < 1.0  # 应该接近 0

    def test_insufficient_data(self):
        """数据不足。"""
        closes = np.array([10.0, 11.0, 12.0])
        skew = compute_skewness(closes, window=20)
        assert skew is None


class TestComputeKurtosis:
    """峰度计算测试。"""

    def test_kurtosis(self):
        """峰度计算。"""
        np.random.seed(42)
        returns = np.random.randn(101) * 0.01
        closes = 10 * np.exp(np.cumsum(returns))
        kurt = compute_kurtosis(closes, window=100)
        assert kurt is not None
        # 可以是正或负

    def test_insufficient_data(self):
        """数据不足。"""
        closes = np.array([10.0, 11.0, 12.0])
        kurt = compute_kurtosis(closes, window=20)
        assert kurt is None


class TestComputeAutocorrelation:
    """自相关计算测试。"""

    def test_autocorrelation_lag1(self):
        """lag-1 自相关。"""
        # 自相关：今天的收益与昨天的收益相关
        np.random.seed(42)
        returns = np.random.randn(100) * 0.01
        closes = 10 * np.exp(np.cumsum(returns))
        result = compute_autocorrelation(closes, lags=[1], window=50)
        assert 1 in result

    def test_autocorrelation_multiple_lags(self):
        """多滞后自相关。"""
        np.random.seed(42)
        returns = np.random.randn(100) * 0.01
        closes = 10 * np.exp(np.cumsum(returns))
        result = compute_autocorrelation(closes, lags=[1, 5, 10], window=50)
        assert result[1] is not None
        assert result[5] is not None
        assert result[10] is not None

    def test_default_lags(self):
        """默认滞后阶数。"""
        np.random.seed(42)
        returns = np.random.randn(100) * 0.01
        closes = 10 * np.exp(np.cumsum(returns))
        result = compute_autocorrelation(closes, window=50)
        assert 1 in result
        assert 5 in result


class TestComputeTimeseriesFeatures:
    """时间序列特征综合测试。"""

    def test_all_features(self):
        """所有特征。"""
        np.random.seed(42)
        # 需要 window+1 个价格数据来计算 window 个收益率
        closes = 10 * np.exp(np.cumsum(np.random.randn(55) * 0.01))
        features = compute_timeseries_features(closes, window=50)

        assert isinstance(features, TimeSeriesFeatures)
        assert features.trend_slope is not None
        assert features.trend_r_squared is not None
        assert features.historical_volatility is not None
        assert features.skewness is not None
        assert features.kurtosis is not None
        assert features.autocorrelation_lag1 is not None
        assert features.autocorrelation_lag5 is not None

    def test_no_features_insufficient_data(self):
        """数据不足时特征为 None。"""
        closes = np.array([10.0, 11.0])
        features = compute_timeseries_features(closes, window=20)
        # 大部分特征应为 None
        assert features.trend_slope is None
        assert features.historical_volatility is None


class TestTimeSeriesFeatures:
    """TimeSeriesFeatures 数据结构测试。"""

    def test_to_dict(self):
        """转换为字典。"""
        features = TimeSeriesFeatures(
            trend_slope=0.5,
            trend_r_squared=0.8,
            historical_volatility=0.2,
        )
        d = features.to_dict()
        assert isinstance(d, dict)
        assert d["trend_slope"] == 0.5

    def test_to_array(self):
        """转换为数组。"""
        features = TimeSeriesFeatures(trend_slope=0.5)
        arr = features.to_array()
        assert isinstance(arr, np.ndarray)
        assert len(arr) > 0
