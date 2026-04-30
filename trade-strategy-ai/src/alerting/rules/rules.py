"""预定义告警规则（S7-007 扩展）。

提供原有默认规则 + S7-007 新规则导出。
"""

from src.alerting.models import AlertEvent, AlertLevel, AlertRule


def _articles_freshness_condition(stats, quality) -> bool:
    """文章数据新鲜度条件。"""
    hours = getattr(stats.articles, "freshness_hours", None)
    return hours is not None and hours > 24


def _trades_freshness_condition(stats, quality) -> bool:
    """交易数据新鲜度条件。"""
    hours = getattr(stats.trades, "freshness_hours", None)
    return hours is not None and hours > 24


def _market_freshness_condition(stats, quality) -> bool:
    """行情数据新鲜度条件。"""
    hours = getattr(stats.market_data, "freshness_hours", None)
    return hours is not None and hours > 24


def _anomaly_rate_condition(stats, quality) -> bool:
    """异常率条件。"""
    from src.pipeline.dashboard_models import DashboardStats, QualityMetrics
    total = stats.articles.total + stats.trades.total + stats.market_data.total
    if total <= 0:
        return False
    anomaly_rate = (quality.total_issues / total) * 100
    return anomaly_rate > 10


def _buy_sell_drift_condition(stats, quality) -> bool:
    """买卖比漂移条件。"""
    total = stats.trades.total
    if total <= 0:
        return False
    by_type = getattr(stats.trades, "by_type", {})
    buys = by_type.get("buy", 0) if isinstance(by_type, dict) else 0
    ratio = buys / total
    return ratio < 0.2 or ratio > 0.8


DEFAULT_ALERT_RULES: list[AlertRule] = [
    AlertRule(
        name="articles_freshness",
        condition=_articles_freshness_condition,
        level=AlertLevel.WARNING,
        title="文章数据新鲜度告警",
        message_template="文章数据已 {articles_freshness:.1f} 小时未更新",
        cooldown_seconds=3600,
        tags=["freshness", "articles"],
    ),
    AlertRule(
        name="trades_freshness",
        condition=_trades_freshness_condition,
        level=AlertLevel.WARNING,
        title="交易记录新鲜度告警",
        message_template="交易记录已 {trades_freshness:.1f} 小时未更新",
        cooldown_seconds=3600,
        tags=["freshness", "trades"],
    ),
    AlertRule(
        name="market_data_freshness",
        condition=_market_freshness_condition,
        level=AlertLevel.WARNING,
        title="行情数据新鲜度告警",
        message_template="行情数据已 {market_freshness:.1f} 小时未更新",
        cooldown_seconds=3600,
        tags=["freshness", "market_data"],
    ),
    AlertRule(
        name="anomaly_rate_high",
        condition=_anomaly_rate_condition,
        level=AlertLevel.WARNING,
        title="数据异常率偏高",
        message_template="数据异常率 {anomaly_rate:.1f}% 超过 10% 阈值",
        cooldown_seconds=1800,
        tags=["quality", "anomaly"],
    ),
    AlertRule(
        name="buy_sell_drift",
        condition=_buy_sell_drift_condition,
        level=AlertLevel.WARNING,
        title="买卖比漂移",
        message_template="买入比例 {buy_ratio:.1f}% 偏离正常区间 [20%, 80%]",
        cooldown_seconds=3600,
        tags=["quality", "balance"],
    ),
]


def get_default_rules() -> list[AlertRule]:
    """返回默认告警规则列表。"""
    return list(DEFAULT_ALERT_RULES)


def create_custom_rule(
    name: str,
    condition,
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
        tags: 标签

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
