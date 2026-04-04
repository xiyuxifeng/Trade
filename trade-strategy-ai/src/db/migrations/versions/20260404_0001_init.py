"""
初始迁移：创建 blog_articles、article_metadata、market_data、trade_logs 四张表及索引
"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = '20260404_0001_init'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'blog_articles',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_article_id', sa.String(128)),
        sa.Column('source_url', sa.String(1024), nullable=False, unique=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('author_name', sa.String(100)),
        sa.Column('author_id', sa.String(128)),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('crawled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_text', sa.Text, nullable=False),
        sa.Column('content_html', sa.Text),
        sa.Column('summary', sa.Text),
        sa.Column('tags', sa.JSON, nullable=False, default=list),
        sa.Column('content_hash', sa.String(64), unique=True),
        sa.Column('view_count', sa.Integer, nullable=False, default=0),
        sa.Column('like_count', sa.Integer, nullable=False, default=0),
        sa.Column('bookmark_count', sa.Integer, nullable=False, default=0),
        sa.Column('comment_count', sa.Integer, nullable=False, default=0),
        sa.Column('comments_payload', sa.JSON, nullable=False, default=list),
        sa.Column('raw_payload', sa.JSON, nullable=False, default=dict),
    )
    op.create_index('ix_blog_articles_source_published_at', 'blog_articles', ['source', 'published_at'])
    op.create_index('ix_blog_articles_author_published_at', 'blog_articles', ['author_id', 'published_at'])
    op.create_index('ix_blog_articles_content_hash', 'blog_articles', ['content_hash'])

    op.create_table(
        'article_metadata',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('article_id', sa.Uuid(as_uuid=True), sa.ForeignKey('blog_articles.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('schema_version', sa.String(20), nullable=False, default='v1'),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('extracted_concepts', sa.JSON, nullable=False, default=list),
        sa.Column('trading_symbols', sa.JSON, nullable=False, default=list),
        sa.Column('strategy_rules', sa.JSON, nullable=False, default=list),
        sa.Column('preconditions', sa.JSON, nullable=False, default=list),
        sa.Column('comment_insights', sa.JSON, nullable=False, default=list),
        sa.Column('raw_llm_output', sa.JSON, nullable=False, default=dict),
        sa.Column('sentiment_score', sa.Numeric(4, 3)),
        sa.Column('confidence_score', sa.Numeric(4, 3)),
    )
    op.create_index('ix_article_metadata_schema_version', 'article_metadata', ['schema_version'])
    op.create_index('ix_article_metadata_processed_at', 'article_metadata', ['processed_at'])

    op.create_table(
        'market_data',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('symbol', sa.String(32), nullable=False),
        sa.Column('traded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Numeric(18, 6), nullable=False),
        sa.Column('high', sa.Numeric(18, 6), nullable=False),
        sa.Column('low', sa.Numeric(18, 6), nullable=False),
        sa.Column('close', sa.Numeric(18, 6), nullable=False),
        sa.Column('volume', sa.Numeric(18, 2), nullable=False),
        sa.Column('turnover', sa.Numeric(18, 2)),
        sa.Column('extra', sa.JSON, nullable=False, default=dict),
    )
    op.create_index('ix_market_data_symbol_traded_at', 'market_data', ['symbol', 'traded_at'])

    op.create_table(
        'trade_logs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', sa.String(64)),
        sa.Column('symbol', sa.String(32), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('side', sa.String(8)),
        sa.Column('quantity', sa.Numeric(18, 6), nullable=False),
        sa.Column('price', sa.Numeric(18, 6), nullable=False),
        sa.Column('amount', sa.Numeric(18, 6), nullable=False),
        sa.Column('fee', sa.Numeric(18, 6), default=0),
        sa.Column('raw_payload', sa.JSON, nullable=False, default=dict),
        sa.Column('external_id', sa.String(128)),
        sa.Column('article_id', sa.Uuid(as_uuid=True), sa.ForeignKey('blog_articles.id', ondelete='SET NULL')),
    )
    op.create_index('ix_trade_logs_symbol_executed_at', 'trade_logs', ['symbol', 'executed_at'])
    op.create_index('ix_trade_logs_account_executed_at', 'trade_logs', ['account_id', 'executed_at'])
    op.create_index('ix_trade_logs_article_executed_at', 'trade_logs', ['article_id', 'executed_at'])

def downgrade():
    op.drop_table('trade_logs')
    op.drop_table('market_data')
    op.drop_table('article_metadata')
    op.drop_table('blog_articles')
