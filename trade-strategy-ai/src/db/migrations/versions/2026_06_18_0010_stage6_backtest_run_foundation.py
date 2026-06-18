"""stage6 backtest run foundation

Revision ID: 2026_06_18_0010
Revises: 2026_06_17_0009
Create Date: 2026-06-18
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_06_18_0010"
down_revision: Union[str, None] = "2026_06_17_0009"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("rule_version_id", sa.Uuid(), nullable=True),
        sa.Column("rule_version_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("rule_version_no", sa.Integer(), nullable=True),
        sa.Column("rule_family_id", sa.Uuid(), nullable=True),
        sa.Column("rule_family_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("frozen_rule_version_ids", _json_type(), nullable=False),
        sa.Column("frozen_rule_version_fingerprints", _json_type(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("universe_json", _json_type(), nullable=False),
        sa.Column("benchmark_symbol", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("requested_level", sa.String(length=32), nullable=False),
        sa.Column("effective_level", sa.String(length=32), nullable=False),
        sa.Column("dataset_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("market_snapshot_ids", _json_type(), nullable=False),
        sa.Column("market_snapshot_fingerprints", _json_type(), nullable=False),
        sa.Column("market_state_model_version", sa.String(length=64), nullable=True),
        sa.Column("indicator_version", sa.String(length=64), nullable=False),
        sa.Column("engine_version", sa.String(length=64), nullable=False),
        sa.Column("execution_policy_version", sa.String(length=64), nullable=False),
        sa.Column("recommendation_policy_version", sa.String(length=64), nullable=True),
        sa.Column("decision_time_policy", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("reproducibility_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("snapshot_only", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("coverage_state", sa.String(length=32), nullable=False),
        sa.Column("quality_state", sa.String(length=32), nullable=False),
        sa.Column("unavailable_reasons", _json_type(), nullable=False),
        sa.Column("limitations", _json_type(), nullable=False),
        sa.Column("progress_json", _json_type(), nullable=False),
        sa.Column("audit_json", _json_type(), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source_surface", sa.String(length=128), nullable=False),
        sa.Column("before_state_json", _json_type(), nullable=True),
        sa.Column("after_state_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_snapshot_id"], ["dataset_snapshots.dataset_snapshot_id"], name="fk_btrun_dataset_snapshot", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rule_family_id"], ["rule_families.rule_family_id"], name="fk_btrun_rule_family", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rule_version_id"], ["rule_versions.rule_version_id"], name="fk_btrun_rule_version", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("uq_btrun_request_fingerprint", "backtest_runs", ["request_fingerprint"], unique=True)
    op.create_index("ix_btrun_rule_version_created", "backtest_runs", ["rule_version_id", "created_at"], unique=False)
    op.create_index("ix_btrun_rule_family_created", "backtest_runs", ["rule_family_id", "created_at"], unique=False)
    op.create_index("ix_btrun_dataset_snapshot", "backtest_runs", ["dataset_snapshot_id"], unique=False)
    op.create_index("ix_btrun_status_created", "backtest_runs", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_btrun_status_created", table_name="backtest_runs")
    op.drop_index("ix_btrun_dataset_snapshot", table_name="backtest_runs")
    op.drop_index("ix_btrun_rule_family_created", table_name="backtest_runs")
    op.drop_index("ix_btrun_rule_version_created", table_name="backtest_runs")
    op.drop_index("uq_btrun_request_fingerprint", table_name="backtest_runs")
    op.drop_table("backtest_runs")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS backtest_run_status")
