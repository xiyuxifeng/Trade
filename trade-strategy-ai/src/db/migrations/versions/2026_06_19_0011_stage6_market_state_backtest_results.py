"""stage6 market-state backtest results

Revision ID: 2026_06_19_0011
Revises: 2026_06_18_0010
Create Date: 2026-06-19
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_06_19_0011"
down_revision: Union[str, None] = "2026_06_18_0010"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "backtest_results",
        sa.Column("result_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("result_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("reproducibility_fingerprint", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_level", sa.String(length=32), nullable=False),
        sa.Column("effective_level", sa.String(length=32), nullable=False),
        sa.Column("market_state_model_version", sa.String(length=64), nullable=True),
        sa.Column("market_state_source_version", sa.String(length=64), nullable=True),
        sa.Column("market_state_result_version", sa.String(length=64), nullable=True),
        sa.Column("decision_time_policy", sa.String(length=128), nullable=False),
        sa.Column("overall_metrics", _json_type(), nullable=False),
        sa.Column("per_market_state_metrics", _json_type(), nullable=False),
        sa.Column("per_rule_metrics", _json_type(), nullable=False),
        sa.Column("sample_state_counts", _json_type(), nullable=False),
        sa.Column("coverage_json", _json_type(), nullable=False),
        sa.Column("warnings", _json_type(), nullable=False),
        sa.Column("limitations", _json_type(), nullable=False),
        sa.Column("provenance_json", _json_type(), nullable=False),
        sa.Column("audit_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["backtest_runs.run_id"], name="fk_btres_run", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("result_id"),
    )
    op.create_index("uq_btres_run", "backtest_results", ["run_id"], unique=True)
    op.create_index("uq_btres_result_fingerprint", "backtest_results", ["result_fingerprint"], unique=True)
    op.create_index("ix_btres_status_created", "backtest_results", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_btres_status_created", table_name="backtest_results")
    op.drop_index("uq_btres_result_fingerprint", table_name="backtest_results")
    op.drop_index("uq_btres_run", table_name="backtest_results")
    op.drop_table("backtest_results")
