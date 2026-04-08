"""告警系统模块。

提供关键指标告警功能：
- 告警数据模型 (models)
- 告警通知器 (notifiers)
- 告警管理器 (manager)
- 预定义告警规则 (rules)

用法:
    from src.alerting import AlertManager, AlertEvent
    from src.alerting.notifiers import ConsoleNotifier
    from src.alerting.rules import get_default_rules

    # 创建告警管理器
    manager = AlertManager(
        rules=get_default_rules(),
        notifiers=[ConsoleNotifier()],
    )

    # 评估并发送告警
    alerts = await manager.evaluate_and_notify(stats, quality)
"""

from src.alerting.models import (
    AlertEvent,
    AlertLevel,
    AlertRule,
    create_alert,
)

from src.alerting.notifiers import (
    AlertNotifier,
    ConsoleNotifier,
    WebhookNotifier,
    MemoryNotifier,
    CompositeNotifier,
)

from src.alerting.manager import AlertManager

from src.alerting.rules import (
    DEFAULT_ALERT_RULES,
    get_default_rules,
    create_custom_rule,
)


__all__ = [
    # models
    "AlertEvent",
    "AlertLevel",
    "AlertRule",
    "create_alert",
    # notifiers
    "AlertNotifier",
    "ConsoleNotifier",
    "WebhookNotifier",
    "MemoryNotifier",
    "CompositeNotifier",
    # manager
    "AlertManager",
    # rules
    "DEFAULT_ALERT_RULES",
    "get_default_rules",
    "create_custom_rule",
]
