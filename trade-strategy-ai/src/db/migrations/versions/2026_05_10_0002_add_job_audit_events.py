"""Add job audit events table."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "2026_05_10_0002"
down_revision = "2026_05_08_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("params_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_audit_events_job_id_created_at", "job_audit_events", ["job_id", "created_at"])
    op.create_index("ix_job_audit_events_operation_created_at", "job_audit_events", ["operation", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_job_audit_events_operation_created_at", table_name="job_audit_events")
    op.drop_index("ix_job_audit_events_job_id_created_at", table_name="job_audit_events")
    op.drop_table("job_audit_events")
