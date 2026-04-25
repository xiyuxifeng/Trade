"""Add evidence_packs table for postmortem evidence persistence."""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "2026_04_25_0002"
down_revision = "2026_04_25_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_packs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("idea_id", UUID(as_uuid=True), nullable=True, unique=True),
        sa.Column("trader_id", sa.String(64), nullable=True, index=True),
        sa.Column("trade_date", sa.Date(), nullable=True, index=True),
        sa.Column("symbol", sa.String(20), nullable=True, index=True),
        sa.Column("strategy_version_id", sa.String(128), nullable=True, index=True),
        sa.Column(
            "pack_data",
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
    )
    op.create_index(
        "ix_evidence_packs_trader_date",
        "evidence_packs",
        ["trader_id", "trade_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_packs_trader_date", table_name="evidence_packs")
    op.drop_table("evidence_packs")
