"""Add raw_articles and crawl_state tables

Revision ID: 2026_04_11_001
Revises: 2026_04_09_001
Create Date: 2026-04-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TEXT

# revision identifiers, used by Alembic.
revision = '2026_04_11_001'
down_revision = '2026_04_09_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 raw_articles 表
    op.create_table(
        'raw_articles',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('site', sa.String(100), nullable=False),
        sa.Column('trader_id', sa.String(100), nullable=True),
        sa.Column('author_id', sa.String(128), nullable=False),
        sa.Column('author_name', sa.String(100), nullable=True),
        sa.Column('source_url', sa.String(1024), nullable=False),
        sa.Column('source_article_id', sa.String(128), nullable=True),
        sa.Column('title', sa.String(500), nullable=False, server_default=''),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('crawled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comments', JSONB(), nullable=False, server_default='[]'),
        sa.Column('raw_payload', JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('char_length(source_url) > 0', name='raw_article_source_url_not_empty'),
    )
    # 创建索引
    op.create_index('ix_raw_articles_source_author', 'raw_articles', ['source', 'author_id'])
    op.create_index('ix_raw_articles_crawled_at', 'raw_articles', ['crawled_at'])
    op.create_index('ix_raw_articles_content_hash', 'raw_articles', ['content_hash'])
    op.create_index('ix_raw_articles_is_processed', 'raw_articles', ['is_processed'])

    # 创建 crawl_state 表
    op.create_table(
        'crawl_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('author_id', sa.String(128), nullable=False),
        sa.Column('last_seen_article_url', sa.Text(), nullable=True),
        sa.Column('last_seen_published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('seen_urls', ARRAY(TEXT), nullable=False, server_default='{}'),
        sa.Column('seen_hashes', ARRAY(TEXT), nullable=False, server_default='{}'),
        sa.Column('last_success_article_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'author_id', name='ix_crawl_state_source_author'),
    )


def downgrade() -> None:
    op.drop_table('crawl_state')
    op.drop_table('raw_articles')
