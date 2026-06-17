from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


def test_market_snapshot_serializes_sections() -> None:
    """MarketSnapshot 应能稳定序列化嵌套 sections。"""
    from src.models.market_snapshot import MarketSnapshot, MarketSnapshotSection

    snapshot = MarketSnapshot(
        snapshot_id="snapshot-2026-05-16",
        trade_date="2026-05-16",
        slot="17-30",
        market="CN",
        data_version="v1",
        provider_sources=["kaipan", "market"],
        source_time=datetime(2026, 5, 16, 17, 30, tzinfo=UTC),
        captured_at=datetime(2026, 5, 16, 17, 31, tzinfo=UTC),
        ingested_at=datetime(2026, 5, 16, 17, 32, tzinfo=UTC),
        available_at=datetime(2026, 5, 16, 17, 30, tzinfo=UTC),
        frozen_at=datetime(2026, 5, 16, 17, 33, tzinfo=UTC),
        content_fingerprint="fingerprint-001",
        data_quality={"overall": "partial"},
        sections={
            "overview": MarketSnapshotSection(
                section_id="overview",
                trade_date="2026-05-16",
                slot="17-30",
                source_dataset="market_context",
                provider="kaipan",
                source_time=datetime(2026, 5, 16, 17, 30, tzinfo=UTC),
                captured_at=datetime(2026, 5, 16, 17, 31, tzinfo=UTC),
                ingested_at=datetime(2026, 5, 16, 17, 32, tzinfo=UTC),
                available_at=datetime(2026, 5, 16, 17, 30, tzinfo=UTC),
                record_count=3,
                missing_reason=None,
                quality_status="ok",
                raw_payload_fingerprint="raw-001",
                normalization_version="kaipan-normalizer-v2",
                payload={"sentiment": 56, "capacity": 23417, "indices": []},
            ),
        },
        storage_ref={"logical_snapshot_id": "kaipan:CN:2026-05-16:17-30"},
    )

    data = snapshot.to_dict()
    assert data["snapshot_id"] == "snapshot-2026-05-16"
    assert data["slot"] == "17-30"
    assert data["content_fingerprint"] == "fingerprint-001"
    assert data["sections"]["overview"]["quality_status"] == "ok"
    assert data["sections"]["overview"]["record_count"] == 3
    assert data["sections"]["overview"]["slot"] == "17-30"
    assert data["sections"]["overview"]["raw_payload_fingerprint"] == "raw-001"
    assert data["provider_sources"] == ["kaipan", "market"]


def test_market_snapshot_section_summary_reports_missing_reason() -> None:
    """MarketSnapshotSection 应暴露可读摘要。"""
    from src.models.market_snapshot import MarketSnapshotSection

    section = MarketSnapshotSection(
        section_id="auction",
        trade_date="2026-05-16",
        slot="09-25",
        source_dataset="pre_market_stats",
        provider=None,
        source_time=None,
        captured_at=None,
        ingested_at=None,
        available_at=None,
        record_count=0,
        missing_reason="provider unavailable",
        quality_status="missing",
        raw_payload_fingerprint=None,
        normalization_version="kaipan-normalizer-v2",
        payload={},
    )

    data = section.to_dict()
    assert data["section_id"] == "auction"
    assert data["slot"] == "09-25"
    assert data["missing_reason"] == "provider unavailable"
    assert data["quality_status"] == "missing"


@dataclass(frozen=True)
class _FakeBuilder:
    section_id: str

    def build(self, context):  # pragma: no cover - shape checked by registry tests
        raise RuntimeError("not used in this test")
