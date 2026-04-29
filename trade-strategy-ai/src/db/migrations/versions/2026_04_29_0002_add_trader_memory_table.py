"""add trader_memory table

Revision ID: 2026_04_29_0002
Revises: 2026_04_29_0001
Create Date: 2026-04-29
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_04_29_0002"
down_revision: Union[str, None] = "2026_04_29_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trader_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trader_id", sa.String(length=64), nullable=False),
        sa.Column("memory_type", sa.String(length=32), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("content", sa.String(length=4096), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="manager"),
        sa.Column("source_ref", sa.String(length=512), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("strategy_version_id", sa.String(length=64), nullable=True),
        sa.Column("ranking_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topic_source", sa.String(length=64), nullable=True),
        sa.Column("raw_topic_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("postmortem_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("strategy_adjustment_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("market_regime_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trader_id", "memory_type", "as_of_date", "symbol", "title", name="uq_memory_ctx"),
    )
    op.create_index("ix_memory_trader_id", "trader_memory", ["trader_id"], unique=False)
    op.create_index("ix_memory_trader_archived", "trader_memory", ["trader_id", "archived"], unique=False)
    op.create_index("ix_memory_trade_date", "trader_memory", ["as_of_date"], unique=False)
    op.create_index("ix_memory_symbol", "trader_memory", ["symbol"], unique=False)
    op.create_index("ix_memory_type", "trader_memory", ["memory_type"], unique=False)
    op.create_index("ix_memory_created_at", "trader_memory", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_memory_created_at", table_name="trader_memory")
    op.drop_index("ix_memory_type", table_name="trader_memory")
    op.drop_index("ix_memory_symbol", table_name="trader_memory")
    op.drop_index("ix_memory_trade_date", table_name="trader_memory")
    op.drop_index("ix_memory_trader_archived", table_name="trader_memory")
    op.drop_index("ix_memory_trader_id", table_name="trader_memory")
    op.drop_table("trader_memory")