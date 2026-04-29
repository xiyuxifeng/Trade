"""钉钉群机器人格式化器（S7-007）。"""

from __future__ import annotations

from src.alerting.channels.base import ChannelFormatter
from src.alerting.models import AlertEvent


class DingTalkFormatter(ChannelFormatter):
    """钉钉群机器人 Markdown 格式。"""

    LEVEL_EMOJI = {
        "CRITICAL": "🔴",
        "WARNING": "🟡",
        "INFO": "🔵",
    }

    def format(self, alert: AlertEvent) -> str:
        ts = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        emoji = self.LEVEL_EMOJI.get(alert.level.value.upper(), "")
        tags_str = ", ".join(f"`{t}`" for t in alert.tags) if alert.tags else "无"

        lines = [
            f"### {emoji} [{alert.level.value.upper()}] {alert.title}",
            "",
            f"**时间：** {ts}",
        ]

        if alert.message:
            lines.append(f"**详情：** {alert.message}")

        if alert.metadata:
            for k, v in alert.metadata.items():
                if k not in (
                    "aggregated_count",
                    "aggregation_window_start",
                    "aggregation_window_end",
                    "last_error",
                    "rule_name",
                ):
                    lines.append(f"**{k}：** {v}")

        lines.append(f"**标签：** {tags_str}")

        return "\n".join(lines)

    def format_aggregated(self, alert: AlertEvent) -> str:
        meta = alert.metadata or {}
        count = meta.get("aggregated_count", 1)
        window_start = meta.get("aggregation_window_start", "")
        window_end = meta.get("aggregation_window_end", "")
        last_error = meta.get("last_error", "未知")
        ts = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        emoji = self.LEVEL_EMOJI.get(alert.level.value.upper(), "")
        tags_str = ", ".join(f"`{t}`" for t in alert.tags) if alert.tags else "无"

        lines = [
            f"### {emoji} [{alert.level.value.upper()}] {alert.title}（告警聚合）",
            "",
            f"**时间：** {ts}",
            f"**聚合窗口：** {window_start} ~ {window_end}",
            f"**累计次数：** {count} 次",
            f"**最近一次错误：** {last_error}",
            f"**标签：** {tags_str}",
        ]

        return "\n".join(lines)
