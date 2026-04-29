"""告警聚合器（S7-007）。

同一 aggregation_key 在时间窗口内的多条告警合并成一条发送。
"""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Callable

from src.alerting.models import AlertEvent


class AlertAggregator:
    """告警聚合器。

    同一 aggregation_key（规则名 + tags）在窗口时间内多条告警合并为一条。
    """

    def __init__(
        self,
        window_minutes: int = 60,
        max_count: int = 100,
    ) -> None:
        self.window_minutes = window_minutes
        self.max_count = max_count
        # buckets[key] = {"alerts": [], "window_start": datetime, "last_sent_at": datetime}
        self.buckets: dict[str, dict] = {}

    def _make_aggregation_key(self, alert: AlertEvent) -> str:
        """生成告警的 aggregation_key。"""
        rule_name = alert.metadata.get("rule_name", "default") if alert.metadata else "default"
        sorted_tags = sorted(alert.tags) if alert.tags else []
        tags_str = ",".join(sorted_tags)
        raw = f"{rule_name}:{tags_str}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _get_or_create_bucket(self, alert: AlertEvent) -> dict:
        """获取或创建聚合 bucket。"""
        key = self._make_aggregation_key(alert)
        now = datetime.now(timezone.utc)

        if key not in self.buckets:
            self.buckets[key] = {
                "alerts": [],
                "window_start": now,
                "last_sent_at": None,
            }

        bucket = self.buckets[key]

        # 检查是否需要开启新窗口
        if bucket["last_sent_at"] is not None:
            elapsed = now - bucket["last_sent_at"]
            if elapsed >= timedelta(minutes=self.window_minutes):
                # 新窗口开始
                bucket["alerts"] = []
                bucket["window_start"] = now

        return bucket

    def add_alert(self, alert: AlertEvent) -> bool:
        """添加告警到聚合桶。

        Returns:
            True 如果告警被添加到桶中（还未发送）
            False 如果触发了 flush（发送了聚合告警）
        """
        bucket = self._get_or_create_bucket(alert)
        bucket["alerts"].append(alert)

        # 超过 max_count 立即 flush
        if len(bucket["alerts"]) >= self.max_count:
            self.flush(self._make_aggregation_key(alert))
            return False

        return True

    def flush(
        self,
        key: str | None = None,
        emit_fn: Callable[[AlertEvent], None] | None = None,
    ) -> list[AlertEvent]:
        """触发 flush，发送聚合告警。

        Args:
            key: 指定 key（空则 flush 所有）
            emit_fn: 发送回调，接收聚合后的 AlertEvent

        Returns:
            已发送的聚合告警列表
        """
        sent = []
        keys_to_flush = [key] if key else list(self.buckets.keys())

        for k in keys_to_flush:
            if k not in self.buckets:
                continue
            bucket = self.buckets[k]
            if not bucket["alerts"]:
                continue

            now = datetime.now(timezone.utc)
            first = bucket["alerts"][0]
            last = bucket["alerts"][-1]

            # 构建聚合告警
            aggregated = copy.deepcopy(first)
            aggregated.metadata = dict(first.metadata or {})
            aggregated.metadata["aggregated_count"] = len(bucket["alerts"])
            aggregated.metadata["aggregation_window_start"] = bucket["window_start"].isoformat()
            aggregated.metadata["aggregation_window_end"] = now.isoformat()
            aggregated.metadata["last_error"] = last.message or "未知"

            if emit_fn:
                emit_fn(aggregated)

            # 重置 bucket
            bucket["alerts"] = []
            bucket["last_sent_at"] = now

            sent.append(aggregated)

        return sent
