from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


def test_market_snapshot_serializes_sections() -> None:
    """MarketSnapshot 应能稳定序列化嵌套 sections。"""
    from src.models.market_snapshot import MarketSnapshot, MarketSnapshotSection

    snapshot = MarketSnapshot(
        snapshot_id="snapshot-2026-05-16",
        trade_date="2026-05-16",
        market="CN",
        data_version="v1",
        provider_sources=["kaipan", "market"],
        created_at=datetime(2026, 5, 16, 8, 0),
        data_quality={"overall": "partial"},
        sections={
            "overview": MarketSnapshotSection(
                section_id="overview",
                provider="kaipan",
                source_time=datetime(2026, 5, 16, 8, 0),
                record_count=3,
                missing_reason=None,
                quality_status="ok",
                payload={"sentiment": 56, "capacity": 23417, "indices": []},
            ),
        },
    )

    data = snapshot.to_dict()
    assert data["snapshot_id"] == "snapshot-2026-05-16"
    assert data["sections"]["overview"]["quality_status"] == "ok"
    assert data["sections"]["overview"]["record_count"] == 3
    assert data["provider_sources"] == ["kaipan", "market"]


def test_market_snapshot_section_summary_reports_missing_reason() -> None:
    """MarketSnapshotSection 应暴露可读摘要。"""
    from src.models.market_snapshot import MarketSnapshotSection

    section = MarketSnapshotSection(
        section_id="auction",
        provider=None,
        source_time=None,
        record_count=0,
        missing_reason="provider unavailable",
        quality_status="missing",
        payload={},
    )

    data = section.to_dict()
    assert data["section_id"] == "auction"
    assert data["missing_reason"] == "provider unavailable"
    assert data["quality_status"] == "missing"


@dataclass(frozen=True)
class _FakeBuilder:
    section_id: str

    def build(self, context):  # pragma: no cover - shape checked by registry tests
        raise RuntimeError("not used in this test")
