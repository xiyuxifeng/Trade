"""Tests for alerting notifiers (P1-V01)."""

from __future__ import annotations

import sys
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock
from urllib.error import URLError, HTTPError

import pytest

sys.path.insert(0, "src")

from src.alerting.models import AlertEvent, AlertLevel
from src.alerting.notifiers import (
    AlertNotifier,
    ConsoleNotifier,
    WebhookNotifier,
    MemoryNotifier,
    CompositeNotifier,
)


def create_test_alert(level: AlertLevel = AlertLevel.INFO) -> AlertEvent:
    """创建测试用告警事件。"""
    return AlertEvent(
        level=level,
        title="Test Alert",
        message="This is a test alert",
        source="TestSource",
    )


class TestAlertEvent:
    """测试 AlertEvent 数据类。"""

    def test_to_dict(self):
        """转换为字典格式正确。"""
        alert = create_test_alert(AlertLevel.WARNING)
        result = alert.to_dict()

        assert result["title"] == "Test Alert"
        assert result["message"] == "This is a test alert"
        assert result["level"] == "WARNING"
        assert result["source"] == "TestSource"
        assert "timestamp" in result
        assert "id" in result

    def test_matches_tags_empty(self):
        """空标签列表匹配所有。"""
        alert = create_test_alert()
        alert.tags = ["tag1", "tag2"]
        assert alert.matches_tags([]) is True

    def test_matches_tags_found(self):
        """匹配的标签返回 True。"""
        alert = create_test_alert()
        alert.tags = ["tag1", "tag2"]
        assert alert.matches_tags(["tag1"]) is True

    def test_matches_tags_not_found(self):
        """不匹配的标签返回 False。"""
        alert = create_test_alert()
        alert.tags = ["tag1", "tag2"]
        assert alert.matches_tags(["tag3"]) is False


class TestAlertLevel:
    """测试 AlertLevel 枚举。"""

    def test_str_info(self):
        """INFO 级别字符串表示。"""
        assert str(AlertLevel.INFO) == "INFO"

    def test_str_warning(self):
        """WARNING 级别字符串表示。"""
        assert str(AlertLevel.WARNING) == "WARNING"

    def test_str_critical(self):
        """CRITICAL 级别字符串表示。"""
        assert str(AlertLevel.CRITICAL) == "CRITICAL"


class TestConsoleNotifier:
    """测试 ConsoleNotifier。"""

    @pytest.mark.asyncio
    async def test_send_no_color(self):
        """不启用颜色时发送告警。"""
        notifier = ConsoleNotifier(colorize=False)
        alert = create_test_alert(AlertLevel.INFO)

        # 不应抛出异常
        await notifier.send(alert)

    @pytest.mark.asyncio
    async def test_send_with_color_info(self):
        """INFO 级别启用颜色。"""
        notifier = ConsoleNotifier(colorize=True)
        alert = create_test_alert(AlertLevel.INFO)

        await notifier.send(alert)

    @pytest.mark.asyncio
    async def test_send_with_color_warning(self):
        """WARNING 级别启用颜色。"""
        notifier = ConsoleNotifier(colorize=True)
        alert = create_test_alert(AlertLevel.WARNING)

        await notifier.send(alert)

    @pytest.mark.asyncio
    async def test_send_with_color_critical(self):
        """CRITICAL 级别启用颜色。"""
        notifier = ConsoleNotifier(colorize=True)
        alert = create_test_alert(AlertLevel.CRITICAL)

        await notifier.send(alert)

    def test_get_color_info(self):
        """INFO 级别颜色代码。"""
        notifier = ConsoleNotifier()
        assert notifier._get_color(AlertLevel.INFO) == "94"

    def test_get_color_warning(self):
        """WARNING 级别颜色代码。"""
        notifier = ConsoleNotifier()
        assert notifier._get_color(AlertLevel.WARNING) == "93"

    def test_get_color_critical(self):
        """CRITICAL 级别颜色代码。"""
        notifier = ConsoleNotifier()
        assert notifier._get_color(AlertLevel.CRITICAL) == "91"


class TestMemoryNotifier:
    """测试 MemoryNotifier。"""

    @pytest.mark.asyncio
    async def test_send_stores_alert(self):
        """发送告警存储到内存。"""
        notifier = MemoryNotifier()
        alert = create_test_alert()

        await notifier.send(alert)

        assert notifier.count == 1
        assert notifier.get_alerts()[0].title == "Test Alert"

    @pytest.mark.asyncio
    async def test_send_batch(self):
        """批量发送告警。"""
        notifier = MemoryNotifier()
        alerts = [create_test_alert() for _ in range(3)]

        await notifier.send_batch(alerts)

        assert notifier.count == 3

    def test_get_alerts_returns_copy(self):
        """get_alerts 返回列表副本。"""
        notifier = MemoryNotifier()
        notifier._alerts.append(create_test_alert())

        alerts = notifier.get_alerts()
        alerts.clear()

        assert notifier.count == 1

    def test_clear(self):
        """clear 方法清空告警。"""
        notifier = MemoryNotifier()
        notifier._alerts.append(create_test_alert())

        notifier.clear()

        assert notifier.count == 0

    def test_filter_by_level(self):
        """按级别过滤告警。"""
        notifier = MemoryNotifier()
        notifier._alerts = [
            AlertEvent(level=AlertLevel.INFO, title="i1", message="m"),
            AlertEvent(level=AlertLevel.WARNING, title="w1", message="m"),
            AlertEvent(level=AlertLevel.INFO, title="i2", message="m"),
        ]

        result = notifier.filter_by_level(AlertLevel.INFO)

        assert len(result) == 2


class TestWebhookNotifier:
    """测试 WebhookNotifier。"""

    @pytest.mark.asyncio
    async def test_send_success(self, monkeypatch):
        """发送成功不抛异常。"""
        notifier = WebhookNotifier(url="https://example.com/webhook")

        mock_response = MagicMock()
        mock_response.status = 200
        # 支持上下文管理器协议
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        async def mock_run_in_executor(*args):
            return mock_response

        monkeypatch.setattr(
            "asyncio.get_event_loop",
            lambda: MagicMock(run_in_executor=mock_run_in_executor)
        )
        monkeypatch.setattr(
            "src.alerting.notifiers.urlopen",
            lambda *args, **kwargs: mock_response
        )

        await notifier.send(create_test_alert())

    @pytest.mark.asyncio
    async def test_send_http_error(self, monkeypatch):
        """HTTP 错误时抛出异常。"""
        notifier = WebhookNotifier(url="https://example.com/webhook")

        async def mock_run_in_executor(*args):
            raise HTTPError("https://example.com", 500, "Internal Error", {}, None)

        monkeypatch.setattr(
            "asyncio.get_event_loop",
            lambda: MagicMock(run_in_executor=mock_run_in_executor)
        )

        with pytest.raises(HTTPError):
            await notifier.send(create_test_alert())

    @pytest.mark.asyncio
    async def test_send_url_error(self, monkeypatch):
        """URL 错误时抛出异常。"""
        notifier = WebhookNotifier(url="https://example.com/webhook")

        async def mock_run_in_executor(*args):
            raise URLError("Connection refused")

        monkeypatch.setattr(
            "asyncio.get_event_loop",
            lambda: MagicMock(run_in_executor=mock_run_in_executor)
        )

        with pytest.raises(URLError):
            await notifier.send(create_test_alert())

    def test_init_default_values(self):
        """默认参数正确设置。"""
        notifier = WebhookNotifier(url="https://example.com/webhook")

        assert notifier.method == "POST"
        assert notifier.headers == {"Content-Type": "application/json"}
        assert notifier.timeout == 10.0
        assert notifier.verify_ssl is True

    def test_init_custom_values(self):
        """自定义参数正确设置。"""
        notifier = WebhookNotifier(
            url="https://example.com/webhook",
            method="PUT",
            headers={"X-Custom": "header"},
            timeout=30.0,
            verify_ssl=False,
        )

        assert notifier.method == "PUT"
        assert notifier.headers == {"X-Custom": "header"}
        assert notifier.timeout == 30.0
        assert notifier.verify_ssl is False


class TestCompositeNotifier:
    """测试 CompositeNotifier。"""

    @pytest.mark.asyncio
    async def test_send_to_all_notifiers(self):
        """发送告警到所有子通知器。"""
        memory1 = MemoryNotifier()
        memory2 = MemoryNotifier()
        composite = CompositeNotifier([memory1, memory2])

        await composite.send(create_test_alert())

        assert memory1.count == 1
        assert memory2.count == 1

    @pytest.mark.asyncio
    async def test_send_batch_to_all_notifiers(self):
        """批量发送告警到所有子通知器。"""
        memory1 = MemoryNotifier()
        memory2 = MemoryNotifier()
        composite = CompositeNotifier([memory1, memory2])

        alerts = [create_test_alert() for _ in range(2)]
        await composite.send_batch(alerts)

        assert memory1.count == 2
        assert memory2.count == 2


class TestAlertNotifierAbstract:
    """测试 AlertNotifier 抽象基类。"""

    @pytest.mark.asyncio
    async def test_send_batch_calls_send(self):
        """send_batch 默认调用 send。"""
        # 创建一个简单的测试用通知器
        class TestNotifier(AlertNotifier):
            def __init__(self):
                self.sent = []

            async def send(self, alert: AlertEvent):
                self.sent.append(alert)

        notifier = TestNotifier()
        alerts = [create_test_alert() for _ in range(3)]

        await notifier.send_batch(alerts)

        assert len(notifier.sent) == 3
