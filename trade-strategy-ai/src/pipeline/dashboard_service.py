from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.blog_article import BlogArticle
from src.models.market_data import MarketData
from src.models.trade_log import TradeLog
from .dashboard_models import DashboardReport, DashboardStats, EntityStats, QualityMetrics, QualityTrend


@dataclass
class AlertEvent:
    """告警事件"""
    level: str  # info / warning / critical
    message: str


class StatsCollector:
    """从 PostgreSQL 收集基础统计信息"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def collect(self) -> DashboardStats:
        """收集所有数据类型的统计"""
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        stats = DashboardStats(
            articles=await self._collect_entity_stats(BlogArticle, today_start),
            trades=await self._collect_entity_stats(TradeLog, today_start),
            market_data=await self._collect_entity_stats(MarketData, today_start),
            generated_at=datetime.now(UTC),
        )
        return stats

    async def _collect_entity_stats(
        self, model: type[BlogArticle | TradeLog | MarketData], today_start: datetime
    ) -> EntityStats:
        # 总数
        total_result = await self.session.execute(select(func.count(model.id)))
        total = total_result.scalar() or 0

        # 今日新增
        crawled_col = getattr(model, "crawled_at", None) or getattr(model, "executed_at", None) or getattr(model, "traded_at", None)
        if crawled_col is None:
            return EntityStats(total=total, today_new=0)

        today_query = select(func.count(model.id)).where(crawled_col >= today_start)
        today_result = await self.session.execute(today_query)
        today_new = today_result.scalar() or 0

        # 最后入库时间
        last_query = select(func.max(crawled_col))
        last_result = await self.session.execute(last_query)
        last_crawled_at = last_result.scalar()

        # 计算新鲜度
        freshness_hours = None
        if last_crawled_at:
            freshness_hours = (datetime.now(UTC) - last_crawled_at).total_seconds() / 3600

        return EntityStats(
            total=total,
            today_new=today_new,
            last_crawled_at=last_crawled_at,
            freshness_hours=freshness_hours,
        )


class QualityAnalyzer:
    """从 JSONL 报告分析数据质量"""

    def __init__(self, report_dir: Path, max_details: int = 20):
        self.report_dir = report_dir
        self.max_details = max_details

    def analyze(self) -> QualityMetrics:
        """分析最新的 anomaly 报告"""
        report_files = sorted(self.report_dir.glob("anomaly_report_*.jsonl"))
        if not report_files:
            return QualityMetrics(generated_at=datetime.now(UTC))

        latest_report = report_files[-1]
        return self._parse_report(latest_report)

    def _parse_report(self, report_path: Path) -> QualityMetrics:
        issues: list[dict[str, Any]] = []
        by_severity: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
        by_code: dict[str, int] = {}

        with report_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                issue = json.loads(line)
                issues.append(issue)

                severity = issue.get("severity", "info")
                if severity in by_severity:
                    by_severity[severity] += 1

                code = issue.get("code", "unknown")
                by_code[code] = by_code.get(code, 0) + 1

        # 统计各类问题
        article_dup = sum(1 for i in issues if "article.duplicate" in i.get("code", ""))
        article_missing = sum(1 for i in issues if i.get("code", "").startswith("article.field"))
        market_missing = sum(1 for i in issues if i.get("code", "").startswith("market.field"))
        trade_missing = sum(1 for i in issues if i.get("code", "").startswith("trade.field"))

        return QualityMetrics(
            total_issues=len(issues),
            by_severity=by_severity,
            by_code=by_code,
            article_dup_count=article_dup,
            article_missing_count=article_missing,
            market_missing_count=market_missing,
            trade_missing_count=trade_missing,
            anomaly_details=issues[: self.max_details],
            generated_at=datetime.now(UTC),
        )


class QualityTrendAnalyzer:
    """从历史 anomaly 报告分析质量趋势。"""

    def __init__(self, report_dir: Path, days: int = 7):
        self.report_dir = report_dir
        self.days = days

    def analyze_trend(self) -> "QualityTrend":
        """返回最近 N 天的质量趋势。"""
        report_files = sorted(self.report_dir.glob("anomaly_report_*.jsonl"))

        # 无报告文件时返回空趋势
        if not report_files:
            return QualityTrend(
                days=[],
                issue_counts=[],
                anomaly_rates=[],
                completeness_rates=[],
            )

        today = datetime.now(UTC).date()
        date_to_issues: dict[str, list[dict]] = {}

        # 初始化最近 N 天
        days_list = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(self.days - 1, -1, -1)]
        for d in days_list:
            date_to_issues[d] = []

        # 解析所有报告文件，按日期分组
        for report_file in report_files:
            date_str = report_file.stem.split("_")[-1]  # anomaly_report_YYYY-MM-DD
            if date_str not in date_to_issues:
                continue
            with report_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        issue = json.loads(line)
                        date_to_issues[date_str].append(issue)
                    except json.JSONDecodeError:
                        continue

        issue_counts = [len(date_to_issues[d]) for d in days_list]
        anomaly_rates = []  # 暂不支持（需知道每日总记录数）

        return QualityTrend(
            days=days_list,
            issue_counts=issue_counts,
            anomaly_rates=anomaly_rates,
            completeness_rates=[],  # 暂不支持
        )


class AlertManager:
    """告警判断逻辑"""

    def __init__(
        self,
        freshness_threshold_hours: float = 24.0,
        anomaly_rate_threshold: float = 5.0,
    ):
        self.freshness_threshold_hours = freshness_threshold_hours
        self.anomaly_rate_threshold = anomaly_rate_threshold

    def check(self, stats: DashboardStats, quality: QualityMetrics) -> list[AlertEvent]:
        alerts: list[AlertEvent] = []

        # 检查新鲜度
        for entity_name, entity_stats in [
            ("articles", stats.articles),
            ("trades", stats.trades),
            ("market_data", stats.market_data),
        ]:
            if entity_stats.freshness_hours is not None and entity_stats.freshness_hours > self.freshness_threshold_hours:
                alerts.append(
                    AlertEvent(
                        level="warning",
                        message=f"{entity_name}: 数据超过 {entity_stats.freshness_hours:.1f} 小时未更新",
                    )
                )

        # 检查异常率
        total_records = stats.articles.total + stats.trades.total + stats.market_data.total
        if total_records > 0 and quality.total_issues > 0:
            anomaly_rate = (quality.total_issues / total_records) * 100
            if anomaly_rate > self.anomaly_rate_threshold:
                alerts.append(
                    AlertEvent(
                        level="critical",
                        message=f"异常率 {anomaly_rate:.1f}% 超过阈值 {self.anomaly_rate_threshold}%",
                    )
                )

        return alerts


class DashboardService:
    """Dashboard 核心服务，编排各组件"""

    def __init__(
        self,
        session: AsyncSession,
        report_dir: Path,
        freshness_threshold_hours: float = 24.0,
        anomaly_rate_threshold: float = 5.0,
        max_anomaly_details: int = 20,
    ):
        self.stats_collector = StatsCollector(session)
        self.quality_analyzer = QualityAnalyzer(report_dir, max_anomaly_details)
        self.alert_manager = AlertManager(freshness_threshold_hours, anomaly_rate_threshold)

    async def build_report(self) -> DashboardReport:
        stats = await self.stats_collector.collect()
        quality = self.quality_analyzer.analyze()
        alerts = self.alert_manager.check(stats, quality)

        # 将 AlertEvent 转换为字符串格式
        alert_messages = [f"[{alert.level.upper()}] {alert.message}" for alert in alerts]

        return DashboardReport(
            stats=stats,
            quality=quality,
            alerts=alert_messages,
            generated_at=datetime.now(UTC),
        )
