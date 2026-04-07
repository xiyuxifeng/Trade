"""Tests for QualityTrendAnalyzer (P1-026)."""

from __future__ import annotations

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

from src.pipeline.dashboard_service import QualityTrendAnalyzer


def test_quality_trend_analyzer_no_reports(tmp_path):
    """无报告文件时返回空趋势。"""
    analyzer = QualityTrendAnalyzer(report_dir=tmp_path, days=7)
    trend = analyzer.analyze_trend()

    assert trend.days == []
    assert trend.issue_counts == []
    assert trend.anomaly_rates == []


def test_quality_trend_analyzer_parses_jsonl(tmp_path):
    """能正确解析 JSONL 格式的问题报告。"""
    # 创建测试报告
    report_file = tmp_path / "anomaly_report_2026-04-07.jsonl"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({"code": "test", "severity": "error"}) + "\n")
        f.write(json.dumps({"code": "test2", "severity": "warning"}) + "\n")

    analyzer = QualityTrendAnalyzer(report_dir=tmp_path, days=7)
    trend = analyzer.analyze_trend()

    assert len(trend.issue_counts) > 0
    assert trend.issue_counts[-1] == 2