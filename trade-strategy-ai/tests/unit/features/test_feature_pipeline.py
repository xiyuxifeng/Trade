"""
特征计算脚本单元测试 — P2-015。
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import polars as pl
import pytest

from src.features.feature_pipeline import (
    DailyBars,
    FeatureVector,
    _cci,
    compute_features,
    compute_features_batch,
    compute_features_dataframe,
    compute_features_polars,
)


def _make_bars(n: int = 100) -> DailyBars:
    """生成模拟日线数据。"""
    dates = [date(2024, 1, 1) for _ in range(n)]
    # 简单上涨趋势：每天涨 0.5%
    base = 10.0
    closes = [base := base * (1 + 0.005) for _ in range(n)]
    opens = [c * 0.99 for c in closes]
    highs = [c * 1.02 for c in closes]
    lows = [c * 0.98 for c in closes]
    volumes = [1_000_000 for _ in range(n)]
    return DailyBars(
        symbol="000001.SZ",
        dates=dates,
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        volumes=volumes,
    )


class TestDailyBars:
    """DailyBars 测试。"""

    def test_len(self):
        bars = _make_bars(50)
        assert len(bars) == 50

    def test_to_arrays(self):
        bars = _make_bars(10)
        opens, highs, lows, closes, volumes = bars._to_arrays()
        assert len(opens) == 10
        assert len(highs) == 10
        assert len(lows) == 10
        assert len(closes) == 10
        assert len(volumes) == 10


class TestComputeFeatures:
    """compute_features 核心函数测试。"""

    def test_empty_bars(self):
        """空数据返回默认特征。"""
        bars = DailyBars(symbol="TEST")
        result = compute_features(bars)
        assert isinstance(result, FeatureVector)
        # 所有字段应为 None 或默认值

    def test_insufficient_data(self):
        """数据不足。"""
        bars = _make_bars(5)
        result = compute_features(bars)
        # MA20 需要至少 20 个数据点
        assert result.ma20 is None

    def test_ma20(self):
        """MA20 计算。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.ma20 is not None
        assert result.price_vs_ma20 is not None

    def test_ma50(self):
        """MA50 计算。"""
        bars = _make_bars(60)
        result = compute_features(bars)
        assert result.ma50 is not None
        assert result.price_vs_ma50 is not None

    def test_rsi(self):
        """RSI 计算。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.rsi is not None
        assert 0 <= result.rsi <= 100

    def test_stochastic(self):
        """Stochastic 计算。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.stochastic_k is not None
        assert result.stochastic_d is not None
        assert 0 <= result.stochastic_k <= 100
        assert 0 <= result.stochastic_d <= 100

    def test_macd(self):
        """MACD 计算。"""
        # 需要足够的数据量确保 signal_line 有有效值
        bars = _make_bars(100)
        result = compute_features(bars)
        assert result.macd is not None
        # signal 需要额外 8 个数据点才有效
        if result.macd_signal is not None:
            assert result.macd_histogram is not None

    def test_bollinger(self):
        """Bollinger Bands 计算。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.bollinger_upper is not None
        assert result.bollinger_middle is not None
        assert result.bollinger_lower is not None
        # 上轨 > 中轨 > 下轨
        assert result.bollinger_upper > result.bollinger_middle
        assert result.bollinger_middle > result.bollinger_lower

    def test_cci(self):
        """CCI 计算。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.cci is not None

    def test_volume_ratio(self):
        """成交量比。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.volume_ratio is not None
        assert result.volume_ratio > 0

    def test_close_position(self):
        """收盘位置。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.close_position is not None
        assert 0 <= result.close_position <= 1

    def test_gap_ratio(self):
        """跳空比率。"""
        bars = _make_bars(10)
        result = compute_features(bars)
        assert result.gap_ratio is not None

    def test_atr_ratio(self):
        """ATR 比率。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.atr_ratio is not None
        assert result.atr is not None

    def test_price_volatility(self):
        """价格波动率。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.price_volatility is not None
        assert result.price_volatility >= 0

    def test_breakout_ratios(self):
        """突破/跌破比率。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        assert result.high_breakout_ratio is not None
        assert result.low_breakout_ratio is not None


class TestFeatureVector:
    """FeatureVector 测试。"""

    def test_to_dict(self):
        """转换为字典。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "rsi" in d
        assert "ma20" in d

    def test_to_array(self):
        """转换为 numpy 数组。"""
        bars = _make_bars(30)
        result = compute_features(bars)
        arr = result.to_array()
        assert isinstance(arr, np.ndarray)
        assert len(arr) > 0


class TestCci:
    """CCI 辅助函数测试。"""

    def test_cci_basic(self):
        """CCI 基本计算。"""
        typical_prices = np.array([10.0, 11.0, 10.5, 11.5, 12.0] * 4)
        result = _cci(typical_prices, 4)
        assert len(result) == len(typical_prices)
        # 有效值应在 -100 到 100 之间
        valid = result[~np.isnan(result)]
        assert len(valid) > 0

    def test_cci_insufficient_data(self):
        """数据不足返回全 nan。"""
        typical_prices = np.array([10.0, 11.0])
        result = _cci(typical_prices, 4)
        assert np.all(np.isnan(result))


class TestComputeFeaturesDataframe:
    """Pandas DataFrame 测试。"""

    def test_dataframe_features(self):
        """DataFrame 计算特征。"""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=50),
            "open": np.random.uniform(9.5, 10.5, 50),
            "high": np.random.uniform(10.0, 11.0, 50),
            "low": np.random.uniform(9.0, 10.0, 50),
            "close": np.random.uniform(9.8, 10.8, 50),
            "volume": np.random.uniform(1e6, 2e6, 50),
        })
        result = compute_features_dataframe(df)
        assert "rsi" in result.columns
        assert "ma20" in result.columns
        assert len(result) == len(df)

    def test_dataframe_missing_columns(self):
        """缺少列时抛出异常。"""
        df = pd.DataFrame({"open": [1, 2, 3]})
        with pytest.raises(ValueError, match="Missing columns"):
            compute_features_dataframe(df)

    def test_dataframe_type_error(self):
        """非 DataFrame 抛出异常。"""
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            compute_features_dataframe({"open": [1, 2, 3]})


class TestComputeFeaturesPolars:
    """Polars DataFrame 测试。"""

    def test_polars_features(self):
        """Polars DataFrame 计算特征。"""
        df = pl.DataFrame({
            "date": pd.date_range("2024-01-01", periods=50).tolist(),
            "open": np.random.uniform(9.5, 10.5, 50).tolist(),
            "high": np.random.uniform(10.0, 11.0, 50).tolist(),
            "low": np.random.uniform(9.0, 10.0, 50).tolist(),
            "close": np.random.uniform(9.8, 10.8, 50).tolist(),
            "volume": np.random.uniform(1e6, 2e6, 50).tolist(),
        })
        result = compute_features_polars(df)
        assert "rsi" in result.columns
        assert "ma20" in result.columns
        assert len(result) == len(df)

    def test_polars_missing_columns(self):
        """缺少列时抛出异常。"""
        df = pl.DataFrame({"open": [1, 2, 3]})
        with pytest.raises(ValueError, match="Missing columns"):
            compute_features_polars(df)

    def test_polars_type_error(self):
        """非 DataFrame 抛出异常。"""
        with pytest.raises(TypeError, match="Expected polars DataFrame"):
            compute_features_polars({"open": [1, 2, 3]})


class TestComputeFeaturesBatch:
    """批量处理测试。"""

    def test_batch_processing(self):
        """批量计算多个标的特征。"""
        bars_list = [
            _make_bars(30),
            _make_bars(40),
            _make_bars(50),
        ]
        results = compute_features_batch(bars_list)
        assert len(results) == 3
        assert all(isinstance(r, FeatureVector) for r in results)

    def test_batch_empty(self):
        """空列表。"""
        results = compute_features_batch([])
        assert results == []
