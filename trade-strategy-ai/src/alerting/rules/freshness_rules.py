"""C: 数据新鲜度告警规则（S7-007）。"""

from __future__ import annotations

from src.alerting.models import AlertEvent, AlertLevel


def fire_freshness_alert(
    manager,
    data_type: str,
    hours: float,
    threshold_hours: float = 24.0,
    session=None,
) -> None:
    """数据新鲜度不足时触发告警。

    Args:
        manager: AlertManager 实例
        data_type: 数据类型（articles / trades / market_data）
        hours: 当前未更新小时数
        threshold_hours: 阈值小时数（默认 24h）
        session: DB session（可选）
    """
    if hours < threshold_hours:
        return  # 数据足够新鲜

    level = AlertLevel.CRITICAL if hours > threshold_hours * 2 else AlertLevel.WARNING

    alert = AlertEvent(
        id=f"freshness_{data_type}_{hours:.0f}h",
        level=level,
        title=f"数据新鲜度告警：{data_type}",
        message=f"{data_type} 数据已 {hours:.1f} 小时未更新（阈值 {threshold_hours}h），请检查数据抓取链路。",
        tags=["freshness", data_type],
        metadata={
            "rule_name": "data_freshness",
            "data_type": data_type,
            "hours": hours,
            "threshold_hours": threshold_hours,
        },
    )
    manager.fire_alert(alert, session=session)
