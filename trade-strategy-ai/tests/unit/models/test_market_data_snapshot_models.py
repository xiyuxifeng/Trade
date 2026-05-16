from __future__ import annotations

from datetime import date, datetime, timezone


def test_market_snapshot_model_defines_expected_identity_and_fields() -> None:
    """市场快照主表应暴露稳定身份字段和聚合字段。"""
    from src.models.market_data_snapshot import MarketSnapshot

    assert MarketSnapshot.__tablename__ == "market_snapshots"
    column_names = set(MarketSnapshot.__table__.columns.keys())
    assert {"snapshot_id", "trade_date", "market", "profile_id", "data_version", "quality_status"}.issubset(column_names)


def test_market_snapshot_section_model_defines_expected_fields() -> None:
    """section 表应支持 snapshot + section 的唯一约束。"""
    from src.models.market_data_snapshot_section import MarketSnapshotSection

    assert MarketSnapshotSection.__tablename__ == "market_snapshot_sections"
    column_names = set(MarketSnapshotSection.__table__.columns.keys())
    assert {"snapshot_id", "section_id", "provider", "record_count", "missing_reason", "quality_status", "payload_json"}.issubset(column_names)


def test_market_snapshot_item_model_defines_query_fields() -> None:
    """item 表应支持 symbol / section / dataset 查询。"""
    from src.models.market_data_snapshot_item import MarketSnapshotItem

    assert MarketSnapshotItem.__tablename__ == "market_snapshot_items"
    column_names = set(MarketSnapshotItem.__table__.columns.keys())
    assert {"snapshot_id", "section_id", "dataset_id", "symbol", "item_key", "payload_json"}.issubset(column_names)


def test_market_dataset_and_quality_report_models_define_safe_refs() -> None:
    """dataset / quality report 表应保留安全引用，不暴露绝对路径。"""
    from src.models.market_dataset import MarketDataset
    from src.models.market_data_quality_report import MarketDataQualityReport

    assert MarketDataset.__tablename__ == "market_datasets"
    assert MarketDataQualityReport.__tablename__ == "market_data_quality_reports"
    assert "storage_ref" in MarketDataset.__table__.columns.keys()
    assert "storage_ref" in MarketDataQualityReport.__table__.columns.keys()


def test_market_data_models_to_dict_are_json_compatible() -> None:
    """模型应支持 JSON 兼容字典输出。"""
    from src.models.market_data_snapshot import MarketSnapshot
    from src.models.market_data_snapshot_section import MarketSnapshotSection

    snapshot = MarketSnapshot(
        snapshot_id="snapshot-2026-05-16",
        trade_date=date(2026, 5, 16),
        market="CN",
        data_version="v1",
        profile_id="default",
        provider_sources=["kaipan"],
        created_at=datetime(2026, 5, 16, 8, 0, tzinfo=timezone.utc),
        data_quality={"overall": "ok"},
    )
    snapshot.sections = [
        MarketSnapshotSection(
            snapshot_id="snapshot-2026-05-16",
            section_id="overview",
            provider="kaipan",
            source_time=datetime(2026, 5, 16, 8, 0, tzinfo=timezone.utc),
            record_count=1,
            missing_reason=None,
            quality_status="ok",
            payload_json={"sentiment": 55},
        )
    ]

    data = snapshot.to_dict()
    assert data["snapshot_id"] == "snapshot-2026-05-16"
    assert data["sections"]["overview"]["quality_status"] == "ok"
    assert data["data_quality"] == {"overall": "ok"}
