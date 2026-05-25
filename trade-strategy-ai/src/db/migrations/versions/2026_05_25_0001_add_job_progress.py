"""add job progress column

Revision ID: 2026_05_25_0001
Revises: 2026_05_24_0001
Create Date: 2026-05-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "2026_05_25_0001"
down_revision = "2026_05_24_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("progress", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "progress")
