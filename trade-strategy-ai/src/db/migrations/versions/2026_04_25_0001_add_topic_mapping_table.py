"""Add topic_mapping table for canonical topic name resolution."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "2026_04_25_0001"
down_revision = "2026_04_23_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "topic_mapping",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("raw_topic_id", sa.String(100), nullable=False),
        sa.Column("canonical_name", sa.String(200), nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "provider",
            "raw_topic_id",
            name="uq_topic_mapping_provider_raw_id",
        ),
    )
    op.create_index("ix_topic_mapping_provider", "topic_mapping", ["provider"])
    op.create_index("ix_topic_mapping_canonical", "topic_mapping", ["canonical_name"])


def downgrade() -> None:
    op.drop_index("ix_topic_mapping_canonical", table_name="topic_mapping")
    op.drop_index("ix_topic_mapping_provider", table_name="topic_mapping")
    op.drop_table("topic_mapping")
