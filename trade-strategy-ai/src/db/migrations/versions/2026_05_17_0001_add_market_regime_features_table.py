"""add market_regime_features table

Revision ID: 2026_05_17_0001
Revises: 2026_05_16_0002
Create Date: 2026-05-17
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_17_0001"
down_revision: Union[str, None] = "2026_05_16_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_regime_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False, server_default="CN"),
        sa.Column("feature_version", sa.String(length=64), nullable=False, server_default="market-regime-features-v1"),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="partial"),
        sa.Column("available_feature_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("partial_feature_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_feature_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feature_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("storage_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["snapshot_id"], ["market_snapshots.snapshot_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "feature_version", name="uq_market_regime_features_snapshot_feature_version"),
    )
    op.create_index("ix_market_regime_features_trade_date_market", "market_regime_features", ["trade_date", "market"], unique=False)
    op.create_index("ix_market_regime_features_snapshot_id", "market_regime_features", ["snapshot_id"], unique=False)
    op.create_index("ix_market_regime_features_feature_version", "market_regime_features", ["feature_version"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_market_regime_features_feature_version", table_name="market_regime_features")
    op.drop_index("ix_market_regime_features_snapshot_id", table_name="market_regime_features")
    op.drop_index("ix_market_regime_features_trade_date_market", table_name="market_regime_features")
    op.drop_table("market_regime_features")
