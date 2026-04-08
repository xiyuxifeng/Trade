"""
数据质量单元测试 — P2-019。
"""

from __future__ import annotations

import numpy as np
import pytest

from src.features.data_quality import (
    DataQualityReport,
    MissingValueReport,
    OutlierReport,
    assess_data_quality,
    clip_outliers,
    detect_missing_values,
    detect_outliers_iqr,
    detect_outliers_zscore,
    fill_missing_values,
)


class TestDetectMissingValues:
    """缺失值检测测试。"""

    def test_detect_missing(self):
        """检测缺失值。"""
        data = {
            "a": [1, 2, None, 4, 5],
            "b": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
        report = detect_missing_values(data)

        assert report.missing_counts["a"] == 1
        assert report.missing_counts["b"] == 0
        assert report.missing_ratios["a"] == pytest.approx(0.2, rel=1e-9)

    def test_detect_nan(self):
        """检测 NaN。"""
        data = {
            "x": [1.0, np.nan, 3.0, 4.0, 5.0],
        }
        report = detect_missing_values(data)

        assert report.missing_counts["x"] == 1

    def test_empty_data(self):
        """空数据。"""
        data = {}
        report = detect_missing_values(data)
        assert report.total_records == 0


class TestFillMissingValues:
    """缺失值填充测试。"""

    def test_fill_mean(self):
        """均值填充。"""
        data = {"a": [1.0, 2.0, np.nan, 4.0]}
        result = fill_missing_values(data, strategy="mean")

        # (1 + 2 + 4) / 3 = 7/3 ≈ 2.333
        assert result["a"][2] == pytest.approx(2.333, abs=0.01)

    def test_fill_median(self):
        """中位数填充。"""
        data = {"a": [1.0, 5.0, np.nan, 3.0]}
        result = fill_missing_values(data, strategy="median")

        assert result["a"][2] == pytest.approx(3.0, abs=0.01)

    def test_fill_zero(self):
        """零填充。"""
        data = {"a": [1.0, 2.0, np.nan, 4.0]}
        result = fill_missing_values(data, strategy="zero")

        assert result["a"][2] == 0.0

    def test_fill_forward(self):
        """前向填充。"""
        data = {"a": [1.0, np.nan, 3.0, 4.0]}
        result = fill_missing_values(data, strategy="forward")

        assert result["a"][1] == 1.0  # 填充为前一个值 1.0
        assert result["a"][2] == 3.0  # 已有值不变

    def test_fill_backward(self):
        """后向填充。"""
        data = {"a": [1.0, 2.0, np.nan, 4.0]}
        result = fill_missing_values(data, strategy="backward")

        assert result["a"][2] == 4.0  # 填充为后一个值 4.0


class TestDetectOutliersIqr:
    """IQR 异常值检测测试。"""

    def test_detect_outliers(self):
        """检测异常值。"""
        data = {
            "x": [1, 2, 3, 4, 5, 100],  # 100 是异常值
        }
        report = detect_outliers_iqr(data)

        assert report.outlier_counts["x"] == 1
        assert 5 in report.outlier_indices["x"]

    def test_no_outliers(self):
        """无异常值。"""
        data = {
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        }
        report = detect_outliers_iqr(data)

        assert report.outlier_counts["x"] == 0


class TestDetectOutliersZscore:
    """Z-Score 异常值检测测试。"""

    def test_detect_outliers(self):
        """检测异常值。"""
        data = {
            "x": [1, 2, 3, 4, 5, 100],  # 100 是异常值
        }
        report = detect_outliers_zscore(data, threshold=2.0)

        assert report.outlier_counts["x"] >= 1

    def test_no_outliers(self):
        """无异常值。"""
        data = {
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        }
        report = detect_outliers_zscore(data, threshold=3.0)

        assert report.outlier_counts["x"] == 0


class TestClipOutliers:
    """异常值截断测试。"""

    def test_clip_iqr(self):
        """IQR 截断。"""
        data = {
            "x": [1, 2, 3, 4, 5, 100],
        }
        result = clip_outliers(data, method="iqr")

        # 异常值应该被截断到边界内
        assert result["x"][-1] <= 100  # 不超过原始值

    def test_clip_zscore(self):
        """Z-Score 截断。"""
        data = {
            "x": [1, 2, 3, 4, 5, 100],
        }
        result = clip_outliers(data, method="zscore", threshold=2.0)

        assert result["x"][-1] <= 100


class TestAssessDataQuality:
    """数据质量评估测试。"""

    def test_quality_score(self):
        """质量评分。"""
        data = {
            "x": [1, 2, 3, 4, 5],
            "y": [1, 2, 3, 4, 100],
        }
        report = assess_data_quality(data)

        assert isinstance(report, DataQualityReport)
        assert 0 <= report.quality_score <= 100

    def test_quality_report_structure(self):
        """报告结构。"""
        data = {
            "x": [1, 2, 3, 4, 5],
        }
        report = assess_data_quality(data)

        assert hasattr(report, "missing")
        assert hasattr(report, "outliers_iqr")
        assert hasattr(report, "outliers_zscore")
        assert hasattr(report, "quality_score")


class TestMissingValueReport:
    """MissingValueReport 测试。"""

    def test_to_dict(self):
        """转换为字典。"""
        report = MissingValueReport()
        report.total_records = 10
        report.missing_counts = {"a": 1, "b": 2}
        report.missing_ratios = {"a": 0.1, "b": 0.2}

        d = report.to_dict()
        assert d["total_records"] == 10
        assert d["missing_counts"]["a"] == 1


class TestOutlierReport:
    """OutlierReport 测试。"""

    def test_to_dict(self):
        """转换为字典。"""
        report = OutlierReport(method="iqr")
        report.total_records = 10
        report.outlier_counts = {"x": 2}
        report.outlier_indices = {"x": [3, 7]}

        d = report.to_dict()
        assert d["method"] == "iqr"
        assert d["outlier_counts"]["x"] == 2
