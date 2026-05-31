from types import SimpleNamespace

import pytest

from api.routers.alerts import _build_alerting_status


@pytest.mark.asyncio
async def test_build_alerting_status_reads_alerting_config(monkeypatch) -> None:
    """告警状态接口应正确映射 app config。"""

    def fake_load_app_config(*args, **kwargs):
        return SimpleNamespace(
            config=SimpleNamespace(
                alerting={
                    "enabled": True,
                    "channel": "dingtalk",
                    "aggregation": {"window_minutes": 90, "max_count": 30},
                    "dingtalk": {"webhook_url": "https://example.invalid"},
                    "feishu": {"webhook_url": ""},
                    "wecom": {"webhook_url": ""},
                    "min_level": "WARNING",
                    "console_output": True,
                }
            )
        )

    monkeypatch.setattr("src.common.config.load_app_config", fake_load_app_config)

    status = await _build_alerting_status()

    assert status.enabled is True
    assert status.channel == "dingtalk"
    assert status.min_level == "WARNING"
    assert status.console_output is True
    assert status.aggregation_window_minutes == 90
    assert status.aggregation_max_count == 30
    assert status.webhook_configured is True
    assert status.channel_configured is True


@pytest.mark.asyncio
async def test_build_alerting_status_treats_placeholders_as_unconfigured(monkeypatch) -> None:
    """告警状态应把未解析的环境变量占位符视为未配置。"""

    def fake_load_app_config(*args, **kwargs):
        return SimpleNamespace(
            config=SimpleNamespace(
                alerting={
                    "enabled": True,
                    "channel": "dingtalk",
                    "aggregation": {"window_minutes": 90, "max_count": 30},
                    "dingtalk": {"webhook_url": "${DINGTALK_WEBHOOK_URL}"},
                    "feishu": {"webhook_url": ""},
                    "wecom": {"webhook_url": ""},
                    "min_level": "WARNING",
                    "console_output": True,
                }
            )
        )

    monkeypatch.setattr("src.common.config.load_app_config", fake_load_app_config)

    status = await _build_alerting_status()

    assert status.enabled is True
    assert status.webhook_configured is False
    assert status.channel_configured is True
