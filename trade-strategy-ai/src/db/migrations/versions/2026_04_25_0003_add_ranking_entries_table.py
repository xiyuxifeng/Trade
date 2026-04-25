"""Add ranking_entries table for ranking results persistence."""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "2026_04_25_0003"
down_revision = "2026_04_25_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ranking_entries",
        sa.Column("entry_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("trade_date", sa.String(10), nullable=False),
        sa.Column("trader_id", sa.String(64), nullable=False, index=True),
        sa.Column("strategy_version_id", sa.String(128), nullable=False, index=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("return_pct", sa.Float(), nullable=True),
        sa.Column("mfe", sa.Float(), nullable=True),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("is_latest", sa.Boolean(), nullable=False, default=True),
        sa.Column("idea_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "attribution_source",
            sa.String(32),
            nullable=False,
            server_default="auto",
        ),
        sa.Column(
            "extra",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "trade_date",
            "strategy_version_id",
            "symbol",
            name="uq_ranking_entry",
        ),
    )
    op.create_index("ix_ranking_trader_version", "ranking_entries", ["trader_id", "strategy_version_id"])
    op.create_index("ix_ranking_trade_date", "ranking_entries", ["trade_date"])


def downgrade() -> None:
    op.drop_index("ix_ranking_trade_date", table_name="ranking_entries")
    op.drop_index("ix_ranking_trader_version", table_name="ranking_entries")
    op.drop_table("ranking_entries")
