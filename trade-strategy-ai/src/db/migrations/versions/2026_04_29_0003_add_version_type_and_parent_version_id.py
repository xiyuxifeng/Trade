"""Add version_type and parent_version_id columns to trader_strategy_versions."""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa

revision = "2026_04_29_0003"
down_revision = "2026_04_29_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trader_strategy_versions",
        sa.Column("version_type", sa.String(32), nullable=False, server_default="manual"),
    )
    op.add_column(
        "trader_strategy_versions",
        sa.Column("parent_version_id", sa.String(256), nullable=True),
    )
    op.create_index(
        "ix_trader_strategy_versions_version_type",
        "trader_strategy_versions",
        ["version_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_trader_strategy_versions_version_type", "trader_strategy_versions")
    op.drop_column("trader_strategy_versions", "parent_version_id")
    op.drop_column("trader_strategy_versions", "version_type")
