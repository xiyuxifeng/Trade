"""告警渠道格式化器（S7-007）。"""

from src.alerting.channels.base import ChannelFormatter
from src.alerting.channels.dingtalk import DingTalkFormatter
from src.alerting.channels.feishu import FeishuFormatter
from src.alerting.channels.wecom import WeComFormatter
from src.alerting.channels.generic import GenericFormatter

__all__ = [
    "ChannelFormatter",
    "DingTalkFormatter",
    "FeishuFormatter",
    "WeComFormatter",
    "GenericFormatter",
    "get_formatter",
]


def get_formatter(channel: str) -> ChannelFormatter:
    """根据 channel 名称返回对应的格式化器。"""
    channel_map = {
        "dingtalk": DingTalkFormatter(),
        "feishu": FeishuFormatter(),
        "wecom": WeComFormatter(),
        "generic": GenericFormatter(),
    }
    formatter = channel_map.get(channel.lower())
    if formatter is None:
        available = list(channel_map.keys())
        raise ValueError(f"未知的告警渠道: {channel}，可选：{available}")
    return formatter
