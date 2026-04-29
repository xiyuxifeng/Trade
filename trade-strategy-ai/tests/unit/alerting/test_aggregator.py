"""AlertAggregator 测试（S7-007）。"""
import copy
import pytest
from datetime import datetime, timedelta, timezone

from src.alerting.models import AlertEvent, AlertLevel
from src.alerting.aggregator import AlertAggregator


def make_alert(
    id: str = "test-001",
    level: AlertLevel = AlertLevel.WARNING,
    title: str = "Provider 失败",
    message: str = "Connection timeout",
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> AlertEvent:
    return AlertEvent(
        id=id,
        level=level,
        title=title,
        message=message,
        tags=tags or ["provider", "kaipan"],
        metadata=metadata or {"provider": "kaipan", "capability": "hot_topics", "rule_name": "provider_failure"},
    )


class TestAlertAggregator:
    def test_aggregation_key_deterministic(self):
        alert = make_alert()
        agg = AlertAggregator(window_minutes=60)
        key1 = agg._make_aggregation_key(alert)
        key2 = agg._make_aggregation_key(alert)
        assert key1 == key2

    def test_different_tags_different_key(self):
        agg = AlertAggregator(window_minutes=60)
        alert1 = make_alert(tags=["provider", "kaipan"])
        alert2 = make_alert(tags=["provider", "akshare"])

        key1 = agg._make_aggregation_key(alert1)
        key2 = agg._make_aggregation_key(alert2)
        assert key1 != key2

    def test_add_alert_returns_true_when_not_full(self):
        agg = AlertAggregator(window_minutes=60, max_count=10)
        result = agg.add_alert(make_alert())
        assert result is True

    def test_add_alert_returns_false_when_max_reached(self):
        agg = AlertAggregator(window_minutes=60, max_count=3)

        for i in range(3):
            alert = make_alert(id=f"test-{i}")
            result = agg.add_alert(alert)

        # 第3条触发 flush，返回 False
        assert result is False

    def test_flush_emits_aggregated_alert(self):
        agg = AlertAggregator(window_minutes=60)

        flushed = []
        def mock_emit(alert):
            flushed.append(alert)

        for i in range(5):
            alert = make_alert(id=f"test-{i}", message=f"error-{i}")
            agg.add_alert(alert)

        agg.flush(emit_fn=mock_emit)

        assert len(flushed) == 1
        assert flushed[0].metadata["aggregated_count"] == 5
        assert flushed[0].metadata["last_error"] == "error-4"

    def test_flush_all_keys(self):
        agg = AlertAggregator(window_minutes=60)

        flushed = []
        def mock_emit(alert):
            flushed.append(alert)

        alert1 = make_alert(id="a1", tags=["provider", "kaipan"])
        alert2 = make_alert(id="a2", tags=["provider", "akshare"])

        agg.add_alert(alert1)
        agg.add_alert(alert2)
        agg.flush(emit_fn=mock_emit)

        assert len(flushed) == 2

    def test_empty_bucket_not_flushed(self):
        agg = AlertAggregator(window_minutes=60)
        flushed = []
        agg.flush(emit_fn=lambda a: flushed.append(a))
        assert len(flushed) == 0

    def test_metadata_rule_name_used_in_key(self):
        alert = make_alert(metadata={"rule_name": "my_rule", "tags": []})
        agg = AlertAggregator(window_minutes=60)
        key = agg._make_aggregation_key(alert)
        assert key is not None

    def test_new_window_after_cooldown(self):
        agg = AlertAggregator(window_minutes=60)
        alert1 = make_alert()
        key = agg._make_aggregation_key(alert1)

        agg.add_alert(alert1)
        assert len(agg.buckets[key]["alerts"]) == 1

        # 模拟时间穿越：last_sent_at 超过窗口
        old_time = datetime.now(timezone.utc) - timedelta(minutes=120)
        agg.buckets[key]["last_sent_at"] = old_time
        agg.buckets[key]["window_start"] = old_time

        # 新告警进入新窗口
        new_alert = make_alert(id="test-new")
        agg.add_alert(new_alert)

        # 新窗口只有新的一条
        assert len(agg.buckets[key]["alerts"]) == 1

    def test_flush_with_specific_key(self):
        agg = AlertAggregator(window_minutes=60)
        key1_alert = make_alert(id="k1", tags=["type", "a"])
        key2_alert = make_alert(id="k2", tags=["type", "b"])

        key1 = agg._make_aggregation_key(key1_alert)

        agg.add_alert(key1_alert)
        agg.add_alert(key2_alert)

        flushed = []
        agg.flush(key=key1, emit_fn=lambda a: flushed.append(a))

        # 只 flush 了 key1
        assert len(flushed) == 1
        assert agg.buckets[key1]["alerts"] == []  # key1 已清空
        assert len(agg.buckets[agg._make_aggregation_key(key2_alert)]["alerts"]) == 1  # key2 还在
