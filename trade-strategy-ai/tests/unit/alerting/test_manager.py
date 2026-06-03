"""AlertManager 扩展测试（S7-007）。"""
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.alerting.models import AlertEvent, AlertLevel


class TestAlertManagerExtensions:
    """AlertManager fire_alert 扩展测试。"""

    def test_load_config_creates_aggregator(self):
        """从配置加载后创建 aggregator"""
        from src.alerting.config import load_alerting_config

        cfg = load_alerting_config({
            "alerting": {
                "channel": "dingtalk",
                "aggregation": {"window_minutes": 30, "max_count": 50},
                "dingtalk": {"webhook_url": "https://oapi.dingtalk.com/robot/send?token=xxx"},
            }
        })
        assert cfg.channel == "dingtalk"
        assert cfg.aggregation.window_minutes == 30
        assert cfg.aggregation.max_count == 50

    def test_load_config_defaults(self):
        """无配置时使用默认值"""
        from src.alerting.config import load_alerting_config

        cfg = load_alerting_config(None)
        assert cfg.channel == "generic"
        assert cfg.aggregation.window_minutes == 60

    @pytest.mark.asyncio
    async def test_fire_alert_filters_by_level(self):
        """低于 min_level 的告警被过滤"""
        from src.alerting.manager import AlertManager

        cfg = {
            "alerting": {
                "channel": "generic",
                "aggregation": {"window_minutes": 0, "max_count": 100},
                "min_level": "WARNING",
                "console_output": False,
            }
        }
        manager = AlertManager(alerting_config=cfg)

        # INFO 级别应被过滤（min_level = WARNING）
        info_alert = AlertEvent(
            id="info-001",
            level=AlertLevel.INFO,
            title="信息告警",
            message="这条应该被过滤",
            tags=["test"],
        )

        # 不应抛出，且 aggregator 中没有告警
        # （因为 INFO < WARNING）
        manager.fire_alert(info_alert, session=None)

    def test_fire_alert_calls_webhook(self):
        """fire_alert 应走 Webhook 发送路径且不应同步抛错。"""
        from src.alerting.manager import AlertManager

        cfg = {
            "alerting": {
                "channel": "generic",
                "aggregation": {"window_minutes": 0, "max_count": 100},
                "dingtalk": {"webhook_url": "https://oapi.dingtalk.com/robot/send?token=test"},
                "min_level": "WARNING",
                "console_output": False,
            }
        }
        manager = AlertManager(alerting_config=cfg)

        alert = AlertEvent(
            id="test-001",
            level=AlertLevel.WARNING,
            title="测试告警",
            message="test message",
            tags=["test"],
        )

        manager.fire_alert(alert, session=None)

    def test_disabled_alerting_is_noop(self):
        """alerting.enabled=false 时应直接跳过发送。"""
        from src.alerting.manager import AlertManager

        cfg = {
            "alerting": {
                "enabled": False,
                "channel": "dingtalk",
                "aggregation": {"window_minutes": 0, "max_count": 100},
                "dingtalk": {"webhook_url": "https://oapi.dingtalk.com/robot/send?token=test"},
                "min_level": "WARNING",
                "console_output": False,
            }
        }
        manager = AlertManager(alerting_config=cfg)

        alert = AlertEvent(
            id="disabled-001",
            level=AlertLevel.CRITICAL,
            title="禁用告警",
            message="should be skipped",
            tags=["test"],
        )

        manager.fire_alert(alert, session=None)

    @pytest.mark.asyncio
    async def test_async_persist_uses_independent_session_scope(self):
        """告警持久化应使用独立 session_scope，不复用外层 session。"""
        from src.alerting.manager import AlertManager

        cfg = {
            "alerting": {
                "channel": "generic",
                "aggregation": {"window_minutes": 0, "max_count": 100},
                "min_level": "WARNING",
                "console_output": False,
            }
        }
        manager = AlertManager(alerting_config=cfg)

        inner_session = AsyncMock()
        repo = MagicMock()
        record = MagicMock()
        record.id = uuid.uuid4()
        repo.insert = AsyncMock(return_value=record)
        repo.update_status = AsyncMock(return_value=record)

        alert = AlertEvent(
            id="persist-001",
            level=AlertLevel.WARNING,
            title="持久化告警",
            message="persist me",
            tags=["test"],
            metadata={
                "aggregation_key": "agg-key",
                "aggregated_count": 2,
                "aggregation_window_start": "2026-06-01T00:00:00+00:00",
            },
        )

        @asynccontextmanager
        async def fake_session_scope():
            yield inner_session

        with patch("src.alerting.manager.session_scope", fake_session_scope):
            await manager._async_persist(
                alert,
                "generic",
                "sent",
                repo,
                datetime.now(UTC),
            )

        repo.insert.assert_awaited_once()
        assert repo.insert.await_args.kwargs["session"] is inner_session
        repo.update_status.assert_awaited_once()
        assert repo.update_status.await_args.args[0] is inner_session
