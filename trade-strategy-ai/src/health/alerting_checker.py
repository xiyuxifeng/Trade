"""告警系统健康检查器。"""
from __future__ import annotations

import asyncio

from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus

logger = get_logger("health.alerting")


class AlertingHealthChecker:
    """检查 AlertManager 状态。"""

    name: str = "alerting"

    def __init__(self, manager: "AlertManager | None" = None) -> None:
        """初始化检查器。

        Args:
            manager: AlertManager 实例。如果为 None，使用默认实例。
        """
        self._manager = manager

    async def check(self) -> ComponentCheck:
        """获取告警系统状态。"""
        try:
            from src.alerting.manager import AlertManager

            manager = self._manager
            if manager is None:
                # AlertManager 目前无全局单例，只能检查注入的实例
                return ComponentCheck(
                    name=self.name,
                    status=HealthStatus.WARNING,
                    details={"manager_instance": None},
                    error="AlertManager not injected, skipping",
                )

            stats = await asyncio.to_thread(manager.get_statistics)
            cooldown_rules = stats.get("rules_in_cooldown", [])
            alert_counts = stats.get("alert_counts", {})
            last_24h = sum(alert_counts.values())

            status = HealthStatus.OK if len(cooldown_rules) == 0 else HealthStatus.WARNING

            return ComponentCheck(
                name=self.name,
                status=status,
                details={
                    "total_rules": stats.get("total_rules", 0),
                    "enabled_rules": stats.get("enabled_rules", 0),
                    "cooldown_rules": len(cooldown_rules),
                    "last_24h_alerts": last_24h,
                },
            )
        except Exception as e:
            logger.error("alerting health check failed: %s", e)
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.ERROR,
                error=str(e),
            )