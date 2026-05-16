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
    provider: str | None
    source_time: datetime | None
    record_count: int
    missing_reason: str | None
    quality_status: str
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
    market: str
    data_version: str
    provider_sources: list[str]
    created_at: datetime
    data_quality: dict[str, Any]
    sections: dict[str, MarketSnapshotSection]
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
