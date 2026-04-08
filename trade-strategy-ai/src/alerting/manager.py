"""告警管理器。

提供增强版的告警管理功能：
- 告警规则评估
- 冷却时间管理
- 多通知器协调
- 告警聚合
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from src.common.logger import get_logger
from src.alerting.models import AlertEvent, AlertLevel, AlertRule, create_alert
from src.alerting.notifiers import AlertNotifier

if TYPE_CHECKING:
    from src.pipeline.dashboard_models import DashboardStats, QualityMetrics


logger = get_logger("alerting.manager")


class AlertManager:
    """增强版告警管理器。

    支持：
    - 多个告警规则
    - 多个通知器
    - 冷却时间（防止告警风暴）
    - 告警聚合

    Attributes:
        rules: 告警规则列表
        notifiers: 通知器列表
        default_cooldown: 默认冷却时间（秒）
    """

    def __init__(
        self,
        rules: list[AlertRule] | None = None,
        notifiers: list[AlertNotifier] | None = None,
        default_cooldown: int = 300,
    ) -> None:
        """初始化告警管理器。

        Args:
            rules: 告警规则列表
            notifiers: 通知器列表
            default_cooldown: 默认冷却时间
        """
        self.rules = rules or []
        self.notifiers = notifiers or []
        self.default_cooldown = default_cooldown
        self._last_alert_time: dict[str, datetime] = {}
        self._alert_counts: dict[str, int] = {}  # 用于统计
        self._lock = asyncio.Lock()

    async def evaluate(
        self,
        stats: "DashboardStats",
        quality: "QualityMetrics",
    ) -> list[AlertEvent]:
        """评估所有规则并返回触发的告警列表。

        此方法不发送通知，只返回告警事件。

        Args:
            stats: Dashboard 统计数据
            quality: 数据质量指标

        Returns:
            触发的告警事件列表
        """
        alerts: list[AlertEvent] = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                triggered = rule.condition(stats, quality)
            except Exception as e:
                logger.error(
                    "rule %s evaluation error: %s",
                    rule.name,
                    str(e),
                )
                continue

            if triggered:
                # 检查冷却时间
                if self._is_in_cooldown(rule.name, rule.cooldown_seconds):
                    logger.debug(
                        "rule %s is in cooldown, skipping",
                        rule.name,
                    )
                    continue

                # 构建告警消息
                metadata = self._build_metadata(stats, quality)
                message = rule.message_template.format(**metadata)

                # 创建告警事件
                alert = create_alert(
                    rule=rule,
                    message=message,
                    metadata=metadata,
                )
                alerts.append(alert)

                # 更新冷却时间
                await self._update_cooldown(rule.name)

                # 更新统计
                self._increment_count(rule.name)

        return alerts

    async def evaluate_and_notify(
        self,
        stats: "DashboardStats",
        quality: "QualityMetrics",
    ) -> list[AlertEvent]:
        """评估规则并发送通知。

        Args:
            stats: Dashboard 统计数据
            quality: 数据质量指标

        Returns:
            触发的告警事件列表
        """
        alerts = await self.evaluate(stats, quality)

        if alerts:
            await self._send_to_notifiers(alerts)

        return alerts

    async def _send_to_notifiers(self, alerts: list[AlertEvent]) -> None:
        """发送告警到所有通知器。"""
        for notifier in self.notifiers:
            try:
                await notifier.send_batch(alerts)
            except Exception as e:
                logger.error(
                    "notifier %s failed to send alerts: %s",
                    type(notifier).__name__,
                    str(e),
                )

    def _is_in_cooldown(self, rule_name: str, cooldown_seconds: int | None = None) -> bool:
        """检查规则是否在冷却期。"""
        if rule_name not in self._last_alert_time:
            return False

        cooldown = cooldown_seconds or self.default_cooldown
        elapsed = (datetime.now(UTC) - self._last_alert_time[rule_name]).total_seconds()
        return elapsed < cooldown

    async def _update_cooldown(self, rule_name: str) -> None:
        """更新规则的冷却时间。"""
        async with self._lock:
            self._last_alert_time[rule_name] = datetime.now(UTC)

    def _increment_count(self, rule_name: str) -> None:
        """增加规则触发计数。"""
        self._alert_counts[rule_name] = self._alert_counts.get(rule_name, 0) + 1

    def _build_metadata(self, stats: "DashboardStats", quality: "QualityMetrics") -> dict[str, Any]:
        """构建告警元数据。"""
        total = stats.articles.total + stats.trades.total + stats.market_data.total
        anomaly_rate = (quality.total_issues / total * 100) if total > 0 else 0.0
        buy_ratio = self._calc_buy_ratio(stats)

        return {
            "articles_freshness": stats.articles.freshness_hours or 0,
            "trades_freshness": stats.trades.freshness_hours or 0,
            "market_freshness": stats.market_data.freshness_hours or 0,
            "anomaly_rate": anomaly_rate,
            "total_issues": quality.total_issues,
            "buy_ratio": buy_ratio or 0,
            "sell_ratio": 100 - buy_ratio if buy_ratio is not None else 0,
            "dup_count": quality.article_dup_count,
            "trades_total": stats.trades.total,
            "unique_symbols": getattr(stats.trades, "unique_symbols", 0),
        }

    def _calc_buy_ratio(self, stats: "DashboardStats") -> float | None:
        """计算买入比例。"""
        total = stats.trades.total
        if total <= 0:
            return None
        by_type = getattr(stats.trades, "by_type", {})
        buys = by_type.get("buy", 0) if isinstance(by_type, dict) else 0
        return (buys / total) * 100 if buys else None

    def get_statistics(self) -> dict[str, Any]:
        """获取告警统计信息。"""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "total_notifiers": len(self.notifiers),
            "alert_counts": dict(self._alert_counts),
            "rules_in_cooldown": [
                name for name in self._last_alert_time
                if self._is_in_cooldown(name)
            ],
        }

    def reset_cooldowns(self) -> None:
        """重置所有冷却时间。"""
        self._last_alert_time.clear()
        logger.info("all cooldowns reset")

    def reset_statistics(self) -> None:
        """重置统计计数。"""
        self._alert_counts.clear()
        logger.info("alert statistics reset")

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则。"""
        self.rules.append(rule)
        logger.info("rule added: %s", rule.name)

    def remove_rule(self, rule_name: str) -> bool:
        """移除告警规则。"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                logger.info("rule removed: %s", rule_name)
                return True
        return False

    def enable_rule(self, rule_name: str) -> bool:
        """启用告警规则。"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                logger.info("rule enabled: %s", rule_name)
                return True
        return False

    def disable_rule(self, rule_name: str) -> bool:
        """禁用告警规则。"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info("rule disabled: %s", rule_name)
                return True
        return False

    def get_rule(self, rule_name: str) -> AlertRule | None:
        """获取指定名称的规则。"""
        for rule in self.rules:
            if rule.name == rule_name:
                return rule
        return None

    def get_enabled_rules(self) -> list[AlertRule]:
        """获取所有已启用的规则。"""
        return [r for r in self.rules if r.enabled]
