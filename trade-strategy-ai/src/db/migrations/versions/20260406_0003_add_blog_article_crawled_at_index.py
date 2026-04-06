"""Add crawled_at index for hot article ordering queries."""

from alembic import op


revision = "20260406_003"
down_revision = "20260405_002_ts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_blog_articles_crawled_at",
        "blog_articles",
        ["crawled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_blog_articles_crawled_at", table_name="blog_articles")
