"""单元测试 - 告警通知器。"""

from __future__ import annotations

import pytest

from src.alerting.models import AlertEvent, AlertLevel
from src.alerting.notifiers import (
    AlertNotifier,
    ConsoleNotifier,
    MemoryNotifier,
    CompositeNotifier,
)


class TestConsoleNotifier:
    """测试 ConsoleNotifier。"""

    @pytest.fixture
    def notifier(self) -> ConsoleNotifier:
        """创建控制台通知器。"""
        return ConsoleNotifier(colorize=False)

    @pytest.fixture
    def alert(self) -> AlertEvent:
        """创建测试告警。"""
        return AlertEvent(
            level=AlertLevel.WARNING,
            title="数据过期",
            message="数据超过 24 小时未更新",
        )

    @pytest.mark.asyncio
    async def test_send_alert(self, notifier: ConsoleNotifier, alert: AlertEvent) -> None:
        """测试发送告警（无异常）。"""
        await notifier.send(alert)  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_send_critical_alert(self, alert: AlertEvent) -> None:
        """测试发送严重告警。"""
        alert.level = AlertLevel.CRITICAL
        alert.title = "严重错误"
        notifier = ConsoleNotifier(colorize=False)
        await notifier.send(alert)


class TestMemoryNotifier:
    """测试 MemoryNotifier。"""

    @pytest.fixture
    def notifier(self) -> MemoryNotifier:
        """创建内存通知器。"""
        return MemoryNotifier()

    @pytest.fixture
    def alert(self) -> AlertEvent:
        """创建测试告警。"""
        return AlertEvent(
            level=AlertLevel.WARNING,
            title="测试告警",
            message="测试消息",
        )

    @pytest.mark.asyncio
    async def test_send_and_get(self, notifier: MemoryNotifier, alert: AlertEvent) -> None:
        """测试发送和获取告警。"""
        await notifier.send(alert)

        alerts = notifier.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].title == "测试告警"

    @pytest.mark.asyncio
    async def test_send_batch(self, notifier: MemoryNotifier) -> None:
        """测试批量发送。"""
        alerts = [
            AlertEvent(level=AlertLevel.INFO, title=f"Alert {i}", message=f"Msg {i}")
            for i in range(3)
        ]
        await notifier.send_batch(alerts)

        assert notifier.count == 3

    @pytest.mark.asyncio
    async def test_clear(self, notifier: MemoryNotifier) -> None:
        """测试清空告警。"""
        await notifier.send_batch([
            AlertEvent(level=AlertLevel.WARNING, title="A", message=""),
            AlertEvent(level=AlertLevel.CRITICAL, title="B", message=""),
        ])
        assert notifier.count == 2

        notifier.clear()
        assert notifier.count == 0

    def test_filter_by_level(self, notifier: MemoryNotifier) -> None:
        """测试按级别过滤。"""
        notifier._alerts.extend([
            AlertEvent(level=AlertLevel.INFO, title="Info", message=""),
            AlertEvent(level=AlertLevel.WARNING, title="Warn", message=""),
            AlertEvent(level=AlertLevel.CRITICAL, title="Crit", message=""),
        ])

        warnings = notifier.filter_by_level(AlertLevel.WARNING)
        assert len(warnings) == 1
        assert warnings[0].title == "Warn"


class TestCompositeNotifier:
    """测试 CompositeNotifier。"""

    @pytest.mark.asyncio
    async def test_send_to_multiple(self) -> None:
        """测试向多个通知器发送。"""
        notifier1 = MemoryNotifier()
        notifier2 = MemoryNotifier()

        composite = CompositeNotifier([notifier1, notifier2])

        alert = AlertEvent(
            level=AlertLevel.WARNING,
            title="Composite Test",
            message="Testing",
        )
        await composite.send(alert)

        assert notifier1.count == 1
        assert notifier2.count == 1

    @pytest.mark.asyncio
    async def test_send_batch_to_multiple(self) -> None:
        """测试批量发送到多个通知器。"""
        notifier1 = MemoryNotifier()
        notifier2 = MemoryNotifier()

        composite = CompositeNotifier([notifier1, notifier2])

        alerts = [
            AlertEvent(level=AlertLevel.INFO, title=f"Alert {i}", message=f"Msg {i}")
            for i in range(2)
        ]
        await composite.send_batch(alerts)

        assert notifier1.count == 2
        assert notifier2.count == 2


class TestAlertNotifierAbstract:
    """测试 AlertNotifier 是抽象类。"""

    def test_cannot_instantiate_directly(self) -> None:
        """测试不能直接实例化抽象类。"""
        with pytest.raises(TypeError):
            AlertNotifier()  # type: ignore[abstract]
