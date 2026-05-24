"""add backtest and regime selection summary tables

Revision ID: 2026_05_24_0001
Revises: 2026_05_19_0002
Create Date: 2026-05-24
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_05_24_0001"
down_revision: Union[str, None] = "2026_05_19_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backtest_result_runs",
        sa.Column("result_run_id", sa.String(length=64), nullable=False),
        sa.Column("source_job_id", sa.String(length=64), nullable=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("request_trader_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_version_id", sa.String(length=128), nullable=True),
        sa.Column("request_date_from", sa.Date(), nullable=False),
        sa.Column("request_date_to", sa.Date(), nullable=False),
        sa.Column("benchmark_symbol", sa.String(length=32), nullable=True),
        sa.Column("regime_version", sa.String(length=64), nullable=True),
        sa.Column("source_feature_version", sa.String(length=64), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=True),
        sa.Column("scoring_profile", sa.String(length=64), nullable=True),
        sa.Column("result_version", sa.String(length=32), nullable=False, server_default=sa.text("'1.0'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'ok'")),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default=sa.text("'ok'")),
        sa.Column("total_days", sa.Integer(), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True),
        sa.Column("valid_trades", sa.Integer(), nullable=True),
        sa.Column("skipped_trades", sa.Integer(), nullable=True),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("avg_return_pct", sa.Float(), nullable=True),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("regime_metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("rule_regime_metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
        sa.Column("storage_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("artifact_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("result_run_id"),
        sa.UniqueConstraint("source_job_id", name="uq_backtest_result_runs_source_job_id"),
    )
    op.create_index("ix_backtest_result_runs_trader_date", "backtest_result_runs", ["request_trader_id", "request_date_from", "request_date_to"], unique=False)
    op.create_index("ix_backtest_result_runs_strategy_date", "backtest_result_runs", ["strategy_version_id", "request_date_from", "request_date_to"], unique=False)
    op.create_index("ix_backtest_result_runs_regime_versions", "backtest_result_runs", ["regime_version", "source_feature_version"], unique=False)
    op.create_index("ix_backtest_result_runs_benchmark_date", "backtest_result_runs", ["benchmark_symbol", "request_date_from"], unique=False)
    op.create_index("ix_backtest_result_runs_created_at", "backtest_result_runs", ["created_at"], unique=False)

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
        sa.PrimaryKeyConstraint("selection_id"),
    )
    op.create_index("ix_strategy_regime_selections_strategy_version_id", "strategy_regime_selections", ["strategy_version_id"], unique=False)
    op.create_index("ix_strategy_regime_selections_snapshot_id", "strategy_regime_selections", ["snapshot_id"], unique=False)
    op.create_index("ix_strategy_regime_selections_market_regime_versions", "strategy_regime_selections", ["market_regime_version", "source_feature_version"], unique=False)
    op.create_index("ix_strategy_regime_selections_selected_by_created_at", "strategy_regime_selections", ["selected_by", "created_at"], unique=False)

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
        sa.ForeignKeyConstraint(["selection_id"], ["strategy_regime_selections.selection_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id"),
        sa.UniqueConstraint("selection_id", "rule_id", name="uq_regime_rule_selections_selection_rule"),
    )
    op.create_index("ix_regime_rule_selections_selection_id", "regime_rule_selections", ["selection_id"], unique=False)
    op.create_index("ix_regime_rule_selections_rule_id", "regime_rule_selections", ["rule_id"], unique=False)
    op.create_index("ix_regime_rule_selections_decision", "regime_rule_selections", ["decision"], unique=False)
    op.create_index("ix_regime_rule_selections_regime_version", "regime_rule_selections", ["regime_version"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_regime_rule_selections_regime_version", table_name="regime_rule_selections")
    op.drop_index("ix_regime_rule_selections_decision", table_name="regime_rule_selections")
    op.drop_index("ix_regime_rule_selections_rule_id", table_name="regime_rule_selections")
    op.drop_index("ix_regime_rule_selections_selection_id", table_name="regime_rule_selections")
    op.drop_table("regime_rule_selections")

    op.drop_index("ix_strategy_regime_selections_selected_by_created_at", table_name="strategy_regime_selections")
    op.drop_index("ix_strategy_regime_selections_market_regime_versions", table_name="strategy_regime_selections")
    op.drop_index("ix_strategy_regime_selections_snapshot_id", table_name="strategy_regime_selections")
    op.drop_index("ix_strategy_regime_selections_strategy_version_id", table_name="strategy_regime_selections")
    op.drop_table("strategy_regime_selections")

    op.drop_index("ix_backtest_result_runs_created_at", table_name="backtest_result_runs")
    op.drop_index("ix_backtest_result_runs_benchmark_date", table_name="backtest_result_runs")
    op.drop_index("ix_backtest_result_runs_regime_versions", table_name="backtest_result_runs")
    op.drop_index("ix_backtest_result_runs_strategy_date", table_name="backtest_result_runs")
    op.drop_index("ix_backtest_result_runs_trader_date", table_name="backtest_result_runs")
    op.drop_table("backtest_result_runs")
