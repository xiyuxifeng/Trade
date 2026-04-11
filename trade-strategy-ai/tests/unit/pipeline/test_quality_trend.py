"""Tests for QualityTrendAnalyzer (P1-026)."""

from __future__ import annotations

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, UTC

sys.path.insert(0, "src")

from src.pipeline.dashboard_service import QualityTrendAnalyzer
from src.pipeline.dashboard_models import DataSourceFreshness


def test_quality_trend_analyzer_no_reports(tmp_path):
    """无报告文件时返回空趋势。"""
    analyzer = QualityTrendAnalyzer(report_dir=tmp_path, days=7)
    trend = analyzer.analyze_trend()

    assert trend.days == []
    assert trend.issue_counts == []
    assert trend.anomaly_rates == []


def test_quality_trend_analyzer_parses_jsonl(tmp_path):
    """能正确解析 JSONL 格式的问题报告。"""
    from datetime import date

    # 创建测试报告，使用今天日期确保能被 analyzer 识别
    today_str = date.today().strftime("%Y-%m-%d")
    report_file = tmp_path / f"anomaly_report_{today_str}.jsonl"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({"code": "test", "severity": "error"}) + "\n")
        f.write(json.dumps({"code": "test2", "severity": "warning"}) + "\n")

    analyzer = QualityTrendAnalyzer(report_dir=tmp_path, days=7)
    trend = analyzer.analyze_trend()

    assert len(trend.issue_counts) > 0
    # 找到今天的索引
    today_index = trend.days.index(today_str)
    assert trend.issue_counts[today_index] == 2


def test_source_freshness_model():
    """DataSourceFreshness 模型正确。"""
    stale = DataSourceFreshness(
        source="akshare",
        entity_type="market",
        last_updated=datetime.now(UTC) - timedelta(hours=48),
        freshness_hours=48.0,
        is_stale=True,
    )

    assert stale.is_stale is True
    assert stale.freshness_hours > 24.0
    assert stale.source == "akshare"


def test_source_freshness_not_stale():
    """未超过阈值的数据源不是 stale。"""
    fresh = DataSourceFreshness(
        source="akshare",
        entity_type="market",
        last_updated=datetime.now(UTC) - timedelta(hours=2),
        freshness_hours=2.0,
        is_stale=False,
    )

    assert fresh.is_stale is False


def test_calculate_hhi():
    """HHI 计算正确。"""
    # 3 个标的，数量分别为 50, 30, 20 → 比例 0.5, 0.3, 0.2
    shares = [0.5, 0.3, 0.2]
    hhi = sum(s ** 2 for s in shares)
    assert abs(hhi - 0.38) < 0.01

    # 完全分散：4个标的各 25%
    shares2 = [0.25] * 4
    hhi2 = sum(s ** 2 for s in shares2)
    assert abs(hhi2 - 0.25) < 0.01


def test_trader_stats_model():
    """TraderStats 模型正确。"""
    from src.pipeline.dashboard_models import TraderStats

    stats = TraderStats(
        trader_id="acc1",
        total_trades=100,
        trades_today=5,
        unique_symbols=3,
        hhi=0.38,
        buy_ratio=0.6,
        avg_holding_minutes=None,
        pnl_positive_ratio=None,
        alerts=["买入比例偏高(60%)，注意风格漂移"],
    )

    assert stats.trader_id == "acc1"
    assert stats.hhi == 0.38
    assert len(stats.alerts) == 1