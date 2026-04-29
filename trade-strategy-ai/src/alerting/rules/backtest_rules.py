"""H: 回测任务失败告警规则（S7-007）。"""

from __future__ import annotations

from src.alerting.models import AlertEvent, AlertLevel


def fire_backtest_failure_alert(
    manager,
    task_id: str,
    error: str,
    session=None,
) -> None:
    """回测任务失败时触发告警。

    Args:
        manager: AlertManager 实例
        task_id: 回测任务 ID
        error: 错误信息
        session: DB session（可选）
    """
    alert = AlertEvent(
        id=f"backtest_failure_{task_id}",
        level=AlertLevel.WARNING,
        title=f"回测任务失败：{task_id}",
        message=f"回测任务 {task_id} 执行失败：{error}",
        tags=["backtest", "failed"],
        metadata={
            "rule_name": "backtest_failure",
            "task_id": task_id,
            "error": error,
        },
    )
    manager.fire_alert(alert, session=session)
