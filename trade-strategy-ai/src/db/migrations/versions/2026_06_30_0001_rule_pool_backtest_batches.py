"""rule pool backtest batch runs

Revision ID: 2026_06_30_0001
Revises: 2026_06_20_0001
Create Date: 2026-06-30
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_06_30_0001"
down_revision: Union[str, None] = "2026_06_20_0001"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def _uuid_type() -> sa.types.TypeEngine:
    return postgresql.UUID(as_uuid=True).with_variant(sa.Uuid(), "sqlite")


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(item.get("name") == index_name for item in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _table_exists("rule_pool_backtest_batch_runs"):
        op.create_table(
            "rule_pool_backtest_batch_runs",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("batch_run_id", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("min_confidence", sa.Numeric(4, 3), nullable=False),
            sa.Column("market_regime_version", sa.String(length=128), nullable=True),
            sa.Column("profile_id", sa.String(length=128), nullable=True),
            sa.Column("selected_rule_count", sa.Integer(), nullable=False),
            sa.Column("batch_size", sa.Integer(), nullable=False),
            sa.Column("created_by", sa.String(length=128), nullable=True),
            sa.Column("merged_result_id", sa.String(length=128), nullable=True),
            sa.Column("config_json", _json_type(), nullable=False),
            sa.Column("fingerprint", sa.String(length=128), nullable=False),
            sa.PrimaryKeyConstraint("batch_run_id"),
        )
    if not _table_exists("rule_pool_backtest_batches"):
        op.create_table(
            "rule_pool_backtest_batches",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("batch_id", sa.String(length=128), nullable=False),
            sa.Column("batch_run_id", sa.String(length=128), nullable=False),
            sa.Column("batch_index", sa.Integer(), nullable=False),
            sa.Column("rule_ids_json", _json_type(), nullable=False),
            sa.Column("job_id", _uuid_type(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("result_json", _json_type(), nullable=True),
            sa.Column("result_artifact_id", sa.String(length=128), nullable=True),
            sa.Column("error_json", _json_type(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["batch_run_id"], ["rule_pool_backtest_batch_runs.batch_run_id"], name="fk_rpbt_batch_run", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name="fk_rpbt_batch_job", ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("batch_id"),
        )
    for table_name, column_name in (("rule_pool_backtest_batch_runs", "status"), ("rule_pool_backtest_batches", "status")):
        op.alter_column(table_name, column_name, server_default=None)
    if not _index_exists("rule_pool_backtest_batch_runs", "ix_rpbt_batch_runs_status_created"):
        op.create_index("ix_rpbt_batch_runs_status_created", "rule_pool_backtest_batch_runs", ["status", "created_at"])
    if not _index_exists("rule_pool_backtest_batch_runs", "ix_rpbt_batch_runs_fingerprint"):
        op.create_index("ix_rpbt_batch_runs_fingerprint", "rule_pool_backtest_batch_runs", ["fingerprint"])
    if not _index_exists("rule_pool_backtest_batches", "ix_rpbt_batches_run_index"):
        op.create_index("ix_rpbt_batches_run_index", "rule_pool_backtest_batches", ["batch_run_id", "batch_index"], unique=True)
    if not _index_exists("rule_pool_backtest_batches", "ix_rpbt_batches_status"):
        op.create_index("ix_rpbt_batches_status", "rule_pool_backtest_batches", ["status"])
    if not _index_exists("rule_pool_backtest_batches", "ix_rpbt_batches_job_id"):
        op.create_index("ix_rpbt_batches_job_id", "rule_pool_backtest_batches", ["job_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists("rule_pool_backtest_batch_runs"):
        active_count = bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM rule_pool_backtest_batch_runs
                WHERE status IN ('running', 'partial', 'completed', 'merged')
                   OR merged_result_id IS NOT NULL
                """
            )
        ).scalar_one()
        if active_count:
            raise RuntimeError(
                "Refusing to downgrade RT-PERF-001 because rule pool batch run results exist. "
                "Export or retire batch run records before rollback."
            )
    for index_name in ("ix_rpbt_batches_job_id", "ix_rpbt_batches_status", "ix_rpbt_batches_run_index"):
        if _index_exists("rule_pool_backtest_batches", index_name):
            op.drop_index(index_name, table_name="rule_pool_backtest_batches")
    for index_name in ("ix_rpbt_batch_runs_fingerprint", "ix_rpbt_batch_runs_status_created"):
        if _index_exists("rule_pool_backtest_batch_runs", index_name):
            op.drop_index(index_name, table_name="rule_pool_backtest_batch_runs")
    if _table_exists("rule_pool_backtest_batches"):
        op.drop_table("rule_pool_backtest_batches")
    if _table_exists("rule_pool_backtest_batch_runs"):
        op.drop_table("rule_pool_backtest_batch_runs")
