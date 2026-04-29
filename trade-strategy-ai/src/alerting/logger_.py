"""告警结构化日志（S7-007）。

将所有告警事件写入 data/logs/alert.log，每行 JSON。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from src.alerting.models import AlertEvent

logger = logging.getLogger("alerting")


class AlertFileLogger:
    """告警结构化文件日志。"""

    def __init__(self, log_path: str | Path = "data/logs/alert.log") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        # 确保文件存在
        if not self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")

    def log(
        self,
        alert: AlertEvent,
        status: str,
        channel: str,
        aggregation_key: str | None = None,
    ) -> None:
        """写入单条告警日志。"""
        record = {
            "ts": alert.timestamp.isoformat(),
            "level": alert.level.value,
            "title": alert.title,
            "message": alert.message,
            "channel": channel,
            "status": status,
            "aggregation_count": (
                alert.metadata.get("aggregated_count", 1)
                if alert.metadata
                else 1
            ),
            "aggregation_key": aggregation_key or "",
            "tags": alert.tags or [],
            "metadata": alert.metadata or {},
        }

        line = json.dumps(record, ensure_ascii=False)
        # 追加写入
        self.log_path.write_text(
            self.log_path.read_text(encoding="utf-8") + line + "\n",
            encoding="utf-8",
        )
        logger.debug("alert logged: %s", alert.title)
