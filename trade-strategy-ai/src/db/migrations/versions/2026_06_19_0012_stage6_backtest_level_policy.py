"""stage6 backtest level policy fields

Revision ID: 2026_06_19_0012
Revises: 2026_06_19_0011
Create Date: 2026-06-19
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_06_19_0012"
down_revision: Union[str, None] = "2026_06_19_0011"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.add_column(
        "backtest_runs",
        sa.Column(
            "level_policy_version",
            sa.String(length=64),
            nullable=False,
            server_default="stage6-level-policy-v1",
        ),
    )
    op.add_column("backtest_runs", sa.Column("downgrade_reason", sa.Text(), nullable=True))
    op.add_column(
        "backtest_runs",
        sa.Column("repair_guidance", _json_type(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "backtest_results",
        sa.Column(
            "level_policy_version",
            sa.String(length=64),
            nullable=False,
            server_default="stage6-level-policy-v1",
        ),
    )
    op.alter_column("backtest_runs", "level_policy_version", server_default=None)
    op.alter_column("backtest_runs", "repair_guidance", server_default=None)
    op.alter_column("backtest_results", "level_policy_version", server_default=None)


def downgrade() -> None:
    op.drop_column("backtest_results", "level_policy_version")
    op.drop_column("backtest_runs", "repair_guidance")
    op.drop_column("backtest_runs", "downgrade_reason")
    op.drop_column("backtest_runs", "level_policy_version")
