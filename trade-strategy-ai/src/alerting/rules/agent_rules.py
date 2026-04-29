"""G: Agent 执行异常告警规则（S7-007）。"""

from __future__ import annotations

import logging

from src.alerting.models import AlertEvent, AlertLevel

logger = logging.getLogger(__name__)


def fire_agent_failure_alert(
    manager,
    agent_name: str,
    run_type: str,
    error: str,
    session=None,
) -> None:
    """Agent 执行异常时触发告警。

    Args:
        manager: AlertManager 实例
        agent_name: Agent 名称（如 ManagerAgent）
        run_type: 运行类型（pre_market / after_close）
        error: 错误信息
        session: DB session（可选）
    """
    logger.warning(
        "Agent 执行失败告警触发: agent=%s, run_type=%s, error=%s",
        agent_name,
        run_type,
        error,
    )

    alert = AlertEvent(
        id=f"agent_failure_{agent_name}_{run_type}",
        level=AlertLevel.WARNING,
        title=f"Agent 执行失败：{agent_name}.{run_type}",
        message=f"Agent {agent_name} 执行 {run_type} 失败：{error}",
        tags=["agent", "failed", agent_name],
        metadata={
            "rule_name": "agent_failure",
            "agent_name": agent_name,
            "run_type": run_type,
            "error": error,
        },
    )
    manager.fire_alert(alert, session=session)
