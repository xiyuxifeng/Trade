"""A: 快照缺失告警规则（S7-007）。"""

from __future__ import annotations

import logging
from pathlib import Path

from src.alerting.models import AlertEvent, AlertLevel

logger = logging.getLogger(__name__)


def fire_snapshot_missing_alert(
    manager,
    trade_date: str,
    slot: str,
    session=None,
) -> None:
    """检查快照是否缺失，如缺失则触发告警。

    Args:
        manager: AlertManager 实例
        trade_date: 交易日期 YYYY-MM-DD
        slot: 时段，如 "17-30"
        session: DB session（可选）
    """
    snapshot_path = Path(f"data/market_universe/snapshots/{trade_date}/{slot}.json")

    if snapshot_path.exists():
        return  # 快照存在，不告警

    logger.warning(
        "快照缺失告警触发: trade_date=%s, slot=%s",
        trade_date,
        slot,
    )

    alert = AlertEvent(
        id=f"snapshot_missing_{trade_date}_{slot}",
        level=AlertLevel.WARNING,
        title=f"快照缺失：{trade_date} {slot}",
        message=f"交易日期 {trade_date} Slot {slot} 快照未生成，请检查 pipeline 是否正常执行。",
        tags=["snapshot", "missing"],
        metadata={
            "rule_name": "snapshot_missing",
            "trade_date": trade_date,
            "slot": slot,
        },
    )
    manager.fire_alert(alert, session=session)
