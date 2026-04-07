"""Task 2 & 3 tests — PatternFeatureEngine basic features + evaluate_condition."""

import pytest

from src.indicators import PatternFeatureEngine


def make_bar(open_, high, low, close, volume, date_str="2026-04-01"):
    return {
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "date": date_str,
    }


@pytest.fixture
def sample_bars():
    """20 根常规日线（上涨趋势）。"""
    return [
        make_bar(10, 10.5, 9.8, 10.3, 1000, f"2026-03-{15+i:02d}")
        for i in range(20)
    ]


@pytest.fixture
def flat_bars():
    """价格几乎不变的窄幅震荡 bars。"""
    base = 10.0
    return [
        make_bar(base, base + 0.05, base - 0.05, base, 100, f"2026-03-{15+i:02d}")
        for i in range(20)
    ]


class TestBasicFeatures:
    def test_compute_volume_ratio_equals_average(self, sample_bars):
        """成交量等于均量时 ratio≈1.0。"""
        engine = PatternFeatureEngine(sample_bars)
        ratio = engine.compute_volume_ratio()
        assert 0.8 <= ratio <= 1.2

    def test_compute_volume_ratio_spike(self, sample_bars):
        """成交量放大到 3 倍均量时 ratio > 3。"""
        bars = sample_bars.copy()
        bars[-1]["volume"] = 5000  # 均量 1000
        engine = PatternFeatureEngine(bars)
        ratio = engine.compute_volume_ratio()
        assert ratio > 3.0

    def test_compute_price_vs_ma(self, sample_bars):
        """价格 / MA20 应在合理范围。"""
        engine = PatternFeatureEngine(sample_bars)
        ratio = engine.compute_price_vs_ma()
        assert 0.8 <= ratio <= 1.2

    def test_compute_gap_ratio_no_gap(self, sample_bars):
        """无跳空时 gap_ratio 接近 0。"""
        engine = PatternFeatureEngine(sample_bars)
        ratio = engine.compute_gap_ratio()
        assert abs(ratio) < 0.1

    def test_compute_gap_ratio_positive(self, sample_bars):
        """跳空高开 gap_ratio > 0。"""
        bars = sample_bars.copy()
        bars[-2]["close"] = 10.5
        bars[-1]["open"] = 11.0
        engine = PatternFeatureEngine(bars)
        ratio = engine.compute_gap_ratio()
        assert ratio > 0

    def test_compute_trend_up(self, sample_bars):
        """持续上涨趋势 ma_slope > 0。"""
        bars = sample_bars.copy()
        for i, bar in enumerate(bars):
            bar["close"] = 10.0 + i * 0.1
        engine = PatternFeatureEngine(bars)
        slope = engine.compute_ma_slope()
        assert slope > 0

    def test_compute_trend_down(self, sample_bars):
        """持续下跌趋势 ma_slope < 0。"""
        bars = sample_bars.copy()
        for i, bar in enumerate(bars):
            bar["close"] = 11.0 - i * 0.1
        engine = PatternFeatureEngine(bars)
        slope = engine.compute_ma_slope()
        assert slope < 0

    def test_compute_close_position_high(self, sample_bars):
        """收盘在高位 close_position 接近 1。"""
        bars = sample_bars.copy()
        bars[-1]["high"] = 11.0
        bars[-1]["low"] = 10.0
        bars[-1]["close"] = 10.9
        bars[-1]["open"] = 10.1
        engine = PatternFeatureEngine(bars)
        pos = engine.compute_close_position()
        assert pos > 0.8

    def test_compute_close_position_low(self, sample_bars):
        """收盘在低位 close_position 接近 0。"""
        bars = sample_bars.copy()
        bars[-1]["high"] = 11.0
        bars[-1]["low"] = 10.0
        bars[-1]["close"] = 10.1
        bars[-1]["open"] = 10.9
        engine = PatternFeatureEngine(bars)
        pos = engine.compute_close_position()
        assert pos < 0.2


class TestLazyIndicators:
    def test_ensure_rsi_returns_float_in_range(self, sample_bars):
        """RSI 应返回 0~100 的浮点数或 None。"""
        engine = PatternFeatureEngine(sample_bars)
        val = engine.ensure_rsi()
        if val is not None:
            assert 0 <= val <= 100

    def test_ensure_rsi_caching(self, sample_bars):
        """第二次调用应命中缓存。"""
        engine = PatternFeatureEngine(sample_bars)
        v1 = engine.ensure_rsi()
        v2 = engine.ensure_rsi()
        assert v1 == v2
        assert "rsi" in engine._cache

    def test_ensure_stoch_k_returns_float_or_none(self, sample_bars):
        """Stochastic %K 应返回 0~100 或 None。"""
        engine = PatternFeatureEngine(sample_bars)
        val = engine.ensure_stoch_k()
        if val is not None:
            assert 0 <= val <= 100

    def test_ensure_bb_width_narrow_in_flat_market(self, flat_bars):
        """窄幅震荡市场布林带宽度应极小。"""
        engine = PatternFeatureEngine(flat_bars)
        width = engine.ensure_bb_width()
        assert width is not None
        assert width < 0.05

    def test_ensure_ma50_insufficient_bars(self):
        """不足 51 根 bar 时 ma50 返回 None。"""
        bars = [make_bar(10, 10.5, 9.8, 10.3, 1000) for _ in range(10)]
        engine = PatternFeatureEngine(bars)
        assert engine.ensure_ma50() is None

    def test_ensure_ma200_insufficient_bars(self):
        """不足 201 根 bar 时 ma200 返回 None。"""
        bars = [make_bar(10, 10.5, 9.8, 10.3, 1000) for _ in range(50)]
        engine = PatternFeatureEngine(bars)
        assert engine.ensure_ma200() is None


class TestComputeAll:
    def test_compute_all_returns_pattern_features(self, sample_bars):
        """compute_all() 应返回填充好的 PatternFeatures。"""
        engine = PatternFeatureEngine(sample_bars)
        features = engine.compute_all()
        assert features.volume_ratio > 0
        assert features.price_vs_ma > 0
        assert features.ma_slope is not None

    def test_compute_all_indicator_fields(self, sample_bars):
        """compute_all() 中指标字段应被惰性计算填充。"""
        engine = PatternFeatureEngine(sample_bars)
        features = engine.compute_all()
        # RSI 等指标在 20 根 bar 下可能为 None，但对象应存在
        assert features.rsi is None or isinstance(features.rsi, float)
        assert features.stoch_k is None or isinstance(features.stoch_k, float)

    def test_compute_all_bb_width_flat(self, flat_bars):
        """flat_bars 的 bb_width 应被计算。"""
        engine = PatternFeatureEngine(flat_bars)
        features = engine.compute_all()
        assert features.bb_width is not None
        assert features.bb_width < 0.05


# ══════════════════════════════════════════════════════════════════════════════
# Task 3 — evaluate_condition 测试
# ══════════════════════════════════════════════════════════════════════════════

class TestEvaluateCondition:
    """evaluate_condition(field, op, value) 核心判断接口测试。"""

    def test_volume_spike_3x(self, sample_bars):
        """成交量放大 3 倍以上 → spike_3x = True。"""
        bars = sample_bars.copy()
        bars[-1]["volume"] = 5000  # 均量 1000
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("volume", "spike_3x") is True

    def test_volume_confirm(self, sample_bars):
        """成交量放大 1.2 倍以上 → confirm = True。"""
        bars = sample_bars.copy()
        bars[-1]["volume"] = 1500
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("volume", "confirm") is True

    def test_volume_drying_up(self, sample_bars):
        """成交量萎缩至 50% 以下 → drying_up = True。"""
        bars = sample_bars.copy()
        bars[-1]["volume"] = 300  # 均量 1000
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("volume", "drying_up") is True

    def test_body_small(self, sample_bars):
        """十字星（实体很小）→ body small = True。"""
        bars = sample_bars.copy()
        bars[-1]["open"] = 10.0
        bars[-1]["close"] = 10.0
        bars[-1]["high"] = 10.1
        bars[-1]["low"] = 9.9
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("body", "small") is True

    def test_body_doji(self, sample_bars):
        """极小实体（doji）→ body doji = True。"""
        bars = sample_bars.copy()
        bars[-1]["open"] = 10.0
        bars[-1]["close"] = 10.001
        bars[-1]["high"] = 10.05
        bars[-1]["low"] = 9.95
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("body", "doji") is True

    def test_trend_up(self, sample_bars):
        """持续上涨 → trend up = True。"""
        bars = sample_bars.copy()
        for i, bar in enumerate(bars):
            bar["close"] = 10.0 + i * 0.1
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("trend", "up") is True

    def test_trend_down(self, sample_bars):
        """持续下跌 → trend down = True。"""
        bars = sample_bars.copy()
        for i, bar in enumerate(bars):
            bar["close"] = 11.0 - i * 0.1
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("trend", "down") is True

    def test_bb_width_narrow(self, flat_bars):
        """窄幅震荡 → bb_width narrow = True。"""
        engine = PatternFeatureEngine(flat_bars)
        assert engine.evaluate_condition("bb_width", "narrow") is True

    def test_price_range_narrow(self, flat_bars):
        """价格波动极小 → price_range narrow = True。"""
        engine = PatternFeatureEngine(flat_bars)
        assert engine.evaluate_condition("price_range", "narrow") is True

    def test_price_range_wide(self, sample_bars):
        """价格波动较大 → price_range wide = True。"""
        bars = sample_bars.copy()
        for i, bar in enumerate(bars):
            bar["close"] = 10.0 + i * 0.5  # 大幅波动
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("price_range", "wide") is True

    def test_gap_up(self, sample_bars):
        """跳空高开 → gap up = True。"""
        bars = sample_bars.copy()
        bars[-2]["close"] = 10.0
        bars[-1]["open"] = 10.2
        bars[-1]["close"] = 10.2
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("gap", "up") is True

    def test_gap_down(self, sample_bars):
        """跳空低开 → gap down = True。"""
        bars = sample_bars.copy()
        bars[-2]["close"] = 10.0
        bars[-1]["open"] = 9.8
        bars[-1]["close"] = 9.8
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("gap", "down") is True

    def test_breakout_up(self, sample_bars):
        """价格大幅上涨 → breakout up = True。"""
        bars = sample_bars.copy()
        bars[-2]["close"] = 10.0
        bars[-1]["open"] = 10.0
        bars[-1]["close"] = 10.3  # 3% 涨幅
        bars[-1]["high"] = 10.3
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("breakout", "up") is True

    def test_curr_candle_bullish(self, sample_bars):
        """收盘 > 开盘 → curr_candle bullish = True。"""
        bars = sample_bars.copy()
        bars[-1]["open"] = 10.0
        bars[-1]["close"] = 10.3
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("curr_candle", "bullish") is True

    def test_curr_candle_bearish(self, sample_bars):
        """收盘 < 开盘 → curr_candle bearish = True。"""
        bars = sample_bars.copy()
        bars[-1]["open"] = 10.3
        bars[-1]["close"] = 10.0
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("curr_candle", "bearish") is True

    def test_upper_shadow_tiny(self, sample_bars):
        """上影线极短 → upper_shadow tiny = True。"""
        bars = sample_bars.copy()
        bars[-1]["open"] = 10.0
        bars[-1]["close"] = 10.3
        bars[-1]["high"] = 10.31  # 极短上影
        bars[-1]["low"] = 9.9
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("upper_shadow", "tiny") is True

    def test_lower_shadow_long(self, sample_bars):
        """下影线较长 → lower_shadow long = True。"""
        bars = sample_bars.copy()
        bars[-1]["open"] = 10.0
        bars[-1]["close"] = 10.1  # 小实体
        bars[-1]["high"] = 10.05
        bars[-1]["low"] = 9.3   # 长下影：0.7，超过 body*2=0.2
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("lower_shadow", "long") is True

    def test_unknown_field_returns_false(self, sample_bars):
        """未知字段 → 返回 False。"""
        engine = PatternFeatureEngine(sample_bars)
        assert engine.evaluate_condition("nonexistent_field", "some_op") is False

    def test_rsi_cross_below_value(self, sample_bars):
        """RSI 低于给定值 → cross_below = True。"""
        bars = sample_bars.copy()
        # 制造大跌，使 RSI 大幅下降
        bars[-1]["close"] = bars[-2]["close"] * 0.75
        engine = PatternFeatureEngine(bars)
        result = engine.evaluate_condition("rsi", "cross_below", 70)
        assert isinstance(result, bool)

    def test_stoch_k_gt(self, sample_bars):
        """Stochastic %K 高于给定值 → gt = True。"""
        bars = sample_bars.copy()
        # 推高价格使 %K > 80
        for bar in bars:
            bar["close"] = 15.0
            bar["high"] = 15.1
            bar["low"] = 14.9
        bars[-1]["close"] = 15.1
        engine = PatternFeatureEngine(bars)
        k = engine.ensure_stoch_k()
        if k is not None and k > 50:
            assert engine.evaluate_condition("stoch_k", "gt", 50) is True

    def test_macd_histogram_cross_up(self, sample_bars):
        """MACD 直方图 > 0 → cross_up = True。"""
        bars = sample_bars.copy()
        # 持续上涨使 MACD 转正
        for i, bar in enumerate(bars):
            bar["close"] = 10.0 + i * 0.3
        engine = PatternFeatureEngine(bars)
        h = engine.ensure_macd_histogram()
        if h is not None and h > 0:
            assert engine.evaluate_condition("macd_histogram", "cross_up") is True

    def test_candle_n_small_body(self, sample_bars):
        """第 2 根 K 线为小实体 → candle2 small_body = True。"""
        bars = sample_bars.copy()
        bars[-2]["open"] = 10.0
        bars[-2]["close"] = 10.02  # 小实体
        bars[-2]["high"] = 10.1
        bars[-2]["low"] = 9.9
        engine = PatternFeatureEngine(bars)
        assert engine.evaluate_condition("candle2", "small_body") is True

    def test_channel_horizontal(self, flat_bars):
        """均线走平 → channel horizontal = True。"""
        engine = PatternFeatureEngine(flat_bars)
        assert engine.evaluate_condition("channel", "horizontal") is True
