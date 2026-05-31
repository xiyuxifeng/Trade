"""add article metadata selection table

Revision ID: 2026_05_30_0001
Revises: 2026_05_26_0001
Create Date: 2026-05-30 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_05_30_0001"
down_revision = "2026_05_26_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_metadata_selections",
        sa.Column("selection_id", sa.String(length=64), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("selected_schema_version", sa.String(length=20), nullable=False),
        sa.Column("recommended_schema_version", sa.String(length=20), nullable=False),
        sa.Column("selection_mode", sa.String(length=16), nullable=False, server_default=sa.text("'auto'")),
        sa.Column("selection_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("recommended_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("selection_reason", sa.String(length=255), nullable=True),
        sa.Column("recommended_reason", sa.String(length=255), nullable=True),
        sa.Column("selected_by", sa.String(length=64), nullable=True),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candidate_versions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["article_id"], ["blog_articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("selection_id"),
        sa.UniqueConstraint("article_id", name="uq_article_metadata_selections_article_id"),
    )
    op.create_index(
        "ix_article_metadata_selections_article_id",
        "article_metadata_selections",
        ["article_id"],
        unique=False,
    )
    op.create_index(
        "ix_article_metadata_selections_selected_schema_version",
        "article_metadata_selections",
        ["selected_schema_version"],
        unique=False,
    )
    op.create_index(
        "ix_article_metadata_selections_selected_by_created_at",
        "article_metadata_selections",
        ["selected_by", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_article_metadata_selections_selection_mode",
        "article_metadata_selections",
        ["selection_mode", "selected_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_article_metadata_selections_selection_mode", table_name="article_metadata_selections")
    op.drop_index("ix_article_metadata_selections_selected_by_created_at", table_name="article_metadata_selections")
    op.drop_index("ix_article_metadata_selections_selected_schema_version", table_name="article_metadata_selections")
    op.drop_index("ix_article_metadata_selections_article_id", table_name="article_metadata_selections")
    op.drop_table("article_metadata_selections")
