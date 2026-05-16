from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Protocol

from src.models.market_snapshot import MarketSnapshotBuildContext, MarketSnapshotSection


class MarketSnapshotSectionBuilder(Protocol):
    """市场快照 section 构建器协议。"""

    section_id: str

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection: ...


@dataclass
class MarketSnapshotRegistry:
    """按 section_id 管理 Market Snapshot builder。"""

    _builders: OrderedDict[str, MarketSnapshotSectionBuilder] | None = None

    def __post_init__(self) -> None:
        """初始化内部注册表。"""
        if self._builders is None:
            self._builders = OrderedDict()

    def register(self, builder: MarketSnapshotSectionBuilder) -> None:
        """注册一个 section builder。"""
        self._builders[builder.section_id] = builder

    def get(self, section_id: str) -> MarketSnapshotSectionBuilder | None:
        """按 section_id 查找 builder。"""
        return self._builders.get(section_id)

    def items(self) -> list[MarketSnapshotSectionBuilder]:
        """按注册顺序返回所有 builder。"""
        return list(self._builders.values())

    def section_ids(self) -> list[str]:
        """按注册顺序返回所有 section_id。"""
        return list(self._builders.keys())

    def __contains__(self, section_id: object) -> bool:
        """支持 `in` 判断。"""
        return isinstance(section_id, str) and section_id in self._builders

