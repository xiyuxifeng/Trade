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


def test_stage6_backtest_run_contract_migration_defines_immutable_foundation() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_06_18_0010_stage6_backtest_run_foundation.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision: str = "2026_06_18_0010"' in content
    assert 'down_revision: Union[str, None] = "2026_06_17_0009"' in content
    assert "backtest_runs" in content
    assert "rule_version_id" in content
    assert "rule_family_id" in content
    assert "frozen_rule_version_ids" in content
    assert "dataset_snapshot_id" in content
    assert "market_snapshot_ids" in content
    assert "request_fingerprint" in content
    assert "reproducibility_fingerprint" in content
    assert "snapshot_only" in content
    assert "actor_id" in content


def test_stage7_author_profile_version_migration_defines_lifecycle_and_time_segments() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_06_19_0014_stage7_author_profile_versions.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision: str = "2026_06_19_0014"' in content
    assert 'down_revision: Union[str, None] = "2026_06_19_0013"' in content
    assert "pending_review" in content
    assert "evidence_from" in content
    assert "effective_from" in content
    assert "source_versions_json" in content
    assert "evidence_fingerprint" in content
    assert "profile_fingerprint" in content
    assert "author_profile_version_audits" in content
    assert "Refusing to downgrade RT-S7-004" in content
    assert "source_surface" in content
    assert "before_state_json" in content
    assert "after_state_json" in content


def test_stage6_market_state_backtest_result_migration_defines_immutable_metrics() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_06_19_0011_stage6_market_state_backtest_results.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision: str = "2026_06_19_0011"' in content
    assert 'down_revision: Union[str, None] = "2026_06_18_0010"' in content
    assert "backtest_results" in content
    assert "fk_btres_run" in content
    assert "input_fingerprint" in content
    assert "result_fingerprint" in content
    assert "reproducibility_fingerprint" in content
    assert "market_state_model_version" in content
    assert "market_state_source_version" in content
    assert "market_state_result_version" in content
    assert "per_market_state_metrics" in content
    assert "sample_state_counts" in content
    assert "coverage_json" in content
    assert "provenance_json" in content


def test_stage6_backtest_level_policy_migration_defines_downgrade_audit_fields() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_06_19_0012_stage6_backtest_level_policy.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision: str = "2026_06_19_0012"' in content
    assert 'down_revision: Union[str, None] = "2026_06_19_0011"' in content
    assert "level_policy_version" in content
    assert "downgrade_reason" in content
    assert "repair_guidance" in content
    assert "backtest_runs" in content
    assert "backtest_results" in content


def test_stage6_rule_applicability_profile_migration_defines_formal_contract() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_06_19_0013_stage6_rule_applicability_profiles.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision: str = "2026_06_19_0013"' in content
    assert 'down_revision: Union[str, None] = "2026_06_19_0012"' in content
    assert "rule_applicability_profiles" in content
    assert "source_backtest_run_ids" in content
    assert "source_backtest_result_ids" in content
    assert "source_result_fingerprints" in content
    assert '["rule_id", "profile_version", "source_backtest_id", "profile_version_no"]' in content
    assert "rule_version_fingerprint" in content
    assert "rule_family_id" in content
    assert "frozen_rule_version_ids" in content
    assert "requested_level" in content
    assert "effective_level" in content
    assert "level_policy_version" in content
    assert "recommendation_status" in content
    assert "insufficient_sample_status" in content
    assert "supersedes_profile_id" in content
    assert "rule_applicability_profile_audits" in content
    assert "transition" in content
    assert "before_state_json" in content
    assert "after_state_json" in content
    assert "Refusing to downgrade RT-S6-003" in content


def test_stage8_strategy_center_migration_defines_review_and_audit_contract() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_06_20_0001_stage8_strategy_center_foundation.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert 'revision: str = "2026_06_20_0001"' in content
    assert 'down_revision: Union[str, None] = "2026_06_19_0014"' in content
    assert "review_status" in content
    assert "review_reason" in content
    assert "reviewed_at" in content
    assert "reviewed_by" in content
    assert "strategy_version_audits" in content
    assert "fk_strategies_current_version" in content
    assert "ix_sva_audit_version_created" in content
    assert "ix_sva_audit_transition" in content
    assert "Refusing to downgrade RT-S8-001" in content
