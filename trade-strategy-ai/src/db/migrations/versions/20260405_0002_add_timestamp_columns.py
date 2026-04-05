"""添加 created_at, updated_at 到 blog_articles"""
from alembic import op
import sqlalchemy as sa

revision = '20260405_002_ts'
down_revision = '20260404_0001_init'
branch_labels = None
depends_on = None


def upgrade():
    for table in ('blog_articles', 'article_metadata', 'market_data', 'trade_logs'):
        op.add_column(
            table,
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        op.add_column(
            table,
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )


def downgrade():
    for table in ('blog_articles', 'article_metadata', 'market_data', 'trade_logs'):
        op.drop_column(table, 'updated_at')
        op.drop_column(table, 'created_at')
