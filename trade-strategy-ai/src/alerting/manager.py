"""告警管理器。

提供增强版的告警管理功能：
- 告警规则评估
- 冷却时间管理
- 多通知器协调
- 告警聚合（S7-007）
- 多渠道推送（S7-007）
- AlertHistory DB 持久化（S7-007）
- alert.log 结构化日志（S7-007）
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, Any

from src.common.logger import get_logger
from src.alerting.models import AlertEvent, AlertLevel, AlertRule, create_alert
from src.alerting.db import AlertHistoryRepository
from src.alerting.notifiers import AlertNotifier
from src.db.session import session_scope

if TYPE_CHECKING:
    from src.pipeline.dashboard_models import DashboardStats, QualityMetrics


logger = get_logger("alerting.manager")

# 全局默认 AlertManager 实例（供健康检查等模块发现）
_default_manager: "AlertManager | None" = None


def get_default_manager() -> "AlertManager | None":
    """获取全局默认 AlertManager 实例。"""
    return _default_manager


def set_default_manager(manager: "AlertManager") -> None:
    """设置全局默认 AlertManager 实例。"""
    global _default_manager
    _default_manager = manager


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
        alerting_config: dict[str, Any] | None = None,
    ) -> None:
        """初始化告警管理器。

        Args:
            rules: 告警规则列表
            notifiers: 通知器列表
            default_cooldown: 默认冷却时间
            alerting_config: S7-007 告警配置（channel/aggregation/notifier 等）
        """
        self.rules = rules or []
        self.notifiers = notifiers or []
        self.default_cooldown = default_cooldown
        self._last_alert_time: dict[str, datetime] = {}
        self._alert_counts: dict[str, int] = {}  # 用于统计
        self._lock = asyncio.Lock()

        # S7-007 扩展：告警配置
        self._alerting_config = alerting_config
        self._alert_cfg = None
        self._alerting_enabled = False
        self._init_alerting_extensions()

        # 自动注册为全局默认实例（供健康检查等模块发现）
        # 仅在告警已启用且存在显式配置时注册，避免未配置实例污染全局状态。
        global _default_manager
        if self._alerting_enabled and _default_manager is None:
            _default_manager = self

    def _init_alerting_extensions(self) -> None:
        """初始化 S7-007 告警扩展（渠道/聚合/日志）。"""
        if self._alerting_config is None:
            return

        from src.alerting.config import load_alerting_config
        from src.alerting.channels import get_formatter
        from src.alerting.aggregator import AlertAggregator
        from src.alerting.logger_ import AlertFileLogger

        cfg = load_alerting_config(self._alerting_config)
        self._alert_cfg = cfg
        self._alerting_enabled = bool(cfg.enabled)
        if not cfg.enabled:
            logger.info("alerting disabled by config")
            return
        self._formatter = get_formatter(cfg.channel)
        self._aggregator = AlertAggregator(
            window_minutes=cfg.aggregation.window_minutes,
            max_count=cfg.aggregation.max_count,
        )
        self._file_logger = AlertFileLogger()

    def fire_alert(
        self,
        alert: AlertEvent,
        session=None,
    ) -> None:
        """触发告警：聚合 + 发送 + 持久化 + 写日志。

        Args:
            alert: 告警事件
            session: DB session（可选）
        """
        if hasattr(self, "_alert_cfg") and self._alert_cfg and not self._alert_cfg.enabled:
            logger.debug("alert %s skipped because alerting is disabled", alert.id)
            return

        # 级别过滤
        if hasattr(self, "_alert_cfg") and self._alert_cfg:
            priority_map = {
                AlertLevel.INFO: 0,
                AlertLevel.WARNING: 1,
                AlertLevel.CRITICAL: 2,
            }
            # config 中 min_level 是大写字符串，转小写后映射
            min_level_value = self._alert_cfg.min_level.lower()
            min_priority = 1  # 默认 WARNING
            for lvl, pri in priority_map.items():
                if lvl.value == min_level_value:
                    min_priority = pri
                    break
            alert_priority = priority_map.get(alert.level, 0)
            if alert_priority < min_priority:
                logger.debug("alert %s filtered by min_level", alert.id)
                return

        # 聚合
        if hasattr(self, "_aggregator") and self._aggregator:
            added = self._aggregator.add_alert(alert)
            if not added:
                return  # 触发了 flush，聚合告警已发送

            # 检查是否有待 flush 的窗口
            self._flush_all(session)
        else:
            self._send_and_persist(alert, session=session)

    def _flush_all(self, session=None) -> None:
        """触发所有窗口的 flush。"""
        def emit(aggregated: AlertEvent):
            self._send_and_persist(aggregated, session=session)

        if hasattr(self, "_aggregator") and self._aggregator:
            self._aggregator.flush(emit_fn=emit)

    def _send_and_persist(self, alert: AlertEvent, session=None) -> None:
        """发送告警 + 持久化 + 写日志。"""
        channel = (
            self._alert_cfg.channel
            if getattr(self, "_alert_cfg", None) is not None
            else (self._alerting_config.get("channel", "generic") if self._alerting_config else "generic")
        )

        # 发送到 Webhook
        status = "sent"
        try:
            self._do_send_webhook(alert)
        except Exception as exc:
            logger.warning("webhook send failed: %s", exc)
            status = "failed"

        # 写 alert.log
        if hasattr(self, "_file_logger") and self._file_logger:
            aggregation_key = alert.metadata.get("aggregation_key") if alert.metadata else None
            self._file_logger.log(
                alert=alert,
                status=status,
                channel=channel,
                aggregation_key=aggregation_key,
            )

        # 持久化到 DB
        if session is not None:
            self._persist_alert(alert, channel, status, session)

    def _do_send_webhook(self, alert: AlertEvent) -> None:
        """发送告警到 Webhook。"""
        from src.alerting.notifiers import WebhookNotifier

        cfg = getattr(self, "_alert_cfg", None)
        if cfg is None:
            return

        if cfg.channel == "dingtalk":
            url = cfg.dingtalk.webhook_url
        elif cfg.channel == "feishu":
            url = cfg.feishu.webhook_url
        elif cfg.channel == "wecom":
            url = cfg.wecom.webhook_url
        else:
            url = ""

        if not url:
            logger.debug("no webhook URL configured for channel %s", cfg.channel)
            return

        notifier = WebhookNotifier(url=url)
        # 同步发送（WebhookNotifier 是异步，但 run_in_executor 在其内部已处理）
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, self._sync_send, notifier, alert)

    def _sync_send(self, notifier: WebhookNotifier, alert: AlertEvent) -> None:
        """在线程池中同步发送。"""
        asyncio.run(notifier.send(alert))

    def _persist_alert(
        self,
        alert: AlertEvent,
        channel: str,
        status: str,
        session,
    ) -> None:
        """持久化告警到 DB。

        说明：
        - 这里不复用外层传入的 session，避免告警持久化和业务事务互相抢占同一个 AsyncSession。
        - 持久化任务使用独立 session_scope，自带提交边界。
        """
        repo = AlertHistoryRepository()
        now = datetime.now(timezone.utc)

        # 同步持久化（在已有的事件循环外调用时直接执行；在事件循环内则后台调度）
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._async_persist(alert, channel, status, repo, now))
            return

        task = asyncio.create_task(self._async_persist(alert, channel, status, repo, now))
        task.add_done_callback(self._log_async_persist_error)

    def _log_async_persist_error(self, task: asyncio.Task[None]) -> None:
        """记录后台告警持久化任务中的异常。"""
        with suppress(asyncio.CancelledError):
            try:
                task.result()
            except Exception:
                logger.exception("alert persistence task failed")

    async def _async_persist(
        self,
        alert: AlertEvent,
        channel: str,
        status: str,
        repo: "AlertHistoryRepository",
        now: datetime,
    ) -> None:
        """异步持久化告警。"""
        async with session_scope() as session:
            record = await repo.insert(
                session=session,
                alert_id=alert.id,
                level=alert.level.value,
                title=alert.title,
                message=alert.message,
                channel=channel,
                tags=alert.tags,
                alert_metadata=alert.metadata,
                aggregation_key=alert.metadata.get("aggregation_key") if alert.metadata else None,
                aggregated_count=alert.metadata.get("aggregated_count", 1) if alert.metadata else 1,
                aggregation_window_start=datetime.fromisoformat(alert.metadata["aggregation_window_start"])
                if alert.metadata and "aggregation_window_start" in alert.metadata else None,
            )
            if status == "sent":
                await repo.update_status(session, record.id, "sent", sent_at=now)

    def send_test_alert(
        self,
        title: str = "测试告警",
        message: str = "这是一条测试告警",
        session=None,
    ) -> None:
        """发送测试告警（用于验证 Webhook 配置）。"""
        if hasattr(self, "_alert_cfg") and self._alert_cfg and not self._alert_cfg.enabled:
            logger.debug("test alert skipped because alerting is disabled")
            return

        alert = AlertEvent(
            id=str(uuid.uuid4()),
            level=AlertLevel.INFO,
            title=title,
            message=message,
            tags=["test"],
            metadata={"test": True},
        )
        self._send_and_persist(alert, session=session)

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
        if hasattr(self, "_alert_cfg") and self._alert_cfg and not self._alert_cfg.enabled:
            logger.debug("alert evaluation skipped because alerting is disabled")
            return []

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
