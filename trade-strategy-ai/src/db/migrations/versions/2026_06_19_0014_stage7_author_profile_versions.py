"""stage7 author profile version lifecycle and time segments

Revision ID: 2026_06_19_0014
Revises: 2026_06_19_0013
Create Date: 2026-06-19
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_06_19_0014"
down_revision: Union[str, None] = "2026_06_19_0013"
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
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TYPE formal_lifecycle ADD VALUE IF NOT EXISTS 'pending_review'"))

    _add_column_if_missing("author_profile_versions", sa.Column("prompt_version", sa.String(length=64), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("evidence_from", sa.Date(), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("evidence_to", sa.Date(), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("effective_from", sa.Date(), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("effective_to", sa.Date(), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("source_rule_family_ids", _json_type(), nullable=False, server_default=sa.text("'{}'")))
    _add_column_if_missing("author_profile_versions", sa.Column("source_applicability_profile_ids", _json_type(), nullable=False, server_default=sa.text("'{}'")))
    _add_column_if_missing("author_profile_versions", sa.Column("source_backtest_result_ids", _json_type(), nullable=False, server_default=sa.text("'{}'")))
    _add_column_if_missing("author_profile_versions", sa.Column("source_versions_json", _json_type(), nullable=False, server_default=sa.text("'{}'")))
    _add_column_if_missing("author_profile_versions", sa.Column("evidence_fingerprint", sa.String(length=128), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("profile_fingerprint", sa.String(length=128), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("supersedes_version_id", _uuid_type(), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("superseded_by_version_id", _uuid_type(), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("review_status", sa.String(length=32), nullable=False, server_default="draft"))
    _add_column_if_missing("author_profile_versions", sa.Column("review_reason", sa.Text(), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("author_profile_versions", sa.Column("reviewed_by", sa.String(length=64), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE author_profile_versions
            SET evidence_from = COALESCE(as_of_from, evidence_from),
                evidence_to = COALESCE(as_of_to, evidence_to),
                effective_from = COALESCE(as_of_from, effective_from),
                effective_to = COALESCE(as_of_to, effective_to),
                review_status = CASE
                    WHEN lifecycle_state = 'in_review' THEN 'pending_review'
                    ELSE lifecycle_state::text
                END
            """
        )
    )

    if not _constraint_exists("author_profile_versions", "fk_apv_supersedes"):
        op.create_foreign_key(
            "fk_apv_supersedes",
            "author_profile_versions",
            "author_profile_versions",
            ["supersedes_version_id"],
            ["author_profile_version_id"],
            ondelete="SET NULL",
        )
    if not _constraint_exists("author_profile_versions", "fk_apv_superseded_by"):
        op.create_foreign_key(
            "fk_apv_superseded_by",
            "author_profile_versions",
            "author_profile_versions",
            ["superseded_by_version_id"],
            ["author_profile_version_id"],
            ondelete="SET NULL",
        )
    if not _index_exists("author_profile_versions", "ix_apv_author_kind_state"):
        op.create_index("ix_apv_author_kind_state", "author_profile_versions", ["author_id", "profile_kind", "lifecycle_state"])
    if not _index_exists("author_profile_versions", "ix_apv_kind_effective"):
        op.create_index("ix_apv_kind_effective", "author_profile_versions", ["author_profile_id", "profile_kind", "effective_from", "effective_to"])

    op.alter_column("author_profile_versions", "source_rule_family_ids", server_default=None)
    op.alter_column("author_profile_versions", "source_applicability_profile_ids", server_default=None)
    op.alter_column("author_profile_versions", "source_backtest_result_ids", server_default=None)
    op.alter_column("author_profile_versions", "source_versions_json", server_default=None)
    op.alter_column("author_profile_versions", "review_status", server_default=None)

    if not _table_exists("author_profile_version_audits"):
        op.create_table(
            "author_profile_version_audits",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("audit_id", _uuid_type(), nullable=False),
            sa.Column("author_profile_version_id", _uuid_type(), nullable=False),
            sa.Column("transition", sa.String(length=64), nullable=False),
            sa.Column("actor_id", sa.String(length=128), nullable=False),
            sa.Column("actor_role", sa.String(length=32), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("source_surface", sa.String(length=128), nullable=False),
            sa.Column("before_state_json", _json_type(), nullable=True),
            sa.Column("after_state_json", _json_type(), nullable=True),
            sa.ForeignKeyConstraint(
                ["author_profile_version_id"],
                ["author_profile_versions.author_profile_version_id"],
                name="fk_apv_audit_version",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("audit_id"),
        )
    if not _index_exists("author_profile_version_audits", "ix_apv_audit_profile_created"):
        op.create_index("ix_apv_audit_profile_created", "author_profile_version_audits", ["author_profile_version_id", "created_at"])
    if not _index_exists("author_profile_version_audits", "ix_apv_audit_transition"):
        op.create_index("ix_apv_audit_transition", "author_profile_version_audits", ["transition"])
    if _column_exists("author_profile_version_audits", "created_at"):
        op.alter_column("author_profile_version_audits", "created_at", server_default=None)
    if _column_exists("author_profile_version_audits", "updated_at"):
        op.alter_column("author_profile_version_audits", "updated_at", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    audit_count = bind.execute(sa.text("SELECT COUNT(*) FROM author_profile_version_audits")).scalar_one() if _table_exists("author_profile_version_audits") else 0
    published_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM author_profile_versions
            WHERE lifecycle_state IN ('published', 'archived')
               OR review_status IN ('published', 'archived')
            """
        )
    ).scalar_one()
    if audit_count or published_count:
        raise RuntimeError(
            "Refusing to downgrade RT-S7-004 because reviewed/published author profile version data exists. "
            "Export or explicitly retire these versions before rollback."
        )

    if _index_exists("author_profile_version_audits", "ix_apv_audit_transition"):
        op.drop_index("ix_apv_audit_transition", table_name="author_profile_version_audits")
    if _index_exists("author_profile_version_audits", "ix_apv_audit_profile_created"):
        op.drop_index("ix_apv_audit_profile_created", table_name="author_profile_version_audits")
    if _table_exists("author_profile_version_audits"):
        op.drop_table("author_profile_version_audits")
    if _index_exists("author_profile_versions", "ix_apv_kind_effective"):
        op.drop_index("ix_apv_kind_effective", table_name="author_profile_versions")
    if _index_exists("author_profile_versions", "ix_apv_author_kind_state"):
        op.drop_index("ix_apv_author_kind_state", table_name="author_profile_versions")
    if _constraint_exists("author_profile_versions", "fk_apv_superseded_by"):
        op.drop_constraint("fk_apv_superseded_by", "author_profile_versions", type_="foreignkey")
    if _constraint_exists("author_profile_versions", "fk_apv_supersedes"):
        op.drop_constraint("fk_apv_supersedes", "author_profile_versions", type_="foreignkey")
    for column in (
        "reviewed_by",
        "reviewed_at",
        "review_reason",
        "review_status",
        "superseded_by_version_id",
        "supersedes_version_id",
        "profile_fingerprint",
        "evidence_fingerprint",
        "source_versions_json",
        "source_backtest_result_ids",
        "source_applicability_profile_ids",
        "source_rule_family_ids",
        "effective_to",
        "effective_from",
        "evidence_to",
        "evidence_from",
        "prompt_version",
    ):
        _drop_column_if_exists("author_profile_versions", column)
