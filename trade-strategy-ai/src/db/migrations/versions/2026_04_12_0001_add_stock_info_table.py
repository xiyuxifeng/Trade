"""
添加 stock_info 表 - 股票基本信息映射表
用于元数据提取时将中文股票名称转换为标准代码
"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = '2026_04_12_0001'
down_revision = '202604110002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'stock_info',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('symbol', sa.String(32), nullable=False),
        sa.Column('code', sa.String(16), nullable=False),
        sa.Column('market', sa.String(8), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('security_type', sa.String(32), nullable=False, default='stock'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    # 唯一约束
    op.create_unique_constraint('uq_stock_info_symbol', 'stock_info', ['symbol'])
    op.create_unique_constraint('uq_stock_info_symbol_market', 'stock_info', ['symbol', 'market'])
    # 索引
    op.create_index('ix_stock_info_name', 'stock_info', ['name'])
    op.create_index('ix_stock_info_code', 'stock_info', ['code'])


def downgrade():
    op.drop_table('stock_info')
