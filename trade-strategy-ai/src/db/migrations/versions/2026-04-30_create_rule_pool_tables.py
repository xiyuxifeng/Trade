"""
迁移：创建 rule_pool、trade_sample、article_classification 三张表
创建时间：2026-04-30
"""
from alembic import op
import sqlalchemy as sa
import uuid

# 迁移版本号
revision = '2026_04_30_0002'
down_revision = '2026_04_30_0001'
branch_labels = None
depends_on = None


def upgrade():
    # 创建 rule_pool 表 - 规则池表
    op.create_table(
        'rule_pool',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('rule_id', sa.String(128), nullable=False, unique=True),
        sa.Column('source_article_ids', sa.JSON, nullable=False, default=list),
        sa.Column('source_type', sa.String(32), nullable=False),
        sa.Column('rule_type', sa.String(64), nullable=False),
        sa.Column('instrument_focus', sa.String(32), nullable=False, default='mixed'),
        sa.Column('extraction_layer', sa.JSON, nullable=False, default=dict),
        sa.Column('mapping_status', sa.String(32), nullable=False, default='unmapped'),
        sa.Column('mapped_by', sa.String(64), nullable=True),
        sa.Column('mapped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('initial_confidence', sa.Numeric(4, 3), nullable=False),
        sa.Column('validated_confidence', sa.Numeric(4, 3), nullable=True),
        sa.Column('review_status', sa.String(32), nullable=False, default='pending'),
        sa.Column('reviewed_by', sa.String(64), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('backtest_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('backtest_result', sa.JSON, nullable=True),
        sa.Column('backtest_hits', sa.Integer, nullable=False, default=0),
        sa.Column('backtest_misses', sa.Integer, nullable=False, default=0),
        sa.Column('backtest_samples', sa.Integer, nullable=False, default=0),
        sa.Column('used_in_prediction', sa.Boolean, nullable=False, default=False),
        sa.Column('prediction_count', sa.Integer, nullable=False, default=0),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # 创建 rule_pool 表的索引
    op.create_index('ix_rule_pool_rule_id', 'rule_pool', ['rule_id'])
    op.create_index('ix_rule_pool_rule_type', 'rule_pool', ['rule_type'])
    op.create_index('ix_rule_pool_mapping_status', 'rule_pool', ['mapping_status'])
    op.create_index('ix_rule_pool_review_status', 'rule_pool', ['review_status'])
    op.create_index('ix_rule_pool_created_at', 'rule_pool', ['created_at'])

    # 创建 trade_sample 表 - 交易样本表
    op.create_table(
        'trade_sample',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('sample_id', sa.String(128), nullable=False, unique=True),
        sa.Column('article_id', sa.String(128), nullable=True),
        sa.Column('rule_id', sa.String(128), nullable=True),
        sa.Column('symbol', sa.String(32), nullable=False),
        sa.Column('side', sa.String(16), nullable=False),
        sa.Column('entry_price', sa.Numeric(18, 6), nullable=False),
        sa.Column('exit_price', sa.Numeric(18, 6), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 6), nullable=False),
        sa.Column('entry_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pnl', sa.Numeric(18, 4), nullable=True),
        sa.Column('pnl_pct', sa.Numeric(8, 4), nullable=True),
        sa.Column('holding_period', sa.Integer, nullable=True),
        sa.Column('tags', sa.JSON, nullable=False, default=list),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # 创建 trade_sample 表的索引
    op.create_index('ix_trade_sample_sample_id', 'trade_sample', ['sample_id'])
    op.create_index('ix_trade_sample_symbol', 'trade_sample', ['symbol'])
    op.create_index('ix_trade_sample_entry_at', 'trade_sample', ['entry_at'])
    op.create_index('ix_trade_sample_article_id', 'trade_sample', ['article_id'])
    op.create_index('ix_trade_sample_rule_id', 'trade_sample', ['rule_id'])

    # 创建 article_classification 表 - 文章分类表
    op.create_table(
        'article_classification',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('article_id', sa.String(128), nullable=False, unique=True),
        sa.Column('article_type', sa.String(32), nullable=False),
        sa.Column('confidence', sa.Numeric(4, 3), nullable=False),
        sa.Column('classified_by', sa.String(64), nullable=True),
        sa.Column('classified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reasons', sa.JSON, nullable=False, default=list),
        sa.Column('extra_metadata', sa.JSON, nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # 创建 article_classification 表的索引
    op.create_index('ix_article_classification_article_id', 'article_classification', ['article_id'])
    op.create_index('ix_article_classification_article_type', 'article_classification', ['article_type'])
    op.create_index('ix_article_classification_confidence', 'article_classification', ['confidence'])


def downgrade():
    # 删除 article_classification 表
    op.drop_index('ix_article_classification_confidence', table_name='article_classification')
    op.drop_index('ix_article_classification_article_type', table_name='article_classification')
    op.drop_index('ix_article_classification_article_id', table_name='article_classification')
    op.drop_table('article_classification')

    # 删除 trade_sample 表
    op.drop_index('ix_trade_sample_rule_id', table_name='trade_sample')
    op.drop_index('ix_trade_sample_article_id', table_name='trade_sample')
    op.drop_index('ix_trade_sample_entry_at', table_name='trade_sample')
    op.drop_index('ix_trade_sample_symbol', table_name='trade_sample')
    op.drop_index('ix_trade_sample_sample_id', table_name='trade_sample')
    op.drop_table('trade_sample')

    # 删除 rule_pool 表
    op.drop_index('ix_rule_pool_created_at', table_name='rule_pool')
    op.drop_index('ix_rule_pool_review_status', table_name='rule_pool')
    op.drop_index('ix_rule_pool_mapping_status', table_name='rule_pool')
    op.drop_index('ix_rule_pool_rule_type', table_name='rule_pool')
    op.drop_index('ix_rule_pool_rule_id', table_name='rule_pool')
    op.drop_table('rule_pool')