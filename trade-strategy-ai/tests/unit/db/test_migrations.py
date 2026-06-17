from __future__ import annotations

from pathlib import Path


def test_job_audit_events_migration_defines_expected_schema() -> None:
    """验证 Job 审计表迁移定义与约定一致。"""
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_05_10_0002_add_job_audit_events.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert "revision = \"2026_05_10_0002\"" in content
    assert "down_revision = \"2026_05_08_0001\"" in content
    assert "job_audit_events" in content
    assert "job_id" in content
    assert "params_summary" in content
    assert "source" in content
    assert "event_at" in content
    assert "ix_job_audit_events_job_id_created_at" in content
    assert "ix_job_audit_events_operation_created_at" in content


def test_market_regimes_migration_defines_expected_schema() -> None:
    """验证 Market Regime 迁移定义与约定一致。"""
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_05_18_0001_add_market_regimes_table.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision: str = "2026_05_18_0001"' in content
    assert 'down_revision: Union[str, None] = "2026_05_17_0001"' in content
    assert "market_regimes" in content
    assert "uq_market_regimes_snapshot_regime_version" in content
    assert "source_feature_version" in content
    assert "primary_label" in content
    assert "labels_json" in content
    assert "features_json" in content


def test_stage2_migration_chain_defines_linear_metadata_schema_and_compatibility_steps() -> None:
    """验证 RT-S2-002 线性迁移链文件存在且包含冻结关键动作。"""
    base_dir = Path(__file__).parent.parent.parent.parent / "src/db/migrations/versions"

    metadata_file = base_dir / "2026_06_14_0002_stage2_metadata_alignment.py"
    domain_file = base_dir / "2026_06_14_0003_stage2_domain_schema.py"
    compatibility_file = base_dir / "2026_06_14_0004_stage2_compatibility_views.py"

    metadata = metadata_file.read_text(encoding="utf-8")
    domain = domain_file.read_text(encoding="utf-8")
    compatibility = compatibility_file.read_text(encoding="utf-8")

    assert 'revision = "2026_06_14_0002"' in metadata
    assert 'down_revision = "2026_06_03_0001"' in metadata
    assert "alert_history" in metadata
    assert "trade_logs" in metadata

    assert 'revision = "2026_06_14_0003"' in domain
    assert 'down_revision = "2026_06_14_0002"' in domain
    assert "prompt_runs" in domain
    assert "legacy_id_mappings" in domain
    assert "article_structures" in domain
    assert "rule_versions" in domain
    assert "author_profile_versions" in domain
    assert "daily_rule_selections" in domain

    assert 'revision = "2026_06_14_0004"' in compatibility
    assert 'down_revision = "2026_06_14_0003"' in compatibility
    assert "strategy_regime_selections" in compatibility
    assert "regime_rule_selections" in compatibility
    assert "market_datasets" in compatibility
    assert "CREATE VIEW" in compatibility or "create_view" in compatibility.lower()


def test_stage5_ohlcv_contract_migration_defines_identity_and_time_fields() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_06_17_0008_stage5_ohlcv_contract.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision: str = "2026_06_17_0008"' in content
    assert 'down_revision: Union[str, None] = "2026_06_16_0007"' in content
    assert "uq_ohlcv_identity_trade_date" in content
    assert "source_symbol" in content
    assert "adjustment_policy" in content
    assert "available_at" in content
    assert "captured_at" in content
    assert "ingested_at" in content


def test_stage5_kaipan_contract_migration_defines_slot_provenance_and_freeze_fields() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_06_17_0009_stage5_kaipan_contract.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision: str = "2026_06_17_0009"' in content
    assert 'down_revision: Union[str, None] = "2026_06_17_0008"' in content
    assert "source_time" in content
    assert "frozen_at" in content
    assert "trade_date" in content
    assert "source_dataset" in content
    assert "raw_payload_fingerprint" in content
    assert "normalization_version" in content
    assert "uq_market_snapshots_market_date_slot_version" in content
