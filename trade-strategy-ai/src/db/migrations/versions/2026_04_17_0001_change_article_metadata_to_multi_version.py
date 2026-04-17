"""
将 article_metadata 的唯一约束从 (article_id) 改为 (article_id, version)
以支持同一文章保留多个版本的 metadata 记录
"""
from alembic import op

revision = '2026_04_17_0001'
down_revision = '2026_04_16_0001'
branch_labels = None
depends_on = None


def upgrade():
    # 删除原有的 article_id 唯一约束
    op.drop_constraint('uq_article_metadata_article_id', 'article_metadata', type_='unique')
    # 添加新的复合唯一约束 (article_id, schema_version)
    op.create_unique_constraint(
        'uq_article_metadata_article_id_version',
        'article_metadata',
        ['article_id', 'schema_version'],
    )


def downgrade():
    op.drop_constraint('uq_article_metadata_article_id_version', 'article_metadata', type_='unique')
    op.create_unique_constraint('uq_article_metadata_article_id', 'article_metadata', ['article_id'])
