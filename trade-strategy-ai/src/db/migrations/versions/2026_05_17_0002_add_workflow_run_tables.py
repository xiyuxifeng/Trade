"""add workflow run tables

Revision ID: 2026_05_17_0002
Revises: 2026_05_17_0001
Create Date: 2026-05-17
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_05_17_0002"
down_revision: Union[str, None] = "2026_05_17_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_title", sa.String(length=255), nullable=False),
        sa.Column("workflow_version", sa.String(length=64), nullable=False, server_default=sa.text("'workflow-v1'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("trigger_source", sa.String(length=64), nullable=False, server_default=sa.text("'system'")),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_params_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_runs_workflow_id_created_at", "workflow_runs", ["workflow_id", "created_at"], unique=False)
    op.create_index("ix_workflow_runs_status_created_at", "workflow_runs", ["status", "created_at"], unique=False)
    op.create_index("ix_workflow_runs_created_by_created_at", "workflow_runs", ["created_by", "created_at"], unique=False)
    op.create_index("ix_workflow_runs_trigger_source_created_at", "workflow_runs", ["trigger_source", "created_at"], unique=False)

    op.create_table(
        "workflow_run_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_id", sa.String(length=128), nullable=False),
        sa.Column("step_name", sa.String(length=255), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=128), nullable=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("artifact_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_run_id", "step_order", name="uq_workflow_run_steps_run_order"),
    )
    op.create_index("ix_workflow_run_steps_workflow_run_id", "workflow_run_steps", ["workflow_run_id"], unique=False)
    op.create_index("ix_workflow_run_steps_job_id", "workflow_run_steps", ["job_id"], unique=False)
    op.create_index("ix_workflow_run_steps_step_id", "workflow_run_steps", ["step_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workflow_run_steps_step_id", table_name="workflow_run_steps")
    op.drop_index("ix_workflow_run_steps_job_id", table_name="workflow_run_steps")
    op.drop_index("ix_workflow_run_steps_workflow_run_id", table_name="workflow_run_steps")
    op.drop_table("workflow_run_steps")

    op.drop_index("ix_workflow_runs_trigger_source_created_at", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_created_by_created_at", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_status_created_at", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_workflow_id_created_at", table_name="workflow_runs")
    op.drop_table("workflow_runs")
