"""单元测试 - 告警数据模型。"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
import pytest

from src.alerting.models import AlertEvent, AlertLevel, AlertRule, create_alert


class TestAlertLevel:
    """测试 AlertLevel 枚举。"""

    def test_alert_level_values(self) -> None:
        """测试告警级别值。"""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.CRITICAL.value == "critical"

    def test_alert_level_str(self) -> None:
        """测试告警级别字符串表示。"""
        assert str(AlertLevel.INFO) == "INFO"
        assert str(AlertLevel.WARNING) == "WARNING"
        assert str(AlertLevel.CRITICAL) == "CRITICAL"


class TestAlertEvent:
    """测试 AlertEvent 数据类。"""

    def test_create_basic_alert(self) -> None:
        """测试创建基本告警。"""
        alert = AlertEvent(
            level=AlertLevel.WARNING,
            title="数据过期",
            message="数据超过 24 小时未更新",
        )

        assert alert.level == AlertLevel.WARNING
        assert alert.title == "数据过期"
        assert alert.message == "数据超过 24 小时未更新"
        assert alert.source == "AlertManager"
        assert isinstance(alert.id, str)
        assert isinstance(alert.timestamp, datetime)

    def test_create_alert_with_metadata(self) -> None:
        """测试创建带元数据的告警。"""
        alert = AlertEvent(
            level=AlertLevel.CRITICAL,
            title="异常率过高",
            message="异常率 15.5% 超过阈值",
            metadata={"anomaly_rate": 15.5, "threshold": 5.0},
            tags=["quality", "critical"],
        )

        assert alert.metadata["anomaly_rate"] == 15.5
        assert "quality" in alert.tags
        assert "critical" in alert.tags

    def test_to_dict(self) -> None:
        """测试转换为字典。"""
        alert = AlertEvent(
            level=AlertLevel.WARNING,
            title="测试",
            message="测试消息",
        )
        d = alert.to_dict()

        assert d["level"] == "WARNING"
        assert d["title"] == "测试"
        assert d["message"] == "测试消息"
        assert d["source"] == "AlertManager"
        assert "id" in d
        assert "timestamp" in d

    def test_matches_tags(self) -> None:
        """测试标签匹配。"""
        alert = AlertEvent(
            level=AlertLevel.WARNING,
            title="测试",
            message="测试",
            tags=["data", "freshness"],
        )

        assert alert.matches_tags(["data"]) is True
        assert alert.matches_tags(["quality"]) is False
        assert alert.matches_tags([]) is True  # 空列表匹配所有
        assert alert.matches_tags(["data", "quality"]) is True  # 匹配任一


class TestAlertRule:
    """测试 AlertRule 数据类。"""

    def test_create_rule(self) -> None:
        """测试创建规则。"""
        def condition(stats: object, quality: object) -> bool:
            return True

        rule = AlertRule(
            name="test_rule",
            condition=condition,
            level=AlertLevel.WARNING,
            title="测试规则",
            message_template="测试消息 {value}",
            cooldown_seconds=300,
        )

        assert rule.name == "test_rule"
        assert rule.level == AlertLevel.WARNING
        assert rule.cooldown_seconds == 300
        assert rule.enabled is True

    def test_rule_evaluate(self) -> None:
        """测试规则评估。"""
        def condition(stats: object, quality: object) -> bool:
            return True

        rule = AlertRule(
            name="test_rule",
            condition=condition,
            level=AlertLevel.WARNING,
            title="测试规则",
            message_template="value={value}",
        )

        triggered, message = rule.evaluate(None, None, value=42)
        assert triggered is True
        assert message == "value=42"

    def test_rule_disabled(self) -> None:
        """测试禁用规则。"""
        rule = AlertRule(
            name="test_rule",
            condition=lambda s, q: True,
            level=AlertLevel.WARNING,
            title="测试",
            message_template="test",
            enabled=False,
        )

        assert rule.is_enabled() is False


class TestCreateAlert:
    """测试 create_alert 函数。"""

    def test_create_alert_from_rule(self) -> None:
        """测试从规则创建告警。"""
        rule = AlertRule(
            name="test_rule",
            condition=lambda s, q: True,
            level=AlertLevel.CRITICAL,
            title="测试规则",
            message_template="异常率 {rate}%",
            tags=["test"],
        )

        alert = create_alert(
            rule=rule,
            message="异常率 15%",
            metadata={"rate": 15},
        )

        assert alert.level == AlertLevel.CRITICAL
        assert alert.title == "测试规则"
        assert alert.message == "异常率 15%"
        assert alert.metadata["rate"] == 15
        assert "test" in alert.tags

    def test_create_alert_override_level(self) -> None:
        """测试创建告警时覆盖级别。"""
        rule = AlertRule(
            name="test_rule",
            condition=lambda s, q: True,
            level=AlertLevel.WARNING,
            title="测试",
            message_template="test",
        )

        alert = create_alert(rule=rule, level=AlertLevel.CRITICAL)

        assert alert.level == AlertLevel.CRITICAL
