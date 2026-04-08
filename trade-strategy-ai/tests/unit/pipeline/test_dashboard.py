from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, UTC

import pytest

from src.pipeline.dashboard_models import DashboardStats, EntityStats, QualityMetrics, DashboardReport
from src.pipeline.dashboard_service import QualityAnalyzer
from src.alerting.models import AlertLevel, AlertRule
from src.alerting.manager import AlertManager as AlertingManager


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
# AlertingManager tests
# =============================================================================


def _make_rules(freshness_threshold: float = 24.0, anomaly_threshold: float = 5.0) -> list[AlertRule]:
    """构建与 DashboardService 相同的告警规则。"""
    return [
        AlertRule(
            name="articles_data_stale",
            condition=lambda stats, _: (
                stats.articles.freshness_hours is not None
                and stats.articles.freshness_hours > freshness_threshold
            ),
            level=AlertLevel.WARNING,
            title="文章数据过期",
            message_template=f"文章数据超过 {freshness_threshold:.1f} 小时未更新",
            cooldown_seconds=3600,
            tags=["dashboard", "freshness"],
        ),
        AlertRule(
            name="trades_data_stale",
            condition=lambda stats, _: (
                stats.trades.freshness_hours is not None
                and stats.trades.freshness_hours > freshness_threshold
            ),
            level=AlertLevel.WARNING,
            title="交易数据过期",
            message_template=f"交易数据超过 {freshness_threshold:.1f} 小时未更新",
            cooldown_seconds=3600,
            tags=["dashboard", "freshness"],
        ),
        AlertRule(
            name="market_data_stale",
            condition=lambda stats, _: (
                stats.market_data.freshness_hours is not None
                and stats.market_data.freshness_hours > freshness_threshold
            ),
            level=AlertLevel.WARNING,
            title="市场数据过期",
            message_template=f"市场数据超过 {freshness_threshold:.1f} 小时未更新",
            cooldown_seconds=3600,
            tags=["dashboard", "freshness"],
        ),
        AlertRule(
            name="high_anomaly_rate",
            condition=lambda stats, quality: (
                _calc_anomaly_rate(stats, quality) > anomaly_threshold
            ),
            level=AlertLevel.CRITICAL,
            title="数据异常率过高",
            message_template=f"数据异常率 {{anomaly_rate:.1f}}% 超过阈值 {anomaly_threshold}%",
            cooldown_seconds=1800,
            tags=["dashboard", "quality"],
        ),
    ]


def _calc_anomaly_rate(stats: DashboardStats, quality: QualityMetrics) -> float:
    """计算异常率。"""
    total = stats.articles.total + stats.trades.total + stats.market_data.total
    if total <= 0:
        return 0.0
    return (quality.total_issues / total) * 100


@pytest.mark.asyncio
async def test_no_alert_when_fresh():
    """数据新鲜时无告警"""
    stats = DashboardStats(
        articles=EntityStats(freshness_hours=2.0),
        trades=EntityStats(freshness_hours=1.0),
        market_data=EntityStats(freshness_hours=3.0),
    )
    quality = QualityMetrics(total_issues=0)
    am = AlertingManager(rules=_make_rules(24.0, 5.0), notifiers=[])
    alerts = await am.evaluate(stats, quality)
    assert len(alerts) == 0


@pytest.mark.asyncio
async def test_alert_when_stale():
    """数据过期时触发告警"""
    stats = DashboardStats(
        articles=EntityStats(freshness_hours=30.0),
        trades=EntityStats(freshness_hours=1.0),
        market_data=EntityStats(freshness_hours=1.0),
    )
    quality = QualityMetrics(total_issues=0)
    am = AlertingManager(rules=_make_rules(24.0, 5.0), notifiers=[])
    alerts = await am.evaluate(stats, quality)
    assert len(alerts) == 1
    assert "文章" in alerts[0].message
    assert alerts[0].level == AlertLevel.WARNING


@pytest.mark.asyncio
async def test_critical_alert_when_anomaly_rate_high():
    """异常率超阈值时触发 critical 告警"""
    stats = DashboardStats(
        articles=EntityStats(total=100),
        trades=EntityStats(total=0),
        market_data=EntityStats(total=0),
    )
    quality = QualityMetrics(total_issues=10)  # 10% 异常率
    am = AlertingManager(rules=_make_rules(24.0, 5.0), notifiers=[])
    alerts = await am.evaluate(stats, quality)
    assert len(alerts) == 1
    assert alerts[0].level == AlertLevel.CRITICAL
    assert "异常率" in alerts[0].message


@pytest.mark.asyncio
async def test_no_alert_when_no_issues():
    """无异常时即使异常率计算也不告警"""
    stats = DashboardStats(
        articles=EntityStats(total=100),
        trades=EntityStats(total=0),
        market_data=EntityStats(total=0),
    )
    quality = QualityMetrics(total_issues=0)
    am = AlertingManager(rules=_make_rules(24.0, 5.0), notifiers=[])
    alerts = await am.evaluate(stats, quality)
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