"""add rule applicability profiles table

Revision ID: 2026_05_19_0001
Revises: 2026_05_18_0001
Create Date: 2026-05-19
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_05_19_0001"
down_revision: Union[str, None] = "2026_05_18_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rule_applicability_profiles",
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("rule_id", sa.String(length=128), nullable=False),
        sa.Column("profile_version", sa.String(length=64), nullable=False),
        sa.Column("source_backtest_id", sa.String(length=128), nullable=False),
        sa.Column("source_rule_version", sa.String(length=64), nullable=True),
        sa.Column("market_regime_version", sa.String(length=64), nullable=True),
        sa.Column("source_feature_version", sa.String(length=64), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("min_sample_count", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("applicable_regimes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("blocked_regimes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("neutral_regimes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("best_market_conditions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("worst_market_conditions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("storage_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("reviewed_by", sa.String(length=64), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("profile_id"),
        sa.UniqueConstraint("rule_id", "profile_version", "source_backtest_id", name="uq_rule_applicability_profiles_rule_profile_source"),
    )
    op.create_index("ix_rule_applicability_profiles_rule_id", "rule_applicability_profiles", ["rule_id"], unique=False)
    op.create_index("ix_rule_applicability_profiles_profile_version", "rule_applicability_profiles", ["profile_version"], unique=False)
    op.create_index("ix_rule_applicability_profiles_source_backtest_id", "rule_applicability_profiles", ["source_backtest_id"], unique=False)
    op.create_index("ix_rule_applicability_profiles_review_status", "rule_applicability_profiles", ["review_status"], unique=False)
    op.create_index("ix_rule_applicability_profiles_created_at", "rule_applicability_profiles", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rule_applicability_profiles_created_at", table_name="rule_applicability_profiles")
    op.drop_index("ix_rule_applicability_profiles_review_status", table_name="rule_applicability_profiles")
    op.drop_index("ix_rule_applicability_profiles_source_backtest_id", table_name="rule_applicability_profiles")
    op.drop_index("ix_rule_applicability_profiles_profile_version", table_name="rule_applicability_profiles")
    op.drop_index("ix_rule_applicability_profiles_rule_id", table_name="rule_applicability_profiles")
    op.drop_table("rule_applicability_profiles")
