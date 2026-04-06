"""Add data audit events table."""

from alembic import op
import sqlalchemy as sa


revision = "20260406_004"
down_revision = "20260406_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128)),
        sa.Column("dataset_version", sa.String(128)),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_data_audit_events_created_at", "data_audit_events", ["created_at"])
    op.create_index(
        "ix_data_audit_events_event_type_created_at",
        "data_audit_events",
        ["event_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_data_audit_events_event_type_created_at", table_name="data_audit_events")
    op.drop_index("ix_data_audit_events_created_at", table_name="data_audit_events")
    op.drop_table("data_audit_events")
