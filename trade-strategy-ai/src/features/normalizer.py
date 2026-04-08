"""
特征归一化模块 — P2-011。

提供多种特征归一化算法：
  - Z-Score 标准化
  - Min-Max 归一化
  - Robust Z-Score（使用中位数和 MAD）
  - 截断归一化（Outlier clipping）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class NormalizationParams:
    """归一化参数。"""
    # Z-Score 参数
    mean: float | None = None
    std: float | None = None
    # Min-Max 参数
    min_val: float | None = None
    max_val: float | None = None
    # Robust 参数
    median: float | None = None
    mad: float | None = None  # Median Absolute Deviation
    # 截断参数
    lower_clip: float | None = None
    upper_clip: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class FeatureNormalizer:
    """特征归一化器。

    支持多种归一化方法，可选择是否进行截断处理。
    """

    def __init__(self, method: str = "zscore") -> None:
        """初始化归一化器。

        Args:
            method: 归一化方法，"zscore"、"minmax"、"robust"
        """
        valid_methods = ["zscore", "minmax", "robust"]
        if method not in valid_methods:
            raise ValueError(f"method must be one of {valid_methods}")
        self.method = method
        self.params: NormalizationParams = NormalizationParams()

    def fit(self, values: np.ndarray) -> "FeatureNormalizer":
        """拟合归一化参数。

        Args:
            values: 特征值数组

        Returns:
            self
        """
        if self.method == "zscore":
            self.params.mean = float(np.mean(values))
            self.params.std = float(np.std(values, ddof=0))
        elif self.method == "minmax":
            self.params.min_val = float(np.min(values))
            self.params.max_val = float(np.max(values))
        elif self.method == "robust":
            self.params.median = float(np.median(values))
            mad = np.median(np.abs(values - self.params.median))
            self.params.mad = float(mad) if mad > 0 else 1.0

        return self

    def transform(self, values: np.ndarray, clip: bool = True) -> np.ndarray:
        """应用归一化。

        Args:
            values: 特征值数组
            clip: 是否进行截断（3σ 或 1.5*IQR）

        Returns:
            归一化后的数组
        """
        if self.method == "zscore":
            return self._zscore_transform(values, clip=clip)
        elif self.method == "minmax":
            return self._minmax_transform(values, clip=clip)
        elif self.method == "robust":
            return self._robust_transform(values, clip=clip)
        return values

    def fit_transform(self, values: np.ndarray, clip: bool = True) -> np.ndarray:
        """拟合并应用归一化。

        Args:
            values: 特征值数组
            clip: 是否进行截断

        Returns:
            归一化后的数组
        """
        return self.fit(values).transform(values, clip=clip)

    def _zscore_transform(self, values: np.ndarray, clip: bool) -> np.ndarray:
        """Z-Score 标准化。"""
        if self.params.std is None or self.params.std == 0:
            return np.zeros_like(values)

        result = (values - self.params.mean) / self.params.std

        if clip:
            # 截断到 ±3σ
            lower = -3.0
            upper = 3.0
            result = np.clip(result, lower, upper)

        return result

    def _minmax_transform(self, values: np.ndarray, clip: bool) -> np.ndarray:
        """Min-Max 归一化。"""
        if self.params.min_val is None or self.params.max_val is None:
            return np.zeros_like(values)

        range_val = self.params.max_val - self.params.min_val
        if range_val == 0:
            return np.full_like(values, 0.5)

        result = (values - self.params.min_val) / range_val

        if clip:
            result = np.clip(result, 0.0, 1.0)

        return result

    def _robust_transform(self, values: np.ndarray, clip: bool) -> np.ndarray:
        """Robust Z-Score（使用中位数和 MAD）。"""
        if self.params.median is None or self.params.mad is None or self.params.mad == 0:
            return np.zeros_like(values)

        result = (values - self.params.median) / (1.4826 * self.params.mad)

        if clip:
            # 截断到 ±3σ
            result = np.clip(result, -3.0, 3.0)

        return result

    def inverse_transform(self, values: np.ndarray) -> np.ndarray:
        """反归一化。

        Args:
            values: 归一化后的数组

        Returns:
            原始尺度的数组
        """
        if self.method == "zscore":
            if self.params.std is None or self.params.std == 0:
                return np.full_like(values, self.params.mean or 0.0)
            return values * self.params.std + self.params.mean
        elif self.method == "minmax":
            if self.params.min_val is None or self.params.max_val is None:
                return np.full_like(values, self.params.min_val or 0.0)
            range_val = self.params.max_val - self.params.min_val
            return values * range_val + self.params.min_val
        elif self.method == "robust":
            if self.params.median is None or self.params.mad is None:
                return np.full_like(values, self.params.median or 0.0)
            return values * (1.4826 * self.params.mad) + self.params.median
        return values


def normalize_features(
    feature_dict: dict[str, float | None],
    method: str = "zscore",
    clip: bool = True,
) -> dict[str, float]:
    """对特征字典进行归一化。

    快捷函数，对单个样本的特征进行归一化。

    Args:
        feature_dict: 特征名 -> 特征值的字典
        method: 归一化方法
        clip: 是否截断

    Returns:
        归一化后的特征字典
    """
    # 过滤 None 值
    valid_features = {k: v for k, v in feature_dict.items() if v is not None}
    if not valid_features:
        return {}

    values = np.array(list(valid_features.values()), dtype=np.float64)
    normalizer = FeatureNormalizer(method=method)
    normalized = normalizer.fit_transform(values, clip=clip)

    result = dict(zip(valid_features.keys(), normalized))
    return result


def normalize_feature_matrix(
    feature_matrix: np.ndarray,
    method: str = "zscore",
    clip: bool = True,
) -> tuple[np.ndarray, list[NormalizationParams]]:
    """对特征矩阵进行归一化。

    Args:
        feature_matrix: 特征矩阵 (n_samples, n_features)
        method: 归一化方法
        clip: 是否截断

    Returns:
        (normalized_matrix, params_list)
    """
    if feature_matrix.ndim == 1:
        feature_matrix = feature_matrix.reshape(-1, 1)

    n_features = feature_matrix.shape[1]
    result = np.empty_like(feature_matrix, dtype=np.float64)
    params_list: list[NormalizationParams] = []

    for i in range(n_features):
        normalizer = FeatureNormalizer(method=method)
        col = feature_matrix[:, i]
        result[:, i] = normalizer.fit_transform(col, clip=clip)
        params_list.append(normalizer.params)

    return result, params_list
