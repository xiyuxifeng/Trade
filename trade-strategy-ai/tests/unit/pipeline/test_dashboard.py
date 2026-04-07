from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, UTC

import pytest

from src.pipeline.dashboard_models import DashboardStats, EntityStats, QualityMetrics, DashboardReport
from src.pipeline.dashboard_service import AlertManager, QualityAnalyzer


# =============================================================================
# dashboard_models tests
# =============================================================================


def test_entity_stats_defaults():
    """EntityStats 默认值"""
    stats = EntityStats()
    assert stats.total == 0
    assert stats.today_new == 0
    assert stats.last_crawled_at is None
    assert stats.freshness_hours is None


def test_entity_stats_freshness_calculation():
    """EntityStats 的新鲜度小时数计算"""
    stats = EntityStats(
        total=100,
        today_new=5,
        last_crawled_at=datetime.now(UTC) - timedelta(hours=6),
        freshness_hours=6.0,
    )
    assert stats.freshness_hours == 6.0
    assert stats.total == 100
    assert stats.today_new == 5


def test_dashboard_stats_defaults():
    """DashboardStats 默认值"""
    stats = DashboardStats()
    assert stats.articles.total == 0
    assert stats.trades.total == 0
    assert stats.market_data.total == 0
    assert stats.generated_at is None


def test_quality_metrics_defaults():
    """QualityMetrics 默认值"""
    m = QualityMetrics()
    assert m.total_issues == 0
    assert m.by_severity == {}
    assert m.by_code == {}
    assert m.article_dup_count == 0


def test_dashboard_report_defaults():
    """DashboardReport 默认值"""
    report = DashboardReport()
    assert report.stats.articles.total == 0
    assert report.quality.total_issues == 0
    assert report.alerts == []


# =============================================================================
# AlertManager tests
# =============================================================================


def test_no_alert_when_fresh():
    """数据新鲜时无告警"""
    stats = DashboardStats(
        articles=EntityStats(freshness_hours=2.0),
        trades=EntityStats(freshness_hours=1.0),
        market_data=EntityStats(freshness_hours=3.0),
    )
    quality = QualityMetrics(total_issues=0)
    am = AlertManager(freshness_threshold_hours=24.0, anomaly_rate_threshold=5.0)
    alerts = am.check(stats, quality)
    assert len(alerts) == 0


def test_alert_when_stale():
    """数据过期时触发告警"""
    stats = DashboardStats(
        articles=EntityStats(freshness_hours=30.0),
        trades=EntityStats(freshness_hours=1.0),
        market_data=EntityStats(freshness_hours=1.0),
    )
    quality = QualityMetrics(total_issues=0)
    am = AlertManager(freshness_threshold_hours=24.0, anomaly_rate_threshold=5.0)
    alerts = am.check(stats, quality)
    assert len(alerts) == 1
    assert "articles" in alerts[0].message
    assert alerts[0].level == "warning"


def test_critical_alert_when_anomaly_rate_high():
    """异常率超阈值时触发 critical 告警"""
    stats = DashboardStats(
        articles=EntityStats(total=100),
        trades=EntityStats(total=0),
        market_data=EntityStats(total=0),
    )
    quality = QualityMetrics(total_issues=10)  # 10% 异常率
    am = AlertManager(freshness_threshold_hours=24.0, anomaly_rate_threshold=5.0)
    alerts = am.check(stats, quality)
    assert len(alerts) == 1
    assert alerts[0].level == "critical"
    assert "异常率" in alerts[0].message


def test_no_alert_when_no_issues():
    """无异常时即使异常率计算也不告警"""
    stats = DashboardStats(
        articles=EntityStats(total=100),
        trades=EntityStats(total=0),
        market_data=EntityStats(total=0),
    )
    quality = QualityMetrics(total_issues=0)
    am = AlertManager(freshness_threshold_hours=24.0, anomaly_rate_threshold=5.0)
    alerts = am.check(stats, quality)
    assert len(alerts) == 0


# =============================================================================
# QualityAnalyzer tests
# =============================================================================


def test_quality_analyzer_empty_dir():
    """空目录返回零值"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path
        analyzer = QualityAnalyzer(Path(tmpdir))
        result = analyzer.analyze()
        assert result.total_issues == 0
        assert result.by_severity == {}  # 空目录不初始化 severity 计数


def test_quality_analyzer_parses_report():
    """正确解析 JSONL 报告"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path
        report_dir = Path(tmpdir)
        report_file = report_dir / "anomaly_report_20260407_120000.jsonl"
        report_file.write_text(
            json.dumps({"code": "article.field.missing", "severity": "error", "message": "title missing", "field_name": "title"}) + "\n"
            + json.dumps({"code": "article.duplicate.hash", "severity": "warning", "message": "dup", "field_name": None}) + "\n",
            encoding="utf-8",
        )
        analyzer = QualityAnalyzer(report_dir, max_details=10)
        result = analyzer.analyze()
        assert result.total_issues == 2
        assert result.by_severity["error"] == 1
        assert result.by_severity["warning"] == 1
        assert result.article_missing_count == 1
        assert result.article_dup_count == 1
        assert len(result.anomaly_details) == 2


def test_quality_analyzer_picks_latest_report():
    """选择最新的 JSONL 报告"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path
        report_dir = Path(tmpdir)
        # 旧报告
        old_file = report_dir / "anomaly_report_20260406_120000.jsonl"
        old_file.write_text(json.dumps({"code": "old", "severity": "info", "message": "old issue"}) + "\n", encoding="utf-8")
        # 新报告
        new_file = report_dir / "anomaly_report_20260407_120000.jsonl"
        new_file.write_text(json.dumps({"code": "new", "severity": "error", "message": "new issue"}) + "\n", encoding="utf-8")

        analyzer = QualityAnalyzer(report_dir, max_details=10)
        result = analyzer.analyze()
        assert result.total_issues == 1
        assert result.anomaly_details[0]["code"] == "new"


def test_quality_analyzer_max_details_limit():
    """限制最大异常详情数量"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path
        report_dir = Path(tmpdir)
        report_file = report_dir / "anomaly_report_20260407_120000.jsonl"
        lines = [json.dumps({"code": f"issue_{i}", "severity": "info", "message": f"issue {i}", "field_name": None}) for i in range(30)]
        report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        analyzer = QualityAnalyzer(report_dir, max_details=5)
        result = analyzer.analyze()
        assert result.total_issues == 30
        assert len(result.anomaly_details) == 5