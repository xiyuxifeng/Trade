"""
数据质量模块 — P2-019。

提供缺失值处理和异常检测功能：
  - 缺失值检测与填充
  - 异常值检测（IQR、Z-Score）
  - 数据质量报告
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class MissingValueReport:
    """缺失值报告。"""
    # 字段名 -> 缺失数量
    missing_counts: dict[str, int] = field(default_factory=dict)
    # 字段名 -> 缺失比例
    missing_ratios: dict[str, float] = field(default_factory=dict)
    # 总记录数
    total_records: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_counts": self.missing_counts,
            "missing_ratios": self.missing_ratios,
            "total_records": self.total_records,
        }


@dataclass
class OutlierReport:
    """异常值报告。"""
    # 检测方法
    method: str
    # 字段名 -> 异常值数量
    outlier_counts: dict[str, int] = field(default_factory=dict)
    # 字段名 -> 异常值索引列表
    outlier_indices: dict[str, list[int]] = field(default_factory=dict)
    # 总记录数
    total_records: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "outlier_counts": self.outlier_counts,
            "total_records": self.total_records,
        }


# ---------------------------------------------------------------------------
# 缺失值检测
# ---------------------------------------------------------------------------

def detect_missing_values(data: dict[str, list[Any] | np.ndarray]) -> MissingValueReport:
    """检测缺失值。

    Args:
        data: 字典，键为字段名，值为数据数组

    Returns:
        MissingValueReport
    """
    report = MissingValueReport()

    # 确定记录数
    lengths = [len(v) for v in data.values() if hasattr(v, "__len__")]
    report.total_records = lengths[0] if lengths else 0

    for field_name, values in data.items():
        arr = np.array(values) if not isinstance(values, np.ndarray) else values

        # 检测缺失值（None, NaN, 或空值）
        is_missing = np.array([
            v is None or (isinstance(v, float) and np.isnan(v)) or v == ""
            for v in arr
        ])
        missing_count = int(np.sum(is_missing))
        report.missing_counts[field_name] = missing_count
        report.missing_ratios[field_name] = missing_count / len(arr) if len(arr) > 0 else 0.0

    return report


def fill_missing_values(
    data: dict[str, list[Any] | np.ndarray],
    strategy: str = "mean",
    fill_value: float = 0.0,
) -> dict[str, np.ndarray]:
    """填充缺失值。

    Args:
        data: 字典，键为字段名，值为数据数组
        strategy: 填充策略，"mean"、"median"、"zero"、"forward"、"backward"
        fill_value: 当 strategy="constant" 时使用的填充值

    Returns:
        填充后的数据字典
    """
    result = {}

    for field_name, values in data.items():
        arr = np.array(values, dtype=np.float64) if not isinstance(values, np.ndarray) else values.copy()

        if strategy == "mean":
            valid = arr[~np.isnan(arr)]
            fill = float(np.mean(valid)) if len(valid) > 0 else 0.0
            arr[np.isnan(arr)] = fill
        elif strategy == "median":
            valid = arr[~np.isnan(arr)]
            fill = float(np.median(valid)) if len(valid) > 0 else 0.0
            arr[np.isnan(arr)] = fill
        elif strategy == "zero":
            arr[np.isnan(arr)] = 0.0
        elif strategy == "forward":
            # 前向填充
            last_valid = fill_value
            for i in range(len(arr)):
                if np.isnan(arr[i]):
                    arr[i] = last_valid
                else:
                    last_valid = arr[i]
        elif strategy == "backward":
            # 后向填充
            next_valid = fill_value
            for i in range(len(arr) - 1, -1, -1):
                if np.isnan(arr[i]):
                    arr[i] = next_valid
                else:
                    next_valid = arr[i]
        elif strategy == "constant":
            arr[np.isnan(arr)] = fill_value

        result[field_name] = arr

    return result


# ---------------------------------------------------------------------------
# 异常值检测
# ---------------------------------------------------------------------------

def detect_outliers_iqr(
    data: dict[str, list[Any] | np.ndarray],
    multiplier: float = 1.5,
) -> OutlierReport:
    """使用 IQR（四分位距）检测异常值。

    Args:
        data: 字典，键为字段名，值为数据数组
        multiplier: IQR 乘数（默认 1.5）

    Returns:
        OutlierReport
    """
    report = OutlierReport(method="iqr")
    lengths = [len(v) for v in data.values() if hasattr(v, "__len__")]
    report.total_records = lengths[0] if lengths else 0

    for field_name, values in data.items():
        arr = np.array(values, dtype=np.float64) if not isinstance(values, np.ndarray) else values

        # 跳过非数值类型
        if not np.issubdtype(arr.dtype, np.number):
            continue

        valid = arr[~np.isnan(arr)]
        if len(valid) < 4:
            continue

        q1 = np.percentile(valid, 25)
        q3 = np.percentile(valid, 75)
        iqr = q3 - q1

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        outlier_mask = (arr < lower_bound) | (arr > upper_bound)
        outlier_indices = np.where(outlier_mask)[0].tolist()

        report.outlier_counts[field_name] = len(outlier_indices)
        report.outlier_indices[field_name] = outlier_indices

    return report


def detect_outliers_zscore(
    data: dict[str, list[Any] | np.ndarray],
    threshold: float = 3.0,
) -> OutlierReport:
    """使用 Z-Score 检测异常值。

    Args:
        data: 字典，键为字段名，值为数据数组
        threshold: Z-Score 阈值（默认 3.0）

    Returns:
        OutlierReport
    """
    report = OutlierReport(method="zscore")
    lengths = [len(v) for v in data.values() if hasattr(v, "__len__")]
    report.total_records = lengths[0] if lengths else 0

    for field_name, values in data.items():
        arr = np.array(values, dtype=np.float64) if not isinstance(values, np.ndarray) else values

        # 跳过非数值类型
        if not np.issubdtype(arr.dtype, np.number):
            continue

        valid = arr[~np.isnan(arr)]
        if len(valid) < 3:
            continue

        mean = np.mean(valid)
        std = np.std(valid, ddof=0)

        if std == 0:
            continue

        z_scores = np.abs((arr - mean) / std)
        outlier_mask = z_scores > threshold
        outlier_indices = np.where(outlier_mask)[0].tolist()

        report.outlier_counts[field_name] = len(outlier_indices)
        report.outlier_indices[field_name] = outlier_indices

    return report


def clip_outliers(
    data: dict[str, list[Any] | np.ndarray],
    method: str = "iqr",
    multiplier: float = 1.5,
    threshold: float = 3.0,
) -> dict[str, np.ndarray]:
    """截断异常值。

    Args:
        data: 字典，键为字段名，值为数据数组
        method: 检测方法，"iqr" 或 "zscore"
        multiplier: IQR 乘数
        threshold: Z-Score 阈值

    Returns:
        截断后的数据字典
    """
    result = {}

    for field_name, values in data.items():
        arr = np.array(values, dtype=np.float64) if not isinstance(values, np.ndarray) else values.copy()

        # 跳过非数值类型
        if not np.issubdtype(arr.dtype, np.number):
            result[field_name] = arr
            continue

        valid = arr[~np.isnan(arr)]
        if len(valid) < 4:
            result[field_name] = arr
            continue

        if method == "iqr":
            q1 = np.percentile(valid, 25)
            q3 = np.percentile(valid, 75)
            iqr = q3 - q1
            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr
        else:  # zscore
            mean = np.mean(valid)
            std = np.std(valid, ddof=0)
            if std == 0:
                result[field_name] = arr
                continue
            lower_bound = mean - threshold * std
            upper_bound = mean + threshold * std

        arr[arr < lower_bound] = lower_bound
        arr[arr > upper_bound] = upper_bound
        result[field_name] = arr

    return result


# ---------------------------------------------------------------------------
# 综合质量报告
# ---------------------------------------------------------------------------

@dataclass
class DataQualityReport:
    """综合数据质量报告。"""
    missing: MissingValueReport
    outliers_iqr: OutlierReport
    outliers_zscore: OutlierReport
    # 数据质量评分（0-100）
    quality_score: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing": self.missing.to_dict(),
            "outliers_iqr": self.outliers_iqr.to_dict(),
            "outliers_zscore": self.outliers_zscore.to_dict(),
            "quality_score": self.quality_score,
        }


def assess_data_quality(
    data: dict[str, list[Any] | np.ndarray],
) -> DataQualityReport:
    """综合评估数据质量。

    Args:
        data: 字典，键为字段名，值为数据数组

    Returns:
        DataQualityReport
    """
    # 缺失值检测
    missing_report = detect_missing_values(data)

    # 异常值检测
    outliers_iqr = detect_outliers_iqr(data)
    outliers_zscore = detect_outliers_zscore(data)

    # 计算质量评分
    score = 100.0

    # 缺失值扣分
    for field_name, ratio in missing_report.missing_ratios.items():
        score -= ratio * 20  # 缺失 100% 扣 20 分

    # IQR 异常值扣分
    total_iqr_outliers = sum(outliers_iqr.outlier_counts.values())
    if missing_report.total_records > 0:
        outlier_ratio = total_iqr_outliers / (missing_report.total_records * len(missing_report.missing_counts))
        score -= outlier_ratio * 15  # 异常值比例扣分

    score = max(0.0, min(100.0, score))

    return DataQualityReport(
        missing=missing_report,
        outliers_iqr=outliers_iqr,
        outliers_zscore=outliers_zscore,
        quality_score=score,
    )
