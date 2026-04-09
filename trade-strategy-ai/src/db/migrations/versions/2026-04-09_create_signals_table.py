"""Create signals table

Revision ID: 2026_04_09_001
Revises: 20260407_001
Create Date: 2026-04-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '2026_04_09_001'
down_revision = '20260407_001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('signal_id', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('triggered_rules', JSONB(), nullable=True),
        sa.Column('synthesis_mode', sa.String(20), nullable=True),
        sa.Column('entry_price', JSONB(), nullable=True),
        sa.Column('position_size', JSONB(), nullable=True),
        sa.Column('stop_loss', JSONB(), nullable=True),
        sa.Column('take_profit', JSONB(), nullable=True),
        sa.Column('rejected', sa.Boolean(), default=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('degraded', sa.Boolean(), default=False),
        sa.Column('degradation_reason', sa.Text(), nullable=True),
        sa.Column('version', sa.String(10), nullable=True),
        sa.Column('metadata', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_signals_symbol', 'signals', ['symbol'])
    op.create_index('idx_signals_created_at', 'signals', ['created_at'])
    op.create_index('idx_signals_signal_id', 'signals', ['signal_id'])

def downgrade() -> None:
    op.drop_table('signals')