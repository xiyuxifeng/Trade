"""
迁移：修正 article_id 列类型为 UUID 并添加外键约束
创建时间：2026-05-07

将 trade_sample.article_id 和 article_classification.article_id
从 String(128) 改为 UUID，并添加指向 blog_articles.id 的外键。
"""
from alembic import op
import sqlalchemy as sa


revision = '2026_05_07_0001'
down_revision = '2026_04_30_0002'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 修正 trade_sample.article_id: String(128) → UUID + FK
    op.execute("""
        ALTER TABLE trade_sample
        ALTER COLUMN article_id TYPE UUID USING article_id::UUID
    """)
    op.create_foreign_key(
        'fk_trade_sample_article_id',
        'trade_sample',
        'blog_articles',
        ['article_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # 2. 修正 article_classification.article_id: String(128) → UUID + FK
    op.execute("""
        ALTER TABLE article_classification
        ALTER COLUMN article_id TYPE UUID USING article_id::UUID
    """)
    op.create_foreign_key(
        'fk_article_classification_article_id',
        'article_classification',
        'blog_articles',
        ['article_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade():
    # 1. 移除 article_classification 的外键约束并恢复为 String(128)
    op.drop_constraint(
        'fk_article_classification_article_id',
        'article_classification',
        type_='foreignkey',
    )
    op.execute("""
        ALTER TABLE article_classification
        ALTER COLUMN article_id TYPE VARCHAR(128) USING article_id::VARCHAR(128)
    """)

    # 2. 移除 trade_sample 的外键约束并恢复为 String(128)
    op.drop_constraint(
        'fk_trade_sample_article_id',
        'trade_sample',
        type_='foreignkey',
    )
    op.execute("""
        ALTER TABLE trade_sample
        ALTER COLUMN article_id TYPE VARCHAR(128) USING article_id::VARCHAR(128)
    """)
