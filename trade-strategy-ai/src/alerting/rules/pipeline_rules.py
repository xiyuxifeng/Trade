"""D: Pipeline 失败告警规则（S7-007）。"""

from __future__ import annotations

import logging

from src.alerting.models import AlertEvent, AlertLevel

logger = logging.getLogger(__name__)


def fire_pipeline_failure_alert(
    manager,
    pipeline_name: str,
    node_name: str | None,
    error: str,
    status: str = "failed",
    session=None,
) -> None:
    """Pipeline 运行失败时触发告警。

    Args:
        manager: AlertManager 实例
        pipeline_name: Pipeline 名称
        node_name: 失败的节点名称（可选）
        error: 错误信息
        status: 状态（failed / partial）
        session: DB session（可选）
    """
    level = AlertLevel.CRITICAL if status == "failed" else AlertLevel.WARNING
    node_str = f"节点 {node_name} " if node_name else ""

    logger.warning(
        "Pipeline 失败告警触发: pipeline=%s, node=%s, status=%s, error=%s",
        pipeline_name,
        node_name,
        status,
        error,
    )

    alert = AlertEvent(
        id=f"pipeline_failure_{pipeline_name}_{node_name or 'unknown'}",
        level=level,
        title=f"Pipeline 失败：{pipeline_name}",
        message=f"Pipeline {pipeline_name} {node_str}执行失败：{error}",
        tags=["pipeline", "failed", pipeline_name],
        metadata={
            "rule_name": "pipeline_failure",
            "pipeline_name": pipeline_name,
            "node_name": node_name,
            "error": error,
            "status": status,
        },
    )
    manager.fire_alert(alert, session=session)
