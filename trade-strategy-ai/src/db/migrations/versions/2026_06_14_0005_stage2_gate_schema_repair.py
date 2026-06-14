"""Converge reused Stage 2 tables with the frozen canonical schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "2026_06_14_0005"
down_revision = "2026_06_14_0004"
branch_labels = None
depends_on = None


def _create_enum(name: str, values: tuple[str, ...]) -> None:
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


def upgrade() -> None:
    _create_enum("rule_applicability_result_status", ("ready", "insufficient_sample", "partial", "invalid"))
    _create_enum("signal_state", ("proposed", "approved", "rejected", "cancelled", "expired", "executed"))

    op.add_column("market_snapshots", sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("market_snapshots", sa.Column("available_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("market_snapshots", sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("market_snapshots", sa.Column("content_fingerprint", sa.String(length=64), nullable=True))
    op.add_column(
        "market_snapshots",
        sa.Column("manifest_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.execute(
        sa.text(
            """
            UPDATE market_snapshots
            SET captured_at = COALESCE(created_at, now()),
                available_at = COALESCE(created_at, now()),
                effective_at = COALESCE(created_at, now()),
                content_fingerprint = md5(snapshot_id || ':' || data_version)
            """
        )
    )
    for column in ("captured_at", "available_at", "effective_at", "content_fingerprint"):
        op.alter_column("market_snapshots", column, nullable=False)
    op.create_unique_constraint(
        "uq_market_snapshots_market_date_slot_version",
        "market_snapshots",
        ["market", "trade_date", "slot", "data_version"],
    )
    op.create_unique_constraint("uq_market_snapshots_content_fingerprint", "market_snapshots", ["content_fingerprint"])

    op.add_column("market_regimes", sa.Column("market_state_id", sa.Uuid(), nullable=True))
    op.add_column("market_regimes", sa.Column("market_snapshot_id", sa.Uuid(), nullable=True))
    op.add_column("market_regimes", sa.Column("definition_version", sa.String(length=64), nullable=True))
    op.add_column("market_regimes", sa.Column("feature_version", sa.String(length=64), nullable=True))
    op.add_column("market_regimes", sa.Column("available_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE market_regimes AS mr
            SET market_state_id = md5('market-state:' || mr.regime_id)::uuid,
                market_snapshot_id = ms.id,
                definition_version = mr.regime_version,
                feature_version = mr.source_feature_version,
                available_at = COALESCE(mr.created_at, now())
            FROM market_snapshots AS ms
            WHERE ms.snapshot_id = mr.snapshot_id
            """
        )
    )
    orphan_count = op.get_bind().execute(
        sa.text("SELECT count(*) FROM market_regimes WHERE market_snapshot_id IS NULL")
    ).scalar_one()
    if orphan_count:
        raise RuntimeError("market_regimes contains rows without a matching market_snapshots record")
    for column in ("market_state_id", "market_snapshot_id", "definition_version", "feature_version", "available_at"):
        op.alter_column("market_regimes", column, nullable=False)
    op.drop_constraint("pk_market_regimes", "market_regimes", type_="primary")
    op.create_primary_key("pk_market_regimes", "market_regimes", ["market_state_id"])
    op.create_unique_constraint("uq_market_regimes_regime_id", "market_regimes", ["regime_id"])
    op.create_unique_constraint(
        "uq_market_regimes_snapshot_definition",
        "market_regimes",
        ["market_snapshot_id", "definition_version"],
    )
    op.create_foreign_key(
        "fk_market_regimes_market_snapshot",
        "market_regimes",
        "market_snapshots",
        ["market_snapshot_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.alter_column(
        "backtest_result_runs",
        "strategy_version_id",
        new_column_name="legacy_strategy_version_id",
        existing_type=sa.String(length=128),
    )
    op.add_column("backtest_result_runs", sa.Column("strategy_version_id", sa.Uuid(), nullable=True))
    op.add_column("backtest_result_runs", sa.Column("rule_version_id", sa.Uuid(), nullable=True))
    op.add_column("backtest_result_runs", sa.Column("dataset_snapshot_id", sa.Uuid(), nullable=True))
    op.add_column(
        "backtest_result_runs",
        sa.Column("market_state_definition_version", sa.String(length=64), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE backtest_result_runs AS btr
            SET rule_version_id = lim.canonical_version_id,
                market_state_definition_version = btr.regime_version
            FROM legacy_id_mappings AS lim
            WHERE lim.legacy_system = 'rule_pool'
              AND lim.legacy_object_type = 'rule'
              AND lim.legacy_id = btr.storage_ref->>'legacy_rule_id'
            """
        )
    )
    op.create_foreign_key(
        "fk_btr_strategy_version",
        "backtest_result_runs",
        "strategy_versions",
        ["strategy_version_id"],
        ["strategy_version_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_btr_rule_version",
        "backtest_result_runs",
        "rule_versions",
        ["rule_version_id"],
        ["rule_version_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_btr_dataset_snapshot",
        "backtest_result_runs",
        "dataset_snapshots",
        ["dataset_snapshot_id"],
        ["dataset_snapshot_id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "rule_applicability_profiles",
        sa.Column("applicability_profile_id", sa.Uuid(), nullable=True),
    )
    op.add_column("rule_applicability_profiles", sa.Column("rule_version_id", sa.Uuid(), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("dataset_snapshot_id", sa.Uuid(), nullable=True))
    op.add_column(
        "rule_applicability_profiles",
        sa.Column("market_state_definition_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "rule_applicability_profiles",
        sa.Column("lifecycle_state", sa.Enum(name="formal_lifecycle"), nullable=False, server_default=sa.text("'draft'")),
    )
    op.add_column(
        "rule_applicability_profiles",
        sa.Column(
            "result_status",
            sa.Enum(name="rule_applicability_result_status"),
            nullable=False,
            server_default=sa.text("'partial'"),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE rule_applicability_profiles
            SET applicability_profile_id = profile_id,
                market_state_definition_version = market_regime_version
            """
        )
    )
    op.alter_column("rule_applicability_profiles", "applicability_profile_id", nullable=False)
    op.create_unique_constraint(
        "uq_rap_applicability_profile_id",
        "rule_applicability_profiles",
        ["applicability_profile_id"],
    )
    op.create_foreign_key(
        "fk_rap_rule_version",
        "rule_applicability_profiles",
        "rule_versions",
        ["rule_version_id"],
        ["rule_version_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_rap_dataset_snapshot",
        "rule_applicability_profiles",
        "dataset_snapshots",
        ["dataset_snapshot_id"],
        ["dataset_snapshot_id"],
        ondelete="SET NULL",
    )

    op.alter_column(
        "signals",
        "strategy_version_id",
        new_column_name="legacy_strategy_version_id",
        existing_type=sa.String(length=128),
    )
    op.add_column("signals", sa.Column("strategy_version_id", sa.Uuid(), nullable=True))
    op.add_column("signals", sa.Column("trading_day_plan_id", sa.Uuid(), nullable=True))
    op.add_column("signals", sa.Column("daily_strategy_instance_id", sa.Uuid(), nullable=True))
    op.add_column(
        "signals",
        sa.Column(
            "rule_version_ids",
            postgresql.ARRAY(sa.Uuid()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )
    op.add_column(
        "signals",
        sa.Column("signal_state", sa.Enum(name="signal_state"), nullable=False, server_default=sa.text("'proposed'")),
    )
    op.add_column("signals", sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("signals", sa.Column("available_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("signals", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE signals
            SET generated_at = COALESCE(created_at AT TIME ZONE 'UTC', now()),
                available_at = COALESCE(created_at AT TIME ZONE 'UTC', now()),
                signal_state = CASE
                    WHEN rejected THEN 'rejected'::signal_state
                    ELSE 'proposed'::signal_state
                END
            """
        )
    )
    op.create_foreign_key(
        "fk_signals_strategy_version",
        "signals",
        "strategy_versions",
        ["strategy_version_id"],
        ["strategy_version_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_signals_plan",
        "signals",
        "trading_day_plans",
        ["trading_day_plan_id"],
        ["trading_day_plan_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_signals_daily_instance",
        "signals",
        "daily_strategy_instances",
        ["daily_strategy_instance_id"],
        ["daily_strategy_instance_id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_drs_market_state",
        "daily_rule_selections",
        "market_regimes",
        ["market_state_id"],
        ["market_state_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_pmr_market_state",
        "post_market_reviews",
        "market_regimes",
        ["market_state_id"],
        ["market_state_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_pmr_market_state", "post_market_reviews", type_="foreignkey")
    op.drop_constraint("fk_drs_market_state", "daily_rule_selections", type_="foreignkey")

    for name in ("fk_signals_daily_instance", "fk_signals_plan", "fk_signals_strategy_version"):
        op.drop_constraint(name, "signals", type_="foreignkey")
    for column in (
        "expires_at",
        "available_at",
        "generated_at",
        "signal_state",
        "rule_version_ids",
        "daily_strategy_instance_id",
        "trading_day_plan_id",
        "strategy_version_id",
    ):
        op.drop_column("signals", column)
    op.alter_column(
        "signals",
        "legacy_strategy_version_id",
        new_column_name="strategy_version_id",
        existing_type=sa.String(length=128),
    )

    for name in ("fk_rap_dataset_snapshot", "fk_rap_rule_version"):
        op.drop_constraint(name, "rule_applicability_profiles", type_="foreignkey")
    op.drop_constraint(
        "uq_rap_applicability_profile_id",
        "rule_applicability_profiles",
        type_="unique",
    )
    for column in (
        "result_status",
        "lifecycle_state",
        "market_state_definition_version",
        "dataset_snapshot_id",
        "rule_version_id",
        "applicability_profile_id",
    ):
        op.drop_column("rule_applicability_profiles", column)

    for name in ("fk_btr_dataset_snapshot", "fk_btr_rule_version", "fk_btr_strategy_version"):
        op.drop_constraint(name, "backtest_result_runs", type_="foreignkey")
    for column in (
        "market_state_definition_version",
        "dataset_snapshot_id",
        "rule_version_id",
        "strategy_version_id",
    ):
        op.drop_column("backtest_result_runs", column)
    op.alter_column(
        "backtest_result_runs",
        "legacy_strategy_version_id",
        new_column_name="strategy_version_id",
        existing_type=sa.String(length=128),
    )

    op.drop_constraint("fk_market_regimes_market_snapshot", "market_regimes", type_="foreignkey")
    op.drop_constraint("uq_market_regimes_snapshot_definition", "market_regimes", type_="unique")
    op.drop_constraint("uq_market_regimes_regime_id", "market_regimes", type_="unique")
    op.drop_constraint("pk_market_regimes", "market_regimes", type_="primary")
    op.create_primary_key("pk_market_regimes", "market_regimes", ["regime_id"])
    for column in (
        "available_at",
        "feature_version",
        "definition_version",
        "market_snapshot_id",
        "market_state_id",
    ):
        op.drop_column("market_regimes", column)

    op.drop_constraint(
        "uq_market_snapshots_content_fingerprint",
        "market_snapshots",
        type_="unique",
    )
    op.drop_constraint(
        "uq_market_snapshots_market_date_slot_version",
        "market_snapshots",
        type_="unique",
    )
    for column in (
        "manifest_json",
        "content_fingerprint",
        "effective_at",
        "available_at",
        "captured_at",
    ):
        op.drop_column("market_snapshots", column)
