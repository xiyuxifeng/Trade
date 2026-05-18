"""add market_regimes table

Revision ID: 2026_05_18_0001
Revises: 2026_05_17_0001
Create Date: 2026-05-18
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_18_0001"
down_revision: Union[str, None] = "2026_05_17_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_regimes",
        sa.Column("regime_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False, server_default="CN"),
        sa.Column("regime_version", sa.String(length=64), nullable=False),
        sa.Column("source_feature_version", sa.String(length=64), nullable=False),
        sa.Column("primary_label", sa.String(length=64), nullable=False),
        sa.Column("labels_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("features_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="partial"),
        sa.Column("missing_reason", sa.String(length=512), nullable=True),
        sa.Column("storage_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["snapshot_id"], ["market_snapshots.snapshot_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("regime_id"),
        sa.UniqueConstraint("snapshot_id", "regime_version", name="uq_market_regimes_snapshot_regime_version"),
    )
    op.create_index("ix_market_regimes_trade_date_market", "market_regimes", ["trade_date", "market"], unique=False)
    op.create_index("ix_market_regimes_snapshot_id", "market_regimes", ["snapshot_id"], unique=False)
    op.create_index("ix_market_regimes_regime_version", "market_regimes", ["regime_version"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_market_regimes_regime_version", table_name="market_regimes")
    op.drop_index("ix_market_regimes_snapshot_id", table_name="market_regimes")
    op.drop_index("ix_market_regimes_trade_date_market", table_name="market_regimes")
    op.drop_table("market_regimes")
