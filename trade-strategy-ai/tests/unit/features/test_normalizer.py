"""
特征归一化单元测试 — P2-011。
"""

from __future__ import annotations

import numpy as np
import pytest

from src.features.normalizer import (
    FeatureNormalizer,
    NormalizationParams,
    normalize_features,
    normalize_feature_matrix,
)


class TestFeatureNormalizer:
    """FeatureNormalizer 测试。"""

    def test_zscore_basic(self):
        """Z-Score 基本功能。"""
        values = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        normalizer = FeatureNormalizer(method="zscore")
        result = normalizer.fit_transform(values)

        assert result.mean() == pytest.approx(0.0, abs=1e-10)
        assert result.std() == pytest.approx(1.0, abs=1e-10)

    def test_zscore_with_clip(self):
        """Z-Score 截断。"""
        values = np.array([1, 2, 3, 4, 5, 100])  # 100 是异常值
        normalizer = FeatureNormalizer(method="zscore")
        result = normalizer.fit_transform(values, clip=True)

        # 异常值应该被截断到 3σ
        assert np.max(np.abs(result)) <= 3.0

    def test_zscore_zero_std(self):
        """标准差为零。"""
        values = np.array([5, 5, 5, 5])
        normalizer = FeatureNormalizer(method="zscore")
        result = normalizer.fit_transform(values)

        assert np.all(result == 0.0)

    def test_minmax_basic(self):
        """Min-Max 基本功能。"""
        values = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        normalizer = FeatureNormalizer(method="minmax")
        result = normalizer.fit_transform(values)

        assert np.min(result) == pytest.approx(0.0, abs=1e-10)
        assert np.max(result) == pytest.approx(1.0, abs=1e-10)

    def test_minmax_with_clip(self):
        """Min-Max 截断。"""
        values = np.array([1, 2, 3, 4, 5, 100])
        normalizer = FeatureNormalizer(method="minmax")
        result = normalizer.fit_transform(values, clip=True)

        assert np.max(result) <= 1.0
        assert np.min(result) >= 0.0

    def test_robust_basic(self):
        """Robust 基本功能。"""
        values = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        normalizer = FeatureNormalizer(method="robust")
        result = normalizer.fit_transform(values)

        # 中位数应该接近 0
        assert np.median(result) == pytest.approx(0.0, abs=0.5)

    def test_robust_with_outliers(self):
        """Robust 抗异常值。"""
        values = np.array([1, 2, 3, 4, 5, 100])  # 100 是异常值
        normalizer = FeatureNormalizer(method="robust")
        result = normalizer.fit_transform(values, clip=True)

        # 正常值应该被正确归一化
        assert result[2] < 1.0  # 3 应该接近 0

    def test_invalid_method(self):
        """无效方法。"""
        with pytest.raises(ValueError, match="method must be one of"):
            FeatureNormalizer(method="invalid")

    def test_inverse_transform_zscore(self):
        """Z-Score 反归一化。"""
        values = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        normalizer = FeatureNormalizer(method="zscore")
        normalized = normalizer.fit_transform(values)
        restored = normalizer.inverse_transform(normalized)

        assert np.allclose(values, restored, rtol=1e-10)

    def test_inverse_transform_minmax(self):
        """Min-Max 反归一化。"""
        values = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        normalizer = FeatureNormalizer(method="minmax")
        normalized = normalizer.fit_transform(values)
        restored = normalizer.inverse_transform(normalized)

        assert np.allclose(values, restored, rtol=1e-10)

    def test_inverse_transform_robust(self):
        """Robust 反归一化。"""
        values = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        normalizer = FeatureNormalizer(method="robust")
        normalized = normalizer.fit_transform(values)
        restored = normalizer.inverse_transform(normalized)

        assert np.allclose(values, restored, rtol=1e-10)


class TestNormalizationParams:
    """NormalizationParams 测试。"""

    def test_to_dict(self):
        """转换为字典。"""
        params = NormalizationParams(mean=10.0, std=2.0)
        d = params.to_dict()
        assert isinstance(d, dict)
        assert d["mean"] == 10.0
        assert d["std"] == 2.0
        assert "median" not in d


class TestNormalizeFeatures:
    """normalize_features 快捷函数测试。"""

    def test_normalize_dict_zscore(self):
        """Z-Score 归一化字典。"""
        features = {"a": 1.0, "b": 2.0, "c": 3.0}
        result = normalize_features(features, method="zscore")
        assert len(result) == 3
        # 均值应该为 0
        assert np.mean(list(result.values())) == pytest.approx(0.0, abs=1e-10)

    def test_normalize_dict_with_none(self):
        """带 None 值。"""
        features = {"a": 1.0, "b": None, "c": 3.0}
        result = normalize_features(features, method="zscore")
        assert len(result) == 2  # None 被过滤
        assert "b" not in result

    def test_normalize_empty_dict(self):
        """空字典。"""
        result = normalize_features({}, method="zscore")
        assert result == {}


class TestNormalizeFeatureMatrix:
    """normalize_feature_matrix 测试。"""

    def test_matrix_2d(self):
        """2D 矩阵。"""
        matrix = np.array([
            [1, 10],
            [2, 20],
            [3, 30],
            [4, 40],
            [5, 50],
        ])
        normalized, params = normalize_feature_matrix(matrix, method="zscore")

        assert normalized.shape == matrix.shape
        assert len(params) == 2

        # 每列均值应该为 0
        assert np.mean(normalized[:, 0]) == pytest.approx(0.0, abs=1e-10)
        assert np.mean(normalized[:, 1]) == pytest.approx(0.0, abs=1e-10)

    def test_matrix_1d(self):
        """1D 数组（自动 reshape 为 2D）。"""
        values = np.array([1, 2, 3, 4, 5])
        normalized, params = normalize_feature_matrix(values, method="minmax")

        # 1D 数组会被 reshape 为 (n, 1)
        assert normalized.shape[0] == values.shape[0]
        assert len(params) == 1

    def test_matrix_no_clip(self):
        """不截断。"""
        matrix = np.array([[1, 100], [2, 200], [3, 300]])
        normalized, _ = normalize_feature_matrix(matrix, method="minmax", clip=False)

        # 如果不截断，可能会有超出 [0, 1] 的值
        # 这里测试不报错即可
        assert normalized.shape == matrix.shape
