"""告警配置加载（S7-007）。

从 app.yaml 读取 alerting.* 配置。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel


class AlertingAggregationConfig(BaseModel):
    """聚合配置。"""
    window_minutes: int = 60
    max_count: int = 100


class AlertingDingTalkConfig(BaseModel):
    """钉钉配置。"""
    webhook_url: str = ""
    secret: str = ""


class AlertingFeishuConfig(BaseModel):
    """飞书配置。"""
    webhook_url: str = ""


class AlertingWeComConfig(BaseModel):
    """企业微信配置。"""
    webhook_url: str = ""


class AlertingConfig(BaseModel):
    """告警根配置。"""
    enabled: bool = True
    channel: str = "generic"
    aggregation: AlertingAggregationConfig = AlertingAggregationConfig()
    dingtalk: AlertingDingTalkConfig = AlertingDingTalkConfig()
    feishu: AlertingFeishuConfig = AlertingFeishuConfig()
    wecom: AlertingWeComConfig = AlertingWeComConfig()
    min_level: str = "WARNING"
    console_output: bool = True


def load_alerting_config(config: dict[str, Any] | None = None) -> AlertingConfig:
    """从完整 app config 或 alerting 子配置中提取告警配置。

    Args:
        config: 完整 app config dict，为空时返回默认值

    Returns:
        AlertingConfig 实例
    """
    if config is None:
        return AlertingConfig()
    raw = config.get("alerting", config) if isinstance(config, dict) else {}
    return AlertingConfig(**raw)
