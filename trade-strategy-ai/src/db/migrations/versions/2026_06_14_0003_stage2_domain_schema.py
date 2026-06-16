"""Stage 2 canonical domain schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.models.base import Base
from src.models import stage2_canonical  # noqa: F401


revision = "2026_06_14_0003"
down_revision = "2026_06_14_0002"
branch_labels = None
depends_on = None


EARLY_TABLES = [
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
    "author_profile_versions",
    "strategies",
    "strategy_versions",
    "strategy_rule_memberships",
]

LATE_TABLES = [
    "daily_strategy_instances",
    "trading_day_plans",
    "post_market_reviews",
    "optimization_proposals",
]

# These constraints target columns introduced by the later Stage 2 gate repair
# migration.  Historical migrations must not inherit them from the current ORM
# metadata during fresh-database creation; migration 0005 adds them after the
# referenced columns and keys exist.
DEFERRED_FOREIGN_KEYS = {
    "fk_pmr_market_state",
}

ENUM_TYPES: dict[str, tuple[str, ...]] = {
    "quality_status": ("verified", "complete", "partial", "ambiguous", "unresolved", "rejected", "legacy_only"),
    "formal_lifecycle": ("draft", "in_review", "approved", "published", "archived", "rejected", "superseded"),
    "prompt_validation_state": ("pending", "valid", "invalid_json", "invalid_schema", "invalid_evidence", "repaired", "failed"),
    "migration_run_status": ("pending", "running", "completed", "failed", "cancelled"),
    "migration_item_status": ("pending", "migrated", "rejected", "conflicted", "skipped"),
    "migration_conflict_status": ("open", "accepted", "rejected", "superseded"),
    "candidate_review_state": ("extracted", "auto_review", "manual_review", "approved", "rejected", "superseded"),
    "dataset_lifecycle_state": ("ready", "partial", "invalid", "archived"),
    "author_profile_kind": ("method", "rule", "validated"),
    "daily_rule_selection_state": ("generated", "approved", "rejected", "superseded", "cancelled"),
    "daily_strategy_instance_state": ("generated", "approved", "superseded", "cancelled"),
    "trading_day_plan_state": ("draft", "in_review", "approved", "rejected", "superseded", "cancelled"),
    "post_market_review_state": ("draft", "in_review", "approved", "archived"),
    "proposal_lifecycle_state": ("draft", "in_review", "accepted", "rejected", "archived", "superseded"),
    "proposal_type": ("rule_optimization", "author_profile_revision", "strategy_revision"),
}


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _ensure_empty(table_name: str) -> None:
    count = op.get_bind().execute(sa.text(f"SELECT count(*) FROM {table_name}")).scalar_one()
    if count:
        raise RuntimeError(f"{table_name} contains rows; RT-S2-002 frozen rewrite only permits empty legacy tables")


def _drop_index(name: str) -> None:
    op.execute(sa.text(f"DROP INDEX IF EXISTS {name}"))


def _drop_constraint(table_name: str, name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {name}"))


def _drop_column(table_name: str, column_name: str) -> None:
    if column_name in _column_names(table_name):
        op.drop_column(table_name, column_name)


def _create_enum_type(name: str, values: tuple[str, ...]) -> None:
    values_sql = ", ".join(f"'{value}'" for value in values)
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN
                    CREATE TYPE {name} AS ENUM ({values_sql});
                END IF;
            END
            $$;
            """
        )
    )


def _create_tables(names: list[str]) -> None:
    bind = op.get_bind()
    for name in names:
        table = Base.metadata.tables[name]
        deferred_constraints = [
            constraint
            for constraint in table.constraints
            if isinstance(constraint, sa.ForeignKeyConstraint)
            and constraint.name in DEFERRED_FOREIGN_KEYS
        ]
        for constraint in deferred_constraints:
            table.constraints.remove(constraint)
        try:
            table.create(bind, checkfirst=True)
        finally:
            table.constraints.update(deferred_constraints)


def _rewrite_dataset_snapshots() -> None:
    if not _table_exists("market_datasets"):
        return
    _ensure_empty("market_datasets")

    _drop_constraint("market_snapshot_items", "fk_market_snapshot_items_dataset_id_market_datasets")

    op.rename_table("market_datasets", "dataset_snapshots")
    _drop_index("ix_market_datasets_trade_date_market")
    _drop_index("ix_market_datasets_snapshot_id")
    _drop_index("ix_market_datasets_type_trade_date")
    _drop_constraint("dataset_snapshots", "uq_market_datasets_dataset_id")
    _drop_constraint("dataset_snapshots", "fk_market_datasets_snapshot_id_market_snapshots")
    _drop_constraint("dataset_snapshots", "pk_market_datasets")

    if "id" in _column_names("dataset_snapshots"):
        op.alter_column("dataset_snapshots", "id", new_column_name="dataset_snapshot_id")

    for column_name in ("dataset_id", "source", "snapshot_id", "profile_id", "quality_status"):
        _drop_column("dataset_snapshots", column_name)

    op.alter_column("dataset_snapshots", "dataset_type", existing_type=sa.String(length=64), nullable=True)
    op.alter_column("dataset_snapshots", "trade_date", existing_type=sa.Date(), nullable=True)
    op.alter_column(
        "dataset_snapshots",
        "storage_ref",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="storage_ref::jsonb",
        nullable=True,
    )

    existing = _column_names("dataset_snapshots")
    if "content_fingerprint" not in existing:
        op.add_column("dataset_snapshots", sa.Column("content_fingerprint", sa.String(length=128), nullable=False))
    if "date_from" not in existing:
        op.add_column("dataset_snapshots", sa.Column("date_from", sa.Date(), nullable=True))
    if "date_to" not in existing:
        op.add_column("dataset_snapshots", sa.Column("date_to", sa.Date(), nullable=True))
    if "symbol_manifest" not in existing:
        op.add_column("dataset_snapshots", sa.Column("symbol_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    if "ohlcv_manifest" not in existing:
        op.add_column("dataset_snapshots", sa.Column("ohlcv_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    if "kaipan_manifest" not in existing:
        op.add_column("dataset_snapshots", sa.Column("kaipan_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    if "benchmark_symbol" not in existing:
        op.add_column("dataset_snapshots", sa.Column("benchmark_symbol", sa.String(length=32), nullable=True))
    if "market_state_definition_version" not in existing:
        op.add_column("dataset_snapshots", sa.Column("market_state_definition_version", sa.String(length=64), nullable=True))
    if "available_at" not in existing:
        op.add_column("dataset_snapshots", sa.Column("available_at", sa.DateTime(timezone=True), nullable=True))
    if "frozen_at" not in existing:
        op.add_column("dataset_snapshots", sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True))
    if "lifecycle_state" not in existing:
        op.add_column("dataset_snapshots", sa.Column("lifecycle_state", sa.Enum(name="dataset_lifecycle_state"), nullable=False, server_default=sa.text("'partial'")))
    if "quality_report_id" not in existing:
        op.add_column("dataset_snapshots", sa.Column("quality_report_id", sa.Uuid(), nullable=True))

    op.create_primary_key("pk_dataset_snapshots", "dataset_snapshots", ["dataset_snapshot_id"])
    op.create_index("uq_ds_fp", "dataset_snapshots", ["content_fingerprint"], unique=True)


def _rewrite_daily_rule_selections() -> None:
    if not _table_exists("strategy_regime_selections"):
        return
    _ensure_empty("strategy_regime_selections")
    if _table_exists("regime_rule_selections"):
        _drop_constraint("regime_rule_selections", "fk_regime_rule_selections_selection_id_strategy_regime__d968")

    op.rename_table("strategy_regime_selections", "daily_rule_selections")
    _drop_index("ix_strategy_regime_selections_strategy_version_id")
    _drop_index("ix_strategy_regime_selections_snapshot_id")
    _drop_index("ix_strategy_regime_selections_market_regime_versions")
    _drop_index("ix_strategy_regime_selections_selected_by_created_at")
    _drop_constraint("daily_rule_selections", "pk_strategy_regime_selections")

    for column_name in (
        "selection_id",
        "strategy_version_id",
        "snapshot_id",
        "market_regime_version",
        "source_feature_version",
        "applicability_profile_version",
        "selected_rule_count",
        "skipped_rule_count",
        "blocked_rule_count",
        "confidence",
        "quality_status",
        "selection_reason",
        "evidence_json",
        "override_json",
        "selected_by",
        "storage_ref",
        "artifact_ref",
    ):
        _drop_column("daily_rule_selections", column_name)

    op.add_column("daily_rule_selections", sa.Column("daily_rule_selection_id", sa.Uuid(), nullable=False))
    op.add_column("daily_rule_selections", sa.Column("strategy_version_id", sa.Uuid(), nullable=False))
    op.add_column("daily_rule_selections", sa.Column("market_state_id", sa.Uuid(), nullable=False))
    op.add_column("daily_rule_selections", sa.Column("trade_date", sa.Date(), nullable=False))
    op.add_column("daily_rule_selections", sa.Column("revision_no", sa.Integer(), nullable=False))
    op.add_column("daily_rule_selections", sa.Column("selected_rules_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("daily_rule_selections", sa.Column("reduced_rules_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("daily_rule_selections", sa.Column("blocked_rules_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("daily_rule_selections", sa.Column("quality_status", sa.Enum(name="quality_status"), nullable=False, server_default=sa.text("'partial'")))
    op.add_column("daily_rule_selections", sa.Column("lifecycle_state", sa.Enum(name="daily_rule_selection_state"), nullable=False, server_default=sa.text("'generated'")))
    op.add_column("daily_rule_selections", sa.Column("source_run_id", sa.String(length=128), nullable=True))
    op.add_column("daily_rule_selections", sa.Column("created_by", sa.String(length=64), nullable=True))
    op.add_column("daily_rule_selections", sa.Column("updated_by", sa.String(length=64), nullable=True))

    op.create_primary_key("pk_daily_rule_selections", "daily_rule_selections", ["daily_rule_selection_id"])
    op.create_foreign_key("fk_drs_strategy_version", "daily_rule_selections", "strategy_versions", ["strategy_version_id"], ["strategy_version_id"], ondelete="CASCADE")
    op.create_index("uq_drs_sv_dt_ms_rev", "daily_rule_selections", ["strategy_version_id", "trade_date", "market_state_id", "revision_no"], unique=True)


def _rewrite_daily_rule_selection_items() -> None:
    if not _table_exists("regime_rule_selections"):
        return
    _ensure_empty("regime_rule_selections")

    op.rename_table("regime_rule_selections", "daily_rule_selection_items")
    _drop_index("ix_regime_rule_selections_selection_id")
    _drop_index("ix_regime_rule_selections_rule_id")
    _drop_index("ix_regime_rule_selections_decision")
    _drop_index("ix_regime_rule_selections_regime_version")
    _drop_constraint("daily_rule_selection_items", "uq_regime_rule_selections_selection_rule")
    _drop_constraint("daily_rule_selection_items", "fk_regime_rule_selections_selection_id_strategy_regime__d968")
    _drop_constraint("daily_rule_selection_items", "pk_regime_rule_selections")

    for column_name in (
        "item_id",
        "selection_id",
        "rule_id",
        "score",
        "reason",
        "evidence_json",
        "regime_version",
        "applicability_profile_version",
        "sample_count",
        "profile_confidence",
        "override_applied",
        "rule_applicability_profile_id",
        "decision",
    ):
        _drop_column("daily_rule_selection_items", column_name)

    op.add_column("daily_rule_selection_items", sa.Column("daily_rule_selection_item_id", sa.Uuid(), nullable=False))
    op.add_column("daily_rule_selection_items", sa.Column("daily_rule_selection_id", sa.Uuid(), nullable=False))
    op.add_column("daily_rule_selection_items", sa.Column("rule_version_id", sa.Uuid(), nullable=False))
    op.add_column("daily_rule_selection_items", sa.Column("decision", sa.String(length=32), nullable=True))
    op.add_column("daily_rule_selection_items", sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))

    op.create_primary_key("pk_daily_rule_selection_items", "daily_rule_selection_items", ["daily_rule_selection_item_id"])
    op.create_foreign_key(
        "fk_drsi_selection",
        "daily_rule_selection_items",
        "daily_rule_selections",
        ["daily_rule_selection_id"],
        ["daily_rule_selection_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_drsi_rule_version",
        "daily_rule_selection_items",
        "rule_versions",
        ["rule_version_id"],
        ["rule_version_id"],
        ondelete="CASCADE",
    )
    op.create_index("uq_drsi_sel_rule", "daily_rule_selection_items", ["daily_rule_selection_id", "rule_version_id"], unique=True)


def upgrade() -> None:
    for enum_name, values in ENUM_TYPES.items():
        _create_enum_type(enum_name, values)

    _rewrite_dataset_snapshots()
    _create_tables(EARLY_TABLES)
    _rewrite_daily_rule_selections()
    _rewrite_daily_rule_selection_items()
    _create_tables(LATE_TABLES)


def _ensure_stage2_tables_empty(table_names: list[str]) -> None:
    bind = op.get_bind()
    for table_name in table_names:
        if _table_exists(table_name):
            count = bind.execute(sa.text(f"SELECT count(*) FROM {table_name}")).scalar_one()
            if count:
                raise RuntimeError(f"{table_name} contains canonical rows; use the frozen RT-S2-002 recovery procedure instead of downgrade")


def downgrade() -> None:
    _ensure_stage2_tables_empty(
        [
            "optimization_proposals",
            "post_market_reviews",
            "trading_day_plans",
            "daily_strategy_instances",
            "daily_rule_selection_items",
            "daily_rule_selections",
            "strategy_rule_memberships",
            "strategy_versions",
            "strategies",
            "author_profile_versions",
            "dataset_snapshots",
            "rule_family_memberships",
            "rule_families",
            "rule_versions",
            "rules",
            "rule_candidates",
            "article_structures",
            "migration_quality_reports",
            "migration_conflicts",
            "migration_run_items",
            "migration_runs",
            "lifecycle_events",
            "legacy_id_mappings",
            "prompt_runs",
            "article_revisions",
            "authors",
        ]
    )

    for table_name in reversed(LATE_TABLES):
        if _table_exists(table_name):
            op.drop_table(table_name)

    if _table_exists("daily_rule_selection_items"):
        op.drop_table("daily_rule_selection_items")
        op.create_table(
            "regime_rule_selections",
            sa.Column("item_id", sa.String(length=64), nullable=False),
            sa.Column("selection_id", sa.String(length=64), nullable=False),
            sa.Column("rule_id", sa.String(length=128), nullable=False),
            sa.Column("decision", sa.String(length=32), nullable=False),
            sa.Column("score", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("reason", sa.String(length=255), nullable=True),
            sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("regime_version", sa.String(length=64), nullable=False),
            sa.Column("applicability_profile_version", sa.String(length=64), nullable=True),
            sa.Column("sample_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("profile_confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("override_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("rule_applicability_profile_id", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("item_id", name="pk_regime_rule_selections"),
            sa.UniqueConstraint("selection_id", "rule_id", name="uq_regime_rule_selections_selection_rule"),
        )
        op.create_index("ix_regime_rule_selections_selection_id", "regime_rule_selections", ["selection_id"])
        op.create_index("ix_regime_rule_selections_rule_id", "regime_rule_selections", ["rule_id"])
        op.create_index("ix_regime_rule_selections_decision", "regime_rule_selections", ["decision"])
        op.create_index("ix_regime_rule_selections_regime_version", "regime_rule_selections", ["regime_version"])

    if _table_exists("daily_rule_selections"):
        op.drop_table("daily_rule_selections")
        op.create_table(
            "strategy_regime_selections",
            sa.Column("selection_id", sa.String(length=64), nullable=False),
            sa.Column("strategy_version_id", sa.String(length=128), nullable=False),
            sa.Column("snapshot_id", sa.String(length=128), nullable=False),
            sa.Column("market_regime_version", sa.String(length=64), nullable=False),
            sa.Column("source_feature_version", sa.String(length=64), nullable=True),
            sa.Column("applicability_profile_version", sa.String(length=64), nullable=True),
            sa.Column("selected_rule_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("skipped_rule_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("blocked_rule_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("quality_status", sa.String(length=32), nullable=False, server_default=sa.text("'partial'")),
            sa.Column("selection_reason", sa.String(length=255), nullable=True),
            sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("override_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("selected_by", sa.String(length=64), nullable=True),
            sa.Column("storage_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("artifact_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("selection_id", name="pk_strategy_regime_selections"),
        )
        op.create_index("ix_strategy_regime_selections_strategy_version_id", "strategy_regime_selections", ["strategy_version_id"])
        op.create_index("ix_strategy_regime_selections_snapshot_id", "strategy_regime_selections", ["snapshot_id"])
        op.create_index("ix_strategy_regime_selections_market_regime_versions", "strategy_regime_selections", ["market_regime_version", "source_feature_version"])
        op.create_index("ix_strategy_regime_selections_selected_by_created_at", "strategy_regime_selections", ["selected_by", "created_at"])

    for table_name in reversed(EARLY_TABLES):
        if _table_exists(table_name):
            op.drop_table(table_name)

    if _table_exists("dataset_snapshots"):
        op.drop_table("dataset_snapshots")
        op.create_table(
            "market_datasets",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("dataset_id", sa.String(length=128), nullable=False),
            sa.Column("dataset_type", sa.String(length=64), nullable=False),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("market", sa.String(length=32), nullable=False, server_default=sa.text("'CN'")),
            sa.Column("source", sa.String(length=64), nullable=True),
            sa.Column("storage_ref", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("snapshot_id", sa.String(length=128), nullable=True),
            sa.Column("profile_id", sa.String(length=128), nullable=True),
            sa.Column("quality_status", sa.String(length=32), nullable=False, server_default=sa.text("'ok'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id", name="pk_market_datasets"),
            sa.UniqueConstraint("dataset_id", name="uq_market_datasets_dataset_id"),
        )
        op.create_index("ix_market_datasets_trade_date_market", "market_datasets", ["trade_date", "market"])
        op.create_index("ix_market_datasets_snapshot_id", "market_datasets", ["snapshot_id"])
        op.create_index("ix_market_datasets_type_trade_date", "market_datasets", ["dataset_type", "trade_date"])
