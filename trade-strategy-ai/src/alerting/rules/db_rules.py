"""E: 数据库异常告警规则（S7-007）。"""

from __future__ import annotations

import logging

from src.alerting.models import AlertEvent, AlertLevel

logger = logging.getLogger(__name__)


def fire_db_failure_alert(
    manager,
    error_type: str,
    error_message: str,
    session=None,
) -> None:
    """数据库异常时触发告警。

    Args:
        manager: AlertManager 实例
        error_type: 错误类型（connection_error / query_timeout / deadlock 等）
        error_message: 错误详细信息
        session: DB session（可选）
    """
    logger.error(
        "数据库异常告警触发: error_type=%s, error=%s",
        error_type,
        error_message,
    )

    alert = AlertEvent(
        id=f"db_failure_{error_type}",
        level=AlertLevel.CRITICAL,
        title=f"数据库异常：{error_type}",
        message=f"数据库 {error_type}：{error_message}",
        tags=["database", "error", error_type],
        metadata={
            "rule_name": "database_failure",
            "error_type": error_type,
            "error": error_message,
        },
    )
    manager.fire_alert(alert, session=session)
