"""FeatureEngine 单元测试"""
import pytest
from datetime import date
from src.strategy.feature_engine import FeatureEngine
from src.features.feature_pipeline import DailyBars


def _create_sample_bars() -> DailyBars:
    """创建样本日线数据"""
    import numpy as np
    n = 60
    dates = [date(2026, 1, 1) for _ in range(n)]
    base_price = 100.0
    closes = [base_price + i * 0.5 + np.random.randn() * 0.5 for i in range(n)]
    highs = [c * 1.02 for c in closes]
    lows = [c * 0.98 for c in closes]
    opens = [c * (1 + (np.random.randn() * 0.01)) for c in closes]
    volumes = [1_000_000 for _ in range(n)]
    return DailyBars(
        symbol="TEST",
        dates=dates,
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        volumes=volumes,
    )


def test_compute_realtime_returns_feature_vector():
    """测试实时计算返回特征向量"""
    engine = FeatureEngine()
    bars = _create_sample_bars()
    result = engine.compute_realtime(bars)
    assert result is not None
    assert hasattr(result, "rsi")
    assert hasattr(result, "macd")


def test_from_precomputed_returns_same():
    """测试预计算特征直接返回"""
    engine = FeatureEngine()
    bars = _create_sample_bars()
    features = engine.compute_realtime(bars)
    result = engine.from_precomputed(features)
    assert result is features


def test_compute_batch_multiple_symbols():
    """测试批量计算多标的"""
    engine = FeatureEngine()
    bars1 = _create_sample_bars()
    bars2 = _create_sample_bars()
    items = [("TEST1", bars1), ("TEST2", bars2)]
    result = engine.compute_batch(items)
    assert len(result) == 2
    assert "TEST1" in result
    assert "TEST2" in result