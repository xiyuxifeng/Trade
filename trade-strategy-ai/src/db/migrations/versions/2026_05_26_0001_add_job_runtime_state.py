"""Add runtime_state column to jobs table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "2026_05_26_0001"
down_revision = "2026_05_25_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为 jobs 表增加持久化 runtime_state 字段。"""
    op.add_column("jobs", sa.Column("runtime_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """回滚 runtime_state 字段。"""
    op.drop_column("jobs", "runtime_state")
