"""Alert Channel Formatter 测试（S7-007）。"""
import pytest
import json

from src.alerting.models import AlertEvent, AlertLevel
from src.alerting.channels import (
    ChannelFormatter,
    DingTalkFormatter,
    FeishuFormatter,
    WeComFormatter,
    GenericFormatter,
    get_formatter,
)


@pytest.fixture
def sample_alert():
    return AlertEvent(
        id="test-001",
        level=AlertLevel.WARNING,
        title="快照构建失败",
        message="Connection timeout",
        tags=["snapshot", "missing"],
        metadata={"slot": "17-30", "trade_date": "2026-04-29", "provider": "kaipan"},
    )


@pytest.fixture
def aggregated_alert():
    """聚合告警 fixture"""
    alert = AlertEvent(
        id="test-agg-001",
        level=AlertLevel.WARNING,
        title="Provider 失败聚合",
        message="多次连接失败",
        tags=["provider", "kaipan"],
        metadata={
            "aggregated_count": 12,
            "aggregation_window_start": "2026-04-29T16:00:00",
            "aggregation_window_end": "2026-04-29T17:00:00",
            "last_error": "Connection timeout",
            "provider": "kaipan",
        },
    )
    return alert


class TestDingTalkFormatter:
    def test_format_generates_markdown(self, sample_alert):
        formatter = DingTalkFormatter()
        payload = formatter.format(sample_alert)

        assert "[WARNING] 快照构建失败" in payload
        assert "slot" in payload
        assert "17-30" in payload
        assert "Connection timeout" in payload

    def test_format_includes_tags(self, sample_alert):
        formatter = DingTalkFormatter()
        payload = formatter.format(sample_alert)

        assert "`snapshot`" in payload
        assert "`missing`" in payload

    def test_format_aggregated(self, aggregated_alert):
        formatter = DingTalkFormatter()
        payload = formatter.format_aggregated(aggregated_alert)

        assert "聚合" in payload
        assert "12" in payload
        assert "Connection timeout" in payload


class TestFeishuFormatter:
    def test_format_generates_markdown(self, sample_alert):
        formatter = FeishuFormatter()
        payload = formatter.format(sample_alert)

        assert "[WARNING]" in payload
        assert "快照构建失败" in payload

    def test_format_aggregated(self, aggregated_alert):
        formatter = FeishuFormatter()
        payload = formatter.format_aggregated(aggregated_alert)

        assert "聚合" in payload


class TestWeComFormatter:
    def test_format_generates_markdown(self, sample_alert):
        formatter = WeComFormatter()
        payload = formatter.format(sample_alert)

        assert "[WARNING]" in payload
        assert "快照构建失败" in payload


class TestGenericFormatter:
    def test_format_generates_json(self, sample_alert):
        formatter = GenericFormatter()
        payload = formatter.format(sample_alert)

        parsed = json.loads(payload)
        assert parsed["id"] == "test-001"
        assert parsed["level"] == "WARNING"
        assert parsed["title"] == "快照构建失败"
        assert parsed["message"] == "Connection timeout"

    def test_roundtrip(self, sample_alert):
        formatter = GenericFormatter()
        payload = formatter.format(sample_alert)
        parsed = json.loads(payload)

        assert parsed["tags"] == ["snapshot", "missing"]
        assert parsed["metadata"]["slot"] == "17-30"


class TestGetFormatter:
    def test_dingtalk(self):
        f = get_formatter("dingtalk")
        assert isinstance(f, DingTalkFormatter)

    def test_feishu(self):
        f = get_formatter("feishu")
        assert isinstance(f, FeishuFormatter)

    def test_wecom(self):
        f = get_formatter("wecom")
        assert isinstance(f, WeComFormatter)

    def test_generic(self):
        f = get_formatter("generic")
        assert isinstance(f, GenericFormatter)

    def test_case_insensitive(self):
        f = get_formatter("DingTalk")
        assert isinstance(f, DingTalkFormatter)

    def test_unknown_raises(self):
        with pytest.raises(ValueError) as exc:
            get_formatter("unknown_channel")
        assert "unknown_channel" in str(exc.value)
