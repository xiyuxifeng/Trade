"""Add fields to article_metadata

Revision ID: 2026_04_30_0001
Revises: 2026_04_29_0003
Create Date: 2026-04-30
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "2026_04_30_0001"
down_revision = "2026_04_29_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加 article_metadata 表的新字段"""
    # 文章类型：rule/record/concept/mixed/noise
    op.add_column(
        "article_metadata",
        sa.Column("article_type", sa.String(32), nullable=True),
    )
    # 提取版本
    op.add_column(
        "article_metadata",
        sa.Column("extraction_version", sa.String(20), nullable=True),
    )
    # 进入规则池的 standalone 规则 ID 列表
    op.add_column(
        "article_metadata",
        sa.Column("standalone_rule_ids", sa.JSON(), nullable=True),
    )
    # 反推规则 ID 列表
    op.add_column(
        "article_metadata",
        sa.Column("derived_rule_ids", sa.JSON(), nullable=True),
    )
    # 交易样本 ID 列表
    op.add_column(
        "article_metadata",
        sa.Column("trade_sample_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """删除 article_metadata 表的新字段"""
    op.drop_column("article_metadata", "trade_sample_ids")
    op.drop_column("article_metadata", "derived_rule_ids")
    op.drop_column("article_metadata", "standalone_rule_ids")
    op.drop_column("article_metadata", "extraction_version")
    op.drop_column("article_metadata", "article_type")
