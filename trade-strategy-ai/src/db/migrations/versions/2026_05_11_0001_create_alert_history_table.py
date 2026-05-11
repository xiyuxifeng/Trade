"""
create alert_history table
"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import uuid

# revision identifiers, used by Alembic.
revision = '2026_05_11_0001'
down_revision = '2026_05_10_0002'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'alert_history',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('alert_id', sa.String(100), nullable=False),
        sa.Column('level', sa.String(20), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('tags', pg.JSONB, default=list),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('aggregated_count', sa.Integer, default=1),
        sa.Column('aggregation_key', sa.String(255), nullable=True),
        sa.Column('aggregation_window_start', sa.DateTime, nullable=True),
        sa.Column('sent_at', sa.DateTime, nullable=True),
        sa.Column('acknowledged_at', sa.DateTime, nullable=True),
        sa.Column('acknowledged_by', sa.String(100), nullable=True),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('resolved_by', sa.String(100), nullable=True),
        sa.Column('metadata', pg.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Index('idx_alert_history_status', 'status'),
        sa.Index('idx_alert_history_level', 'level'),
        sa.Index('idx_alert_history_created_at', 'created_at'),
        sa.Index('idx_alert_history_aggregation_key', 'aggregation_key'),
    )

def downgrade():
    op.drop_table('alert_history')
