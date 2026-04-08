"""预定义告警规则。

提供常用的告警规则定义。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable
from dataclasses import dataclass, field

from src.alerting.models import AlertLevel, AlertRule

if TYPE_CHECKING:
    from src.pipeline.dashboard_models import DashboardStats, QualityMetrics


def _calc_anomaly_rate(stats: "DashboardStats", quality: "QualityMetrics") -> float:
    """计算异常率。"""
    total = stats.articles.total + stats.trades.total + stats.market_data.total
    if total <= 0:
        return 0.0
    return (quality.total_issues / total) * 100


def _calc_buy_ratio(stats: "DashboardStats") -> float | None:
    """计算买入比例。"""
    total = stats.trades.total
    if total <= 0:
        return None
    buys = stats.trades.by_type.get("buy", 0)
    return (buys / total) * 100 if buys else None


# 预定义告警规则
DEFAULT_ALERT_RULES: list[AlertRule] = []


def _init_rules() -> list[AlertRule]:
    """初始化预定义规则。"""
    return [
        AlertRule(
            name="articles_data_stale",
            condition=lambda stats, _: (
                stats.articles.freshness_hours is not None
                and stats.articles.freshness_hours > 24
            ),
            level=AlertLevel.WARNING,
            title="文章数据过期",
            message_template="文章数据超过 {articles_freshness:.1f} 小时未更新",
            cooldown_seconds=3600,  # 1 小时
            tags=["data", "freshness", "articles"],
        ),
        AlertRule(
            name="trades_data_stale",
            condition=lambda stats, _: (
                stats.trades.freshness_hours is not None
                and stats.trades.freshness_hours > 24
            ),
            level=AlertLevel.WARNING,
            title="交易数据过期",
            message_template="交易数据超过 {trades_freshness:.1f} 小时未更新",
            cooldown_seconds=3600,
            tags=["data", "freshness", "trades"],
        ),
        AlertRule(
            name="market_data_stale",
            condition=lambda stats, _: (
                stats.market_data.freshness_hours is not None
                and stats.market_data.freshness_hours > 24
            ),
            level=AlertLevel.WARNING,
            title="市场数据过期",
            message_template="市场数据超过 {market_freshness:.1f} 小时未更新",
            cooldown_seconds=3600,
            tags=["data", "freshness", "market"],
        ),
        AlertRule(
            name="high_anomaly_rate",
            condition=lambda stats, quality: _calc_anomaly_rate(stats, quality) > 5.0,
            level=AlertLevel.CRITICAL,
            title="数据异常率过高",
            message_template="数据异常率 {anomaly_rate:.1f}% 超过阈值 5%",
            cooldown_seconds=1800,  # 30 分钟
            tags=["quality", "anomaly"],
        ),
        AlertRule(
            name="critical_anomaly_rate",
            condition=lambda stats, quality: _calc_anomaly_rate(stats, quality) > 10.0,
            level=AlertLevel.CRITICAL,
            title="数据异常率严重",
            message_template="数据异常率 {anomaly_rate:.1f}% 超过阈值 10%",
            cooldown_seconds=900,  # 15 分钟
            tags=["quality", "anomaly", "critical"],
        ),
        AlertRule(
            name="high_buy_ratio",
            condition=lambda stats, _: (
                (_calc_buy_ratio(stats) or 0) > 80
            ),
            level=AlertLevel.INFO,
            title="买入比例偏高",
            message_template="买入比例 {buy_ratio:.0f}%，注意风格漂移",
            cooldown_seconds=43200,  # 12 小时
            tags=["trader", "behavior"],
        ),
        AlertRule(
            name="high_sell_ratio",
            condition=lambda stats, _: (
                (_calc_buy_ratio(stats) or 0) < 20
            ),
            level=AlertLevel.INFO,
            title="卖出比例偏高",
            message_template="卖出比例 {sell_ratio:.0f}%，注意风格漂移",
            cooldown_seconds=43200,
            tags=["trader", "behavior"],
        ),
        AlertRule(
            name="no_trades_today",
            condition=lambda stats, _: (
                stats.trades.total == 0
            ),
            level=AlertLevel.WARNING,
            title="今日无交易",
            message_template="今日无交易记录",
            cooldown_seconds=86400,  # 24 小时
            tags=["trader", "activity"],
        ),
        AlertRule(
            name="single_symbol_focus",
            condition=lambda stats, _: (
                stats.trades.total > 0 and stats.trades.unique_symbols == 1
            ),
            level=AlertLevel.INFO,
            title="单一标的集中",
            message_template="仅交易 1 只标的，集中度过高",
            cooldown_seconds=43200,
            tags=["trader", "risk"],
        ),
        AlertRule(
            name="article_dup_rate_high",
            condition=lambda _, quality: (
                quality.article_dup_count > 10
            ),
            level=AlertLevel.WARNING,
            title="文章重复率高",
            message_template="文章重复数 {dup_count} 超过阈值",
            cooldown_seconds=3600,
            tags=["quality", "duplicate", "articles"],
        ),
    ]


# 延迟初始化
DEFAULT_ALERT_RULES = _init_rules()


def get_default_rules() -> list[AlertRule]:
    """获取默认告警规则列表。"""
    return list(DEFAULT_ALERT_RULES)


def create_custom_rule(
    name: str,
    condition: Callable[["DashboardStats", "QualityMetrics"], bool],
    level: AlertLevel,
    title: str,
    message_template: str,
    cooldown_seconds: int = 300,
    tags: list[str] | None = None,
) -> AlertRule:
    """创建自定义告警规则。

    Args:
        name: 规则名称（唯一标识）
        condition: 触发条件函数 (stats, quality) -> bool
        level: 告警级别
        title: 告警标题
        message_template: 消息模板
        cooldown_seconds: 冷却时间
        tags: 标签列表

    Returns:
        AlertRule 实例
    """
    return AlertRule(
        name=name,
        condition=condition,
        level=level,
        title=title,
        message_template=message_template,
        cooldown_seconds=cooldown_seconds,
        tags=tags or [],
    )
