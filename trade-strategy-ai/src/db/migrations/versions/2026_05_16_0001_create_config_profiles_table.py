"""Create config profiles table for canonical Profile storage."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "2026_05_16_0001"
down_revision = "2026_05_11_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config_profiles",
        sa.Column("profile_id", sa.String(length=128), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("environment", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("sections", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("secret_refs", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("validation_status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_config_profiles_environment_validation_status",
        "config_profiles",
        ["environment", "validation_status"],
    )
    op.create_index("ix_config_profiles_updated_at", "config_profiles", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_config_profiles_updated_at", table_name="config_profiles")
    op.drop_index("ix_config_profiles_environment_validation_status", table_name="config_profiles")
    op.drop_table("config_profiles")

