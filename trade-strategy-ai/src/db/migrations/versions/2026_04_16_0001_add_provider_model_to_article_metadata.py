"""
添加 provider, model 字段到 article_metadata 表
记录 LLM 调用时使用的 provider 和 model
"""
from alembic import op
import sqlalchemy as sa

revision = '2026_04_16_0001'
down_revision = '2026_04_12_0001'
branch_labels = None
depends_on = None


def upgrade():
    # 添加列（允许为空，之后再回填）
    op.add_column('article_metadata', sa.Column('provider', sa.String(50), nullable=True))
    op.add_column('article_metadata', sa.Column('model', sa.String(100), nullable=True))

    # 回填历史数据
    op.execute("UPDATE article_metadata SET provider = 'qwen', model = 'qwen-plus-2025-07-14' WHERE provider IS NULL")


def downgrade():
    op.drop_column('article_metadata', 'model')
    op.drop_column('article_metadata', 'provider')
