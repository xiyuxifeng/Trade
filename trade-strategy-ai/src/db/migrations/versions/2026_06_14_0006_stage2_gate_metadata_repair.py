"""Align repaired Stage 2 indexes and constraint names."""

from __future__ import annotations

from alembic import op


revision = "2026_06_14_0006"
down_revision = "2026_06_14_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_backtest_result_runs_strategy_date", table_name="backtest_result_runs")
    op.create_index(
        "ix_backtest_result_runs_strategy_date",
        "backtest_result_runs",
        ["strategy_version_id", "request_date_from", "request_date_to"],
    )


def downgrade() -> None:
    op.drop_index("ix_backtest_result_runs_strategy_date", table_name="backtest_result_runs")
    op.create_index(
        "ix_backtest_result_runs_strategy_date",
        "backtest_result_runs",
        ["legacy_strategy_version_id", "request_date_from", "request_date_to"],
    )
