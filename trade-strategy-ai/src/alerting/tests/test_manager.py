"""单元测试 - 告警管理器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
import pytest

from src.alerting.models import AlertEvent, AlertLevel, AlertRule
from src.alerting.notifiers import MemoryNotifier
from src.alerting.manager import AlertManager


@dataclass
class MockEntityStats:
    """模拟实体统计。"""
    total: int = 0
    freshness_hours: float | None = None
    by_type: dict[str, int] = field(default_factory=dict)
    unique_symbols: int = 0


@dataclass
class MockDashboardStats:
    """模拟 Dashboard 统计。"""
    articles: MockEntityStats = field(default_factory=MockEntityStats)
    trades: MockEntityStats = field(default_factory=MockEntityStats)
    market_data: MockEntityStats = field(default_factory=MockEntityStats)


@dataclass
class MockQualityMetrics:
    """模拟数据质量指标。"""
    total_issues: int = 0
    article_dup_count: int = 0


class TestAlertManager:
    """测试 AlertManager。"""

    @pytest.fixture
    def stats(self) -> MockDashboardStats:
        """创建测试统计数据。"""
        return MockDashboardStats(
            articles=MockEntityStats(total=100, freshness_hours=48.0),
            trades=MockEntityStats(total=100, freshness_hours=12.0, by_type={"buy": 50, "sell": 50}),
            market_data=MockEntityStats(total=50, freshness_hours=1.0),
        )

    @pytest.fixture
    def quality(self) -> MockQualityMetrics:
        """创建测试质量指标。"""
        return MockQualityMetrics(total_issues=5, article_dup_count=2)

    @pytest.fixture
    def memory_notifier(self) -> MemoryNotifier:
        """创建内存通知器。"""
        return MemoryNotifier()

    @pytest.fixture
    def manager(self, memory_notifier: MemoryNotifier) -> AlertManager:
        """创建告警管理器。"""
        rules = [
            AlertRule(
                name="articles_stale",
                condition=lambda stats, _: (stats.articles.freshness_hours or 0) > 24,
                level=AlertLevel.WARNING,
                title="文章数据过期",
                message_template="文章数据超过 {articles_freshness:.1f} 小时",
                cooldown_seconds=0,  # 禁用冷却以便测试
            ),
            AlertRule(
                name="high_buy_ratio",
                condition=lambda stats, _: (
                    stats.trades.total > 0 and
                    stats.trades.by_type.get("buy", 0) / stats.trades.total > 0.7
                ),
                level=AlertLevel.INFO,
                title="买入比例偏高",
                message_template="买入比例 {buy_ratio:.0f}%",
                cooldown_seconds=0,
            ),
            AlertRule(
                name="no_market_data",
                condition=lambda stats, _: stats.market_data.total == 0,
                level=AlertLevel.CRITICAL,
                title="无市场数据",
                message_template="市场数据缺失",
                cooldown_seconds=0,
            ),
        ]
        return AlertManager(rules=rules, notifiers=[memory_notifier])

    @pytest.mark.asyncio
    async def test_evaluate_triggers_alert(self, manager: AlertManager, stats: MockDashboardStats, quality: MockQualityMetrics) -> None:
        """测试评估触发告警。"""
        alerts = await manager.evaluate(stats, quality)

        # 应该触发 articles_stale (freshness_hours=48 > 24)
        assert len(alerts) == 1
        assert alerts[0].title == "文章数据过期"

    @pytest.mark.asyncio
    async def test_evaluate_no_trigger(self, manager: AlertManager, stats: MockDashboardStats, quality: MockQualityMetrics) -> None:
        """测试评估不触发告警。"""
        # 修改数据使得不触发任何告警
        stats.articles.freshness_hours = 12.0
        stats.trades.by_type = {"buy": 5, "sell": 5}
        stats.market_data.total = 10

        alerts = await manager.evaluate(stats, quality)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_evaluate_and_notify(self, manager: AlertManager, memory_notifier: MemoryNotifier, stats: MockDashboardStats, quality: MockQualityMetrics) -> None:
        """测试评估并发送通知。"""
        alerts = await manager.evaluate_and_notify(stats, quality)

        # 验证告警已发送
        assert memory_notifier.count == 1
        stored = memory_notifier.get_alerts()[0]
        assert stored.title == "文章数据过期"

    @pytest.mark.asyncio
    async def test_cooldown(self, manager: AlertManager, stats: MockDashboardStats, quality: MockQualityMetrics) -> None:
        """测试冷却时间。"""
        # 第一次评估
        alerts1 = await manager.evaluate(stats, quality)
        assert len(alerts1) == 1

        # 第二次评估应该被冷却
        alerts2 = await manager.evaluate(stats, quality)
        assert len(alerts2) == 0  # 被冷却

    @pytest.mark.asyncio
    async def test_statistics(self, manager: AlertManager, stats: MockDashboardStats, quality: MockQualityMetrics) -> None:
        """测试统计信息。"""
        await manager.evaluate_and_notify(stats, quality)

        stats_info = manager.get_statistics()
        assert stats_info["total_rules"] == 3
        assert stats_info["enabled_rules"] == 3
        assert "articles_stale" in stats_info["alert_counts"]

    def test_get_rule(self, manager: AlertManager) -> None:
        """测试获取规则。"""
        rule = manager.get_rule("articles_stale")
        assert rule is not None
        assert rule.name == "articles_stale"

        nonexistent = manager.get_rule("nonexistent")
        assert nonexistent is None

    def test_enable_disable_rule(self, manager: AlertManager) -> None:
        """测试启用/禁用规则。"""
        result = manager.disable_rule("articles_stale")
        assert result is True
        assert manager.get_rule("articles_stale").enabled is False

        result = manager.enable_rule("articles_stale")
        assert result is True
        assert manager.get_rule("articles_stale").enabled is True

    def test_add_rule(self, manager: AlertManager) -> None:
        """测试添加规则。"""
        new_rule = AlertRule(
            name="new_rule",
            condition=lambda s, q: True,
            level=AlertLevel.INFO,
            title="新规则",
            message_template="新规则触发",
        )
        manager.add_rule(new_rule)

        assert manager.get_rule("new_rule") is not None
        assert len(manager.rules) == 4

    def test_remove_rule(self, manager: AlertManager) -> None:
        """测试移除规则。"""
        result = manager.remove_rule("articles_stale")
        assert result is True
        assert manager.get_rule("articles_stale") is None
        assert len(manager.rules) == 2

    def test_reset_cooldowns(self, manager: AlertManager, stats: MockDashboardStats, quality: MockQualityMetrics) -> None:
        """测试重置冷却时间。"""
        # 触发一次告警
        import asyncio
        asyncio.run(manager.evaluate(stats, quality))

        # 重置冷却
        manager.reset_cooldowns()

        # 再次评估应该触发
        alerts = asyncio.run(manager.evaluate(stats, quality))
        assert len(alerts) == 1

    def test_get_enabled_rules(self, manager: AlertManager) -> None:
        """测试获取已启用规则。"""
        manager.disable_rule("articles_stale")

        enabled = manager.get_enabled_rules()
        assert len(enabled) == 2
        assert all(r.enabled for r in enabled)


class TestAlertManagerNoNotifiers:
    """测试不带通知器的 AlertManager。"""

    @pytest.mark.asyncio
    async def test_evaluate_without_notifiers(self) -> None:
        """测试不带通知器也能正常工作。"""
        rules = [
            AlertRule(
                name="always_trigger",
                condition=lambda s, q: True,
                level=AlertLevel.WARNING,
                title="总是触发",
                message_template="测试",
            ),
        ]
        manager = AlertManager(rules=rules, notifiers=[])

        stats = MockDashboardStats()
        quality = MockQualityMetrics()

        alerts = await manager.evaluate_and_notify(stats, quality)
        assert len(alerts) == 1
