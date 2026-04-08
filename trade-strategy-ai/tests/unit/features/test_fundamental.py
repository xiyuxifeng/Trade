"""
基本面特征单元测试 — P2-017。
"""

from __future__ import annotations

import numpy as np
import pytest

from src.features.fundamental import (
    FundamentalFeatures,
    compute_annualized_change,
    compute_fundamental_features,
    compute_pb_ratio,
    compute_pe_ratio,
    compute_price_change_rate,
    compute_volume_change_rate,
)


class TestComputePeRatio:
    """PE 计算测试。"""

    def test_positive_eps(self):
        """正常 EPS。"""
        assert compute_pe_ratio(10.0, 0.5) == pytest.approx(20.0, rel=1e-9)

    def test_zero_eps(self):
        """EPS 为零返回 None。"""
        assert compute_pe_ratio(10.0, 0.0) is None

    def test_negative_eps(self):
        """负 EPS 返回 None。"""
        assert compute_pe_ratio(10.0, -0.5) is None


class TestComputePbRatio:
    """PB 计算测试。"""

    def test_positive_book_value(self):
        """正常净资产。"""
        assert compute_pb_ratio(10.0, 2.0) == pytest.approx(5.0, rel=1e-9)

    def test_zero_book_value(self):
        """净资产为零返回 None。"""
        assert compute_pb_ratio(10.0, 0.0) is None

    def test_negative_book_value(self):
        """负净资产返回 None。"""
        assert compute_pb_ratio(10.0, -1.0) is None


class TestComputePriceChangeRate:
    """价格涨速测试。"""

    def test_positive_change(self):
        """上涨。"""
        closes = np.array([10.0, 11.0, 12.0, 13.0, 15.0])
        # window=4: current=closes[-1]=15, past=closes[-4]=closes[1]=11
        result = compute_price_change_rate(closes, window=4)
        assert result == pytest.approx(0.3636, rel=1e-3)  # 15/11 - 1 ≈ 0.3636

    def test_negative_change(self):
        """下跌。"""
        closes = np.array([15.0, 14.0, 13.0, 12.0, 10.0])
        # window=4: current=closes[-1]=10, past=closes[-4]=closes[1]=14
        result = compute_price_change_rate(closes, window=4)
        assert result == pytest.approx(-0.2857, rel=1e-3)  # 10/14 - 1 ≈ -0.2857

    def test_insufficient_data(self):
        """数据不足返回 None。"""
        closes = np.array([10.0, 11.0])
        result = compute_price_change_rate(closes, window=5)
        assert result is None

    def test_zero_past_price(self):
        """过去价格为零返回 None。"""
        closes = np.array([1.0, 0.0, 12.0, 13.0, 15.0])
        result = compute_price_change_rate(closes, window=4)
        assert result is None


class TestComputeAnnualizedChange:
    """年化涨速测试。"""

    def test_annualized_positive(self):
        """年化上涨。"""
        closes = np.array([10.0, 11.0] * 20)
        result = compute_annualized_change(closes, window=20)
        assert result is not None
        assert result > 0  # 一年期年化涨幅

    def test_annualized_negative(self):
        """年化下跌。"""
        closes = np.array([15.0, 14.0] * 20)
        result = compute_annualized_change(closes, window=20)
        assert result is not None
        assert result < 0

    def test_insufficient_data(self):
        """数据不足返回 None。"""
        closes = np.array([10.0, 11.0])
        result = compute_annualized_change(closes, window=5)
        assert result is None


class TestComputeVolumeChangeRate:
    """成交量变化率测试。"""

    def test_volume_increase(self):
        """成交量增加。"""
        volumes = np.array([1e6, 1e6, 1e6, 1e6, 2e6])
        result = compute_volume_change_rate(volumes, window=4)
        assert result == pytest.approx(1.0, rel=1e-9)  # 2e6/1e6 - 1 = 1.0

    def test_volume_decrease(self):
        """成交量减少。"""
        volumes = np.array([2e6, 2e6, 2e6, 2e6, 1e6])
        result = compute_volume_change_rate(volumes, window=4)
        assert result == pytest.approx(-0.5, rel=1e-9)  # 1e6/2e6 - 1 = -0.5

    def test_insufficient_data(self):
        """数据不足返回 None。"""
        volumes = np.array([1e6, 2e6])
        result = compute_volume_change_rate(volumes, window=5)
        assert result is None


class TestComputeFundamentalFeatures:
    """基本面特征综合测试。"""

    def test_all_features(self):
        """所有特征。"""
        closes = np.array([10.0, 11.0, 12.0, 13.0, 15.0] * 10)
        volumes = np.array([1e6, 1e6, 1e6, 1e6, 2e6] * 10)
        result = compute_fundamental_features(
            price=15.0,
            eps=0.5,
            book_value_per_share=3.0,
            closes=closes,
            volumes=volumes,
            market_cap=1e10,
            window=20,
        )
        assert result.pe_ratio == pytest.approx(30.0, rel=1e-9)
        assert result.pb_ratio == pytest.approx(5.0, rel=1e-9)
        assert result.price_change_rate is not None
        assert result.annualized_price_change is not None
        assert result.volume_change_rate is not None
        assert result.market_cap == 1e10

    def test_partial_features(self):
        """部分特征（无 EPS）。"""
        closes = np.array([10.0, 11.0, 12.0, 13.0, 15.0] * 10)
        result = compute_fundamental_features(
            price=15.0,
            closes=closes,
            window=20,
        )
        assert result.pe_ratio is None  # 无 EPS
        assert result.price_change_rate is not None

    def test_no_data(self):
        """无数据。"""
        result = compute_fundamental_features(price=15.0)
        assert result.pe_ratio is None
        assert result.pb_ratio is None
        assert result.price_change_rate is None


class TestFundamentalFeatures:
    """FundamentalFeatures 数据结构测试。"""

    def test_to_dict(self):
        """转换为字典。"""
        features = FundamentalFeatures(pe_ratio=20.0, pb_ratio=3.0)
        d = features.to_dict()
        assert isinstance(d, dict)
        assert d["pe_ratio"] == 20.0
        assert d["pb_ratio"] == 3.0

    def test_to_array(self):
        """转换为数组。"""
        features = FundamentalFeatures(pe_ratio=20.0, pb_ratio=3.0)
        arr = features.to_array()
        assert isinstance(arr, np.ndarray)
        assert len(arr) > 0
