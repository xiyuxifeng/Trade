"""企业微信群机器人格式化器（S7-007）。"""

from __future__ import annotations

from src.alerting.channels.base import ChannelFormatter
from src.alerting.channels.dingtalk import DingTalkFormatter
from src.alerting.models import AlertEvent


class WeComFormatter(ChannelFormatter):
    """企业微信群机器人 Markdown 格式（与钉钉类似）。"""

    def format(self, alert: AlertEvent) -> str:
        dingtalk = DingTalkFormatter()
        return dingtalk.format(alert)

    def format_aggregated(self, alert: AlertEvent) -> str:
        dingtalk = DingTalkFormatter()
        return dingtalk.format_aggregated(alert)
