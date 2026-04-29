"""S7-010: akshare staleness alert rule."""

from __future__ import annotations

import logging

from src.alerting.models import AlertEvent, AlertLevel

logger = logging.getLogger(__name__)


def fire_akshare_stale_alert(
    manager,
    last_loaded_at: str | None,
    source: str,
    session=None,
) -> None:
    """akshare 交易日历数据过期时触发告警。

    当 TradeCalendar 数据来源为 akshare 且超过 7 天未更新时触发。

    Args:
        manager: AlertManager 实例
        last_loaded_at: 上次加载时间（ISO format）
        source: 当前数据来源（file / akshare / holidays / none）
        session: DB session（可选）
    """
    from src.backtest.engine import TradeCalendar

    if not TradeCalendar.is_stale():
        return  # 数据未过期

    logger.warning(
        "akshare 交易日历过期告警触发: source=%s, last_loaded=%s",
        source,
        last_loaded_at,
    )

    level = AlertLevel.WARNING
    title = "akshare 交易日历数据过期告警"
    message = (
        f"akshare 交易日历超过 7 天未更新（当前来源: {source}，上次加载: {last_loaded_at}）。"
        f"建议更新本地交易日历文件或检查网络连接。"
    )

    alert = AlertEvent(
        id="akshare_stale_alert",
        level=level,
        title=title,
        message=message,
        tags=["freshness", "akshare", "trading_calendar"],
        metadata={
            "rule_name": "akshare_stale",
            "last_loaded_at": last_loaded_at,
            "source": source,
        },
    )
    manager.fire_alert(alert, session=session)