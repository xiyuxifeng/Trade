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
