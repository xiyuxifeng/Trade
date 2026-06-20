"""stage8 canonical strategy center foundation

Revision ID: 2026_06_20_0001
Revises: 2026_06_19_0014
Create Date: 2026-06-20
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_06_20_0001"
down_revision: Union[str, None] = "2026_06_19_0014"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def _uuid_type() -> sa.types.TypeEngine:
    return postgresql.UUID(as_uuid=True).with_variant(sa.Uuid(), "sqlite")


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return column_name in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    constraints = inspector.get_foreign_keys(table_name) + inspector.get_unique_constraints(table_name)
    return any(item.get("name") == constraint_name for item in constraints)


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(item.get("name") == index_name for item in inspector.get_indexes(table_name))


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_if_missing("strategy_versions", sa.Column("title", sa.String(length=256), nullable=True))
    _add_column_if_missing("strategy_versions", sa.Column("summary", sa.Text(), nullable=True))
    _add_column_if_missing("strategy_versions", sa.Column("review_status", sa.String(length=32), nullable=False, server_default="draft"))
    _add_column_if_missing("strategy_versions", sa.Column("review_reason", sa.Text(), nullable=True))
    _add_column_if_missing("strategy_versions", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("strategy_versions", sa.Column("reviewed_by", sa.String(length=64), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE strategy_versions
            SET review_status = CASE
                WHEN lifecycle_state = 'in_review' THEN 'pending_review'
                WHEN lifecycle_state = 'approved' THEN 'approved'
                WHEN lifecycle_state = 'published' THEN 'published'
                ELSE 'draft'
            END
            """
        )
    )
    op.alter_column("strategy_versions", "review_status", server_default=None)

    if not _constraint_exists("strategies", "fk_strategies_current_version"):
        op.create_foreign_key(
            "fk_strategies_current_version",
            "strategies",
            "strategy_versions",
            ["current_published_version_id"],
            ["strategy_version_id"],
            ondelete="SET NULL",
        )

    if not _table_exists("strategy_version_audits"):
        op.create_table(
            "strategy_version_audits",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("audit_id", _uuid_type(), nullable=False),
            sa.Column("strategy_version_id", _uuid_type(), nullable=False),
            sa.Column("transition", sa.String(length=64), nullable=False),
            sa.Column("actor_id", sa.String(length=128), nullable=False),
            sa.Column("actor_role", sa.String(length=32), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("source_surface", sa.String(length=128), nullable=False),
            sa.Column("before_state_json", _json_type(), nullable=True),
            sa.Column("after_state_json", _json_type(), nullable=True),
            sa.ForeignKeyConstraint(
                ["strategy_version_id"],
                ["strategy_versions.strategy_version_id"],
                name="fk_sva_audit_version",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("audit_id"),
        )
    if not _index_exists("strategy_version_audits", "ix_sva_audit_version_created"):
        op.create_index("ix_sva_audit_version_created", "strategy_version_audits", ["strategy_version_id", "created_at"])
    if not _index_exists("strategy_version_audits", "ix_sva_audit_transition"):
        op.create_index("ix_sva_audit_transition", "strategy_version_audits", ["transition"])
    if _column_exists("strategy_version_audits", "created_at"):
        op.alter_column("strategy_version_audits", "created_at", server_default=None)
    if _column_exists("strategy_version_audits", "updated_at"):
        op.alter_column("strategy_version_audits", "updated_at", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    audit_count = bind.execute(sa.text("SELECT COUNT(*) FROM strategy_version_audits")).scalar_one() if _table_exists("strategy_version_audits") else 0
    published_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM strategy_versions
            WHERE lifecycle_state = 'published'
               OR review_status = 'published'
            """
        )
    ).scalar_one()
    if audit_count or published_count:
        raise RuntimeError(
            "Refusing to downgrade RT-S8-001 because reviewed/published strategy version data exists. "
            "Retire or export formal strategy versions before rollback."
        )

    if _index_exists("strategy_version_audits", "ix_sva_audit_transition"):
        op.drop_index("ix_sva_audit_transition", table_name="strategy_version_audits")
    if _index_exists("strategy_version_audits", "ix_sva_audit_version_created"):
        op.drop_index("ix_sva_audit_version_created", table_name="strategy_version_audits")
    if _table_exists("strategy_version_audits"):
        op.drop_table("strategy_version_audits")
    if _constraint_exists("strategies", "fk_strategies_current_version"):
        op.drop_constraint("fk_strategies_current_version", "strategies", type_="foreignkey")
    for column in ("reviewed_by", "reviewed_at", "review_reason", "review_status", "summary", "title"):
        _drop_column_if_exists("strategy_versions", column)
