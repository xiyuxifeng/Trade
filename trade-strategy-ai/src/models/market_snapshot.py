from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@dataclass(frozen=True)
class MarketSnapshotSection:
    """Market Snapshot 的单个 section。"""

    section_id: str
    trade_date: str | None = None
    slot: str | None = None
    source_dataset: str | None = None
    provider: str | None = None
    source_time: datetime | None = None
    captured_at: datetime | None = None
    ingested_at: datetime | None = None
    available_at: datetime | None = None
    record_count: int = 0
    missing_reason: str | None = None
    quality_status: str = "missing"
    raw_payload_fingerprint: str | None = None
    normalization_version: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)


@dataclass(frozen=True)
class MarketSnapshot:
    """结构化市场快照。"""

    snapshot_id: str
    trade_date: str
    slot: str = "17-30"
    market: str = "CN"
    data_version: str = "market-snapshot-v2"
    provider_sources: list[str] = field(default_factory=list)
    source_time: datetime | None = None
    captured_at: datetime | None = None
    ingested_at: datetime | None = None
    available_at: datetime | None = None
    frozen_at: datetime | None = None
    content_fingerprint: str | None = None
    created_at: datetime | None = None
    data_quality: dict[str, Any] = field(default_factory=dict)
    sections: dict[str, MarketSnapshotSection] = field(default_factory=dict)
    storage_ref: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)


@dataclass(frozen=True)
class MarketSnapshotBuildContext:
    """构建 Market Snapshot 时需要的上下文。"""

    config_path: str
    profile_id: str | None
    trade_date: str
    slot: str
    market: str = "CN"
    offline: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """返回 JSON 兼容字典。"""
        return _to_plain(self)
