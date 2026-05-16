from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class _FakeBuilder:
    section_id: str

    def build(self, context):  # pragma: no cover - registry only checks interface
        from src.models.market_snapshot import MarketSnapshotSection

        return MarketSnapshotSection(
            section_id=self.section_id,
            provider="fake",
            source_time=datetime(2026, 5, 16, 8, 0),
            record_count=1,
            missing_reason=None,
            quality_status="ok",
            payload={"section_id": self.section_id},
        )


def test_registry_can_register_and_resolve_builders() -> None:
    """Registry 应支持注册与解析 section builder。"""
    from src.services.market_snapshot_registry import MarketSnapshotRegistry

    registry = MarketSnapshotRegistry()
    registry.register(_FakeBuilder("overview"))

    builder = registry.get("overview")
    assert builder is not None
    assert builder.section_id == "overview"


def test_registry_preserves_deterministic_order() -> None:
    """Registry 的顺序应与注册顺序一致，便于稳定输出。"""
    from src.services.market_snapshot_registry import MarketSnapshotRegistry

    registry = MarketSnapshotRegistry()
    registry.register(_FakeBuilder("overview"))
    registry.register(_FakeBuilder("auction"))

    assert [builder.section_id for builder in registry.items()] == ["overview", "auction"]
