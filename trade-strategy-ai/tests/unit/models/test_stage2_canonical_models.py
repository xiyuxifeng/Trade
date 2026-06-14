from __future__ import annotations


def test_stage2_canonical_tables_are_registered() -> None:
    from src.models.base import Base
    import src.models as models  # noqa: F401

    expected_tables = {
        "authors",
        "article_revisions",
        "prompt_runs",
        "legacy_id_mappings",
        "lifecycle_events",
        "migration_runs",
        "migration_run_items",
        "migration_conflicts",
        "migration_quality_reports",
        "article_structures",
        "rule_candidates",
        "rules",
        "rule_versions",
        "rule_families",
        "rule_family_memberships",
        "dataset_snapshots",
        "author_profile_versions",
        "strategies",
        "strategy_versions",
        "strategy_rule_memberships",
        "daily_rule_selections",
        "daily_rule_selection_items",
        "daily_strategy_instances",
        "trading_day_plans",
        "post_market_reviews",
        "optimization_proposals",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_stage2_canonical_tables_expose_frozen_identity_columns() -> None:
    from src.models.base import Base
    import src.models as models  # noqa: F401

    assert {"rule_id", "current_published_version_id"}.issubset(Base.metadata.tables["rules"].columns.keys())
    assert {"rule_version_id", "rule_id", "version_no", "lifecycle_state"}.issubset(
        Base.metadata.tables["rule_versions"].columns.keys()
    )
    assert {"dataset_snapshot_id", "content_fingerprint", "lifecycle_state"}.issubset(
        Base.metadata.tables["dataset_snapshots"].columns.keys()
    )
    assert {"strategy_id", "current_published_version_id"}.issubset(
        Base.metadata.tables["strategies"].columns.keys()
    )
    assert {"strategy_version_id", "strategy_id", "version_no", "lifecycle_state"}.issubset(
        Base.metadata.tables["strategy_versions"].columns.keys()
    )
    assert {"daily_rule_selection_id", "strategy_version_id", "market_state_id", "trade_date"}.issubset(
        Base.metadata.tables["daily_rule_selections"].columns.keys()
    )


def test_reused_stage2_tables_expose_frozen_canonical_columns_and_foreign_keys() -> None:
    from src.models.base import Base
    import src.models as models  # noqa: F401

    expected_columns = {
        "market_snapshots": {
            "captured_at",
            "available_at",
            "effective_at",
            "content_fingerprint",
            "manifest_json",
        },
        "market_regimes": {
            "market_state_id",
            "market_snapshot_id",
            "definition_version",
            "feature_version",
            "available_at",
        },
        "backtest_result_runs": {
            "dataset_snapshot_id",
            "rule_version_id",
            "strategy_version_id",
            "market_state_definition_version",
            "legacy_strategy_version_id",
        },
        "rule_applicability_profiles": {
            "applicability_profile_id",
            "rule_version_id",
            "dataset_snapshot_id",
            "market_state_definition_version",
            "lifecycle_state",
            "result_status",
        },
        "signals": {
            "trading_day_plan_id",
            "daily_strategy_instance_id",
            "rule_version_ids",
            "signal_state",
            "generated_at",
            "available_at",
            "expires_at",
            "legacy_strategy_version_id",
        },
    }
    for table_name, columns in expected_columns.items():
        assert columns.issubset(Base.metadata.tables[table_name].columns.keys())

    expected_foreign_keys = {
        ("market_regimes", "market_snapshot_id", "market_snapshots.id"),
        ("backtest_result_runs", "dataset_snapshot_id", "dataset_snapshots.dataset_snapshot_id"),
        ("backtest_result_runs", "rule_version_id", "rule_versions.rule_version_id"),
        ("backtest_result_runs", "strategy_version_id", "strategy_versions.strategy_version_id"),
        ("rule_applicability_profiles", "rule_version_id", "rule_versions.rule_version_id"),
        ("rule_applicability_profiles", "dataset_snapshot_id", "dataset_snapshots.dataset_snapshot_id"),
        ("signals", "trading_day_plan_id", "trading_day_plans.trading_day_plan_id"),
        ("signals", "daily_strategy_instance_id", "daily_strategy_instances.daily_strategy_instance_id"),
        ("signals", "strategy_version_id", "strategy_versions.strategy_version_id"),
        ("daily_rule_selections", "market_state_id", "market_regimes.market_state_id"),
        ("post_market_reviews", "market_state_id", "market_regimes.market_state_id"),
    }
    actual_foreign_keys = set()
    for table_name in {item[0] for item in expected_foreign_keys}:
        table = Base.metadata.tables[table_name]
        for foreign_key in table.foreign_keys:
            actual_foreign_keys.add(
                (table_name, foreign_key.parent.name, foreign_key.target_fullname)
            )
    assert expected_foreign_keys.issubset(actual_foreign_keys)


def test_stage2_canonical_object_names_fit_postgresql_identifier_limit() -> None:
    from src.models.base import Base
    import src.models as models  # noqa: F401

    stage2_tables = {
        "authors",
        "article_revisions",
        "prompt_runs",
        "legacy_id_mappings",
        "lifecycle_events",
        "migration_runs",
        "migration_run_items",
        "migration_conflicts",
        "migration_quality_reports",
        "article_structures",
        "rule_candidates",
        "rules",
        "rule_versions",
        "rule_families",
        "rule_family_memberships",
        "dataset_snapshots",
        "author_profile_versions",
        "strategies",
        "strategy_versions",
        "strategy_rule_memberships",
        "daily_rule_selections",
        "daily_rule_selection_items",
        "daily_strategy_instances",
        "trading_day_plans",
        "post_market_reviews",
        "optimization_proposals",
    }

    names: list[str] = []
    for table_name in stage2_tables:
        table = Base.metadata.tables[table_name]
        names.extend(index.name for index in table.indexes if index.name)
        names.extend(constraint.name for constraint in table.constraints if constraint.name)

    assert all(len(name) <= 63 for name in names), [name for name in names if len(name) > 63]
