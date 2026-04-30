"""通用 JSON 格式化器（S7-007）。"""

from __future__ import annotations

import json

from src.alerting.channels.base import ChannelFormatter
from src.alerting.models import AlertEvent


class GenericFormatter(ChannelFormatter):
    """通用 JSON 格式（适用于自建 Webhook 服务）。"""

    def format(self, alert: AlertEvent) -> str:
        return json.dumps(alert.to_dict(), ensure_ascii=False, indent=2)
