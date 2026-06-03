"""把 alert_history 的时间列统一改为带时区时间戳。"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_06_03_0001"
down_revision = "2026_05_30_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "alert_history",
        "aggregation_window_start",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="aggregation_window_start AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "alert_history",
        "sent_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="sent_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "alert_history",
        "acknowledged_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="acknowledged_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "alert_history",
        "resolved_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="resolved_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "alert_history",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        "alert_history",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        nullable=False,
        server_default=None,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "alert_history",
        "resolved_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="resolved_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "alert_history",
        "acknowledged_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="acknowledged_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "alert_history",
        "sent_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="sent_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "alert_history",
        "aggregation_window_start",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="aggregation_window_start AT TIME ZONE 'UTC'",
    )
