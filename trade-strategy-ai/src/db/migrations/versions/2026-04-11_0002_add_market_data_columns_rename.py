"""
为 market_data 表添加缺失的列

- source: 数据来源（如 akshare, tushare）
- market: 市场（默认 CN）
- timeframe: 时间周期（默认 1d）
- adj_factor: 复权因子
- is_adjusted: 是否复权
- indicators: 技术指标 JSON
- raw_payload: 原始数据 JSON
"""
from alembic import op
import sqlalchemy as sa

revision = '202604110002'
down_revision = '2026_04_11_001'
branch_labels = None
depends_on = None


def upgrade():
    # 先添加可空列
    op.add_column('market_data', sa.Column('source', sa.String(50), nullable=True))
    op.add_column('market_data', sa.Column('market', sa.String(32), nullable=True))
    op.add_column('market_data', sa.Column('timeframe', sa.String(16), nullable=True))
    op.add_column('market_data', sa.Column('adj_factor', sa.Numeric(20, 6), nullable=True))
    op.add_column('market_data', sa.Column('is_adjusted', sa.Boolean(), nullable=True))
    op.add_column('market_data', sa.Column('indicators', sa.JSON(), nullable=True))
    op.add_column('market_data', sa.Column('raw_payload', sa.JSON(), nullable=True))

    # 更新默认值
    op.execute("UPDATE market_data SET source = 'akshare' WHERE source IS NULL")
    op.execute("UPDATE market_data SET market = 'CN' WHERE market IS NULL")
    op.execute("UPDATE market_data SET timeframe = '1d' WHERE timeframe IS NULL")
    op.execute("UPDATE market_data SET is_adjusted = false WHERE is_adjusted IS NULL")
    op.execute("UPDATE market_data SET indicators = '{}' WHERE indicators IS NULL")
    op.execute("UPDATE market_data SET raw_payload = '{}' WHERE raw_payload IS NULL")

    # 改为 NOT NULL
    op.alter_column('market_data', 'source', nullable=False)
    op.alter_column('market_data', 'market', nullable=False)
    op.alter_column('market_data', 'timeframe', nullable=False)
    op.alter_column('market_data', 'is_adjusted', nullable=False)
    op.alter_column('market_data', 'indicators', nullable=False)
    op.alter_column('market_data', 'raw_payload', nullable=False)


def downgrade():
    op.drop_column('market_data', 'raw_payload')
    op.drop_column('market_data', 'indicators')
    op.drop_column('market_data', 'is_adjusted')
    op.drop_column('market_data', 'adj_factor')
    op.drop_column('market_data', 'timeframe')
    op.drop_column('market_data', 'market')
    op.drop_column('market_data', 'source')
