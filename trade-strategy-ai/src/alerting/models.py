"""告警数据模型。

提供告警系统的核心数据结构：
- AlertLevel: 告警级别枚举
- AlertEvent: 告警事件
- AlertRule: 告警规则
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class AlertLevel(Enum):
    """告警级别枚举。"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    def __str__(self) -> str:
        return self.value.upper()


@dataclass(slots=True)
class AlertEvent:
    """告警事件。

    Attributes:
        id: 告警唯一标识符
        level: 告警级别
        source: 告警来源（如 "AlertManager", "Prometheus"）
        title: 简短标题
        message: 详细描述
        timestamp: 告警时间戳
        metadata: 额外上下文数据
        tags: 用于分组和过滤的标签
    """

    level: AlertLevel
    title: str
    message: str
    source: str = "AlertManager"
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。"""
        return {
            "id": self.id,
            "level": str(self.level),
            "source": self.source,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags,
        }

    def matches_tags(self, tags: list[str]) -> bool:
        """检查是否匹配给定标签。"""
        if not tags:
            return True
        return any(tag in self.tags for tag in tags)


@dataclass(slots=True)
class AlertRule:
    """告警规则配置。

    Attributes:
        name: 规则名称（唯一标识）
        condition: 触发条件函数
        level: 告警级别
        title: 告警标题
        message_template: 告警消息模板（支持格式化）
        cooldown_seconds: 告警冷却时间（秒）
        enabled: 规则是否启用
        tags: 规则关联的标签
    """

    name: str
    condition: "AlertRuleCondition"  # Callable[[Any, Any], bool]
    level: AlertLevel
    title: str
    message_template: str
    cooldown_seconds: int = 300  # 默认 5 分钟冷却
    enabled: bool = True
    tags: list[str] = field(default_factory=list)

    def evaluate(self, *args: Any, **kwargs: Any) -> tuple[bool, str]:
        """评估规则并返回（是否触发，消息）。

        Args:
            *args: 传递给条件的参数 (stats, quality)
            **kwargs: 用于格式化消息模板的额外参数

        Returns:
            (是否触发, 格式化后的消息)
        """
        triggered = self.condition(*args)
        message = self.message_template.format(**kwargs) if kwargs else self.message_template
        return triggered, message

    def is_enabled(self) -> bool:
        """检查规则是否启用。"""
        return self.enabled


# 类型别名，用于 AlertRule.condition
AlertRuleCondition = Any  # Callable[[Any, Any], bool]


def create_alert(
    rule: AlertRule,
    level: AlertLevel | None = None,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> AlertEvent:
    """根据规则创建告警事件。

    Args:
        rule: 告警规则
        level: 告警级别（默认使用规则级别）
        message: 告警消息（默认使用规则模板）
        metadata: 额外元数据
        tags: 额外标签

    Returns:
        AlertEvent 实例
    """
    return AlertEvent(
        level=level or rule.level,
        title=rule.title,
        message=message or rule.message_template,
        source="AlertManager",
        metadata=metadata or {},
        tags=tags or rule.tags,
    )
