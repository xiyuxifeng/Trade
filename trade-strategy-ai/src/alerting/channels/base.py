"""渠道格式化器基类（S7-007）。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.alerting.models import AlertEvent


class ChannelFormatter(ABC):
    """告警渠道格式化器抽象基类。"""

    @abstractmethod
    def format(self, alert: AlertEvent) -> str:
        """将告警格式化为渠道特定的 Payload 字符串。"""
        ...

    def format_aggregated(self, alert: AlertEvent) -> str:
        """格式化聚合告警（多条合并后的告警）。子类可覆盖。"""
        return self.format(alert)
