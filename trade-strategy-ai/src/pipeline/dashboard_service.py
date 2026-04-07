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


class DataSourceFreshnessChecker:
    """检查各数据源新鲜度。"""

    def __init__(self, session: AsyncSession, freshness_threshold_hours: float = 24.0):
        self.session = session
        self.threshold = freshness_threshold_hours

    async def check_all(self) -> list["DataSourceFreshness"]:
        """返回所有数据源的新鲜度。"""
        from .dashboard_models import DataSourceFreshness

        results: list[DataSourceFreshness] = []

        # 检查 BlogArticle 按 source
        article_sources = await self._get_sources(BlogArticle, "crawled_at")
        for source, last_updated in article_sources:
            freshness = self._calc_freshness(last_updated)
            results.append(DataSourceFreshness(
                source=source,
                entity_type="article",
                last_updated=last_updated,
                freshness_hours=freshness,
                is_stale=freshness > self.threshold if freshness is not None else False,
            ))

        # 检查 MarketData 按 source
        market_sources = await self._get_sources(MarketData, "traded_at")
        for source, last_updated in market_sources:
            freshness = self._calc_freshness(last_updated)
            results.append(DataSourceFreshness(
                source=source,
                entity_type="market",
                last_updated=last_updated,
                freshness_hours=freshness,
                is_stale=freshness > self.threshold if freshness is not None else False,
            ))

        return results

    async def _get_sources(self, model, time_col: str):
        """获取某模型按 source 分组的最新时间。"""
        from sqlalchemy import func, select

        time_column = getattr(model, time_col)
        query = (
            select(model.source, func.max(time_column))
            .group_by(model.source)
        )
        result = await self.session.execute(query)
        return result.all()

    def _calc_freshness(self, last_updated: datetime | None) -> float | None:
        """计算新鲜度（小时）。"""
        if last_updated is None:
            return None
        return (datetime.now(UTC) - last_updated).total_seconds() / 3600


class TradeStatsCollector:
    """从 TradeLog 收集交易员级别统计。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def collect_all(self) -> list["TraderStats"]:
        """返回所有交易员的统计。"""
        from .dashboard_models import TraderStats

        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        # 按 account_id 分组统计
        query = (
            select(
                TradeLog.account_id,
                func.count(TradeLog.id).label("total_trades"),
                func.count(TradeLog.id).filter(TradeLog.executed_at >= today_start).label("trades_today"),
            )
            .group_by(TradeLog.account_id)
        )
        result = await self.session.execute(query)
        rows = result.all()

        trader_stats: list[TraderStats] = []
        for row in rows:
            trader_id = row.account_id
            total_trades = row.total_trades
            trades_today = row.trades_today or 0

            # 获取标的多样性
            unique_symbols = await self._get_unique_symbols(trader_id)

            # 获取买卖比例
            buy_ratio = await self._get_buy_ratio(trader_id)

            # 计算 HHI
            hhi = await self._calculate_hhi(trader_id)

            # 生成告警
            alerts = self._generate_alerts(trader_id, buy_ratio, unique_symbols, trades_today)

            trader_stats.append(TraderStats(
                trader_id=trader_id,
                total_trades=total_trades,
                trades_today=trades_today,
                unique_symbols=unique_symbols,
                hhi=hhi,
                buy_ratio=buy_ratio,
                avg_holding_minutes=None,  # 暂不支持（需关联入场/出场）
                pnl_positive_ratio=None,  # 暂不支持（需关联持仓和盈亏）
                alerts=alerts,
            ))

        return trader_stats

    async def _get_unique_symbols(self, trader_id: str) -> int:
        """获取该交易员的唯一标的数。"""
        query = (
            select(func.count(func.distinct(TradeLog.symbol)))
            .where(TradeLog.account_id == trader_id)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _get_buy_ratio(self, trader_id: str) -> float:
        """获取该交易员的买入比例。"""
        total_query = (
            select(func.count(TradeLog.id))
            .where(TradeLog.account_id == trader_id)
        )
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        if total == 0:
            return 0.0

        buy_query = (
            select(func.count(TradeLog.id))
            .where(TradeLog.account_id == trader_id, TradeLog.side == "buy")
        )
        buy_result = await self.session.execute(buy_query)
        buys = buy_result.scalar() or 0

        return buys / total

    async def _calculate_hhi(self, trader_id: str) -> float:
        """计算 HHI（Herfindahl 集中度指数）。"""
        # 获取各标的的交易次数
        query = (
            select(TradeLog.symbol, func.count(TradeLog.id).label("count"))
            .where(TradeLog.account_id == trader_id)
            .group_by(TradeLog.symbol)
        )
        result = await self.session.execute(query)
        rows = result.all()

        total = sum(row.count for row in rows)
        if total == 0:
            return 0.0

        hhi = sum((row.count / total) ** 2 for row in rows)
        return hhi

    def _generate_alerts(self, trader_id: str, buy_ratio: float, unique_symbols: int, trades_today: int) -> list[str]:
        """生成交易员级别告警。"""
        alerts = []

        if buy_ratio > 0.8:
            alerts.append(f"买入比例偏高({buy_ratio:.0%})，注意风格漂移")
        elif buy_ratio < 0.2:
            alerts.append(f"卖出比例偏高({buy_ratio:.0%})，注意风格漂移")

        if unique_symbols == 1 and trades_today >= 3:
            alerts.append(f"仅交易1只标的({trades_today}笔)，集中度过高")

        if trades_today == 0:
            alerts.append("今日无交易")

        return alerts


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

    def check(
        self,
        stats: DashboardStats,
        quality: QualityMetrics,
        quality_trend: "QualityTrend | None" = None,
        source_freshness: list["DataSourceFreshness"] | None = None,
        trader_stats: list["TraderStats"] | None = None,
    ) -> list[AlertEvent]:
        alerts: list[AlertEvent] = []

        # === 原有新鲜度告警（保持不变）===
        for entity_name, entity_stats in [
            ("articles", stats.articles),
            ("trades", stats.trades),
            ("market_data", stats.market_data),
        ]:
            if entity_stats.freshness_hours is not None and entity_stats.freshness_hours > self.freshness_threshold_hours:
                alerts.append(AlertEvent(
                    level="warning",
                    message=f"{entity_name}: 数据超过 {entity_stats.freshness_hours:.1f} 小时未更新",
                ))

        # === 原有异常率告警 ===
        total_records = stats.articles.total + stats.trades.total + stats.market_data.total
        if total_records > 0 and quality.total_issues > 0:
            anomaly_rate = (quality.total_issues / total_records) * 100
            if anomaly_rate > self.anomaly_rate_threshold:
                alerts.append(AlertEvent(
                    level="critical",
                    message=f"异常率 {anomaly_rate:.1f}% 超过阈值 {self.anomaly_rate_threshold}%",
                ))

        # === 异常趋势告警（新增）===
        if quality_trend and len(quality_trend.issue_counts) >= 2:
            if quality_trend.issue_counts[-1] > quality_trend.issue_counts[0] * 1.5:
                alerts.append(AlertEvent(
                    level="warning",
                    message=f"异常率呈上升趋势：{quality_trend.issue_counts[0]} → {quality_trend.issue_counts[-1]}",
                ))

        # === 数据源新鲜度告警（新增）===
        if source_freshness:
            for src in source_freshness:
                if src.is_stale:
                    alerts.append(AlertEvent(
                        level="warning",
                        message=f"数据源 {src.source}({src.entity_type}) 超过 {self.freshness_threshold_hours:.0f}h 未更新",
                    ))

        # === 交易员级别告警（新增）===
        if trader_stats:
            for trader in trader_stats:
                for alert_msg in trader.alerts:
                    alerts.append(AlertEvent(
                        level="info",
                        message=f"交易员 {trader.trader_id}: {alert_msg}",
                    ))

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
        self.quality_trend_analyzer = QualityTrendAnalyzer(report_dir)
        self.source_freshness_checker = DataSourceFreshnessChecker(session, freshness_threshold_hours)
        self.trade_stats_collector = TradeStatsCollector(session)

    async def build_report(self) -> DashboardReport:
        stats = await self.stats_collector.collect()
        quality = self.quality_analyzer.analyze()
        quality_trend = self.quality_trend_analyzer.analyze_trend()
        source_freshness = await self.source_freshness_checker.check_all()
        trader_stats = await self.trade_stats_collector.collect_all()
        alerts = self.alert_manager.check(
            stats, quality,
            quality_trend=quality_trend,
            source_freshness=source_freshness,
            trader_stats=trader_stats,
        )

        alert_messages = [f"[{alert.level.upper()}] {alert.message}" for alert in alerts]

        return DashboardReport(
            stats=stats,
            quality=quality,
            quality_trend=quality_trend,
            source_freshness=source_freshness,
            trader_stats=trader_stats,
            alerts=alert_messages,
            generated_at=datetime.now(UTC),
        )
