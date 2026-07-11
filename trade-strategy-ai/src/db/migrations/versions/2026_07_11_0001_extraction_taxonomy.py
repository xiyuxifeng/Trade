"""taxonomy-first extraction storage and RuleVersion lineage

Revision ID: 2026_07_11_0001
Revises: 2026_06_30_0001
Create Date: 2026-07-11
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_07_11_0001"
down_revision: Union[str, None] = "2026_06_30_0001"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


PRIMARY_TYPES = (
    "executable_rule",
    "rule_candidate",
    "research_hypothesis",
    "semantic_experience",
    "risk_control_hint",
    "data_requirement_hint",
    "unusable_noise",
)


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def _uuid_type() -> sa.types.TypeEngine:
    return postgresql.UUID(as_uuid=True).with_variant(sa.Uuid(), "sqlite")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "extraction_reclassification_runs",
        sa.Column("reclassification_run_id", _uuid_type(), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("source_population", sa.String(length=256), nullable=False),
        sa.Column("input_query_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("classifier", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_extraction_reclass_run_status",
        ),
        sa.PrimaryKeyConstraint("reclassification_run_id"),
    )
    op.create_index(
        "uq_extraction_reclass_identity",
        "extraction_reclassification_runs",
        ["taxonomy_version", "schema_version", "input_query_fingerprint", "classifier"],
        unique=True,
    )

    op.create_table(
        "extraction_items",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("extraction_item_id", _uuid_type(), nullable=False),
        sa.Column("article_id", _uuid_type(), nullable=False),
        sa.Column("article_revision_id", _uuid_type(), nullable=True),
        sa.Column("article_structure_id", _uuid_type(), nullable=False),
        sa.Column("prompt_run_id", _uuid_type(), nullable=False),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("item_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("primary_type", sa.String(length=32), nullable=False),
        sa.Column("secondary_tags", _json_type(), nullable=False),
        sa.Column("taxonomy_payload", _json_type(), nullable=False),
        sa.Column("source_evidence", _json_type(), nullable=False),
        sa.Column("confidence", _json_type(), nullable=False),
        sa.Column("quality_state", sa.String(length=32), nullable=False),
        sa.Column("review_destination", sa.String(length=48), nullable=False),
        sa.Column("review_state", sa.String(length=32), nullable=False),
        sa.Column("provenance", _json_type(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            f"primary_type IN ({_quoted(PRIMARY_TYPES)})",
            name="ck_extraction_item_primary_type",
        ),
        sa.CheckConstraint(
            "quality_state IN ('valid', 'partial', 'invalid', 'needs_review', 'rejected', 'superseded')",
            name="ck_extraction_item_quality_state",
        ),
        sa.CheckConstraint(
            "review_state IN ('unreviewed', 'queued', 'in_review', 'accepted', 'rejected', 'repaired', 'promoted', 'archived')",
            name="ck_extraction_item_review_state",
        ),
        sa.ForeignKeyConstraint(["article_id"], ["blog_articles.id"], name="fk_ei_article", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["article_revision_id"],
            ["article_revisions.article_revision_id"],
            name="fk_ei_revision",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["article_structure_id"],
            ["article_structures.article_structure_id"],
            name="fk_ei_structure",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prompt_run_id"], ["prompt_runs.prompt_run_id"], name="fk_ei_prompt_run", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("extraction_item_id"),
    )
    op.create_index("uq_extraction_item_run_index", "extraction_items", ["prompt_run_id", "item_index"], unique=True)
    op.create_index("uq_extraction_item_fingerprint", "extraction_items", ["item_fingerprint"], unique=True)
    op.create_index("ix_extraction_item_article_type", "extraction_items", ["article_id", "primary_type"])
    op.create_index(
        "ix_extraction_item_destination_state", "extraction_items", ["review_destination", "review_state"]
    )

    op.create_table(
        "extraction_reclassification_items",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reclassification_item_id", _uuid_type(), nullable=False),
        sa.Column("reclassification_run_id", _uuid_type(), nullable=False),
        sa.Column("old_rule_candidate_id", _uuid_type(), nullable=False),
        sa.Column("extraction_item_id", _uuid_type(), nullable=True),
        sa.Column("proposed_primary_type", sa.String(length=32), nullable=False),
        sa.Column("proposed_secondary_tags", _json_type(), nullable=False),
        sa.Column("proposed_taxonomy_payload", _json_type(), nullable=False),
        sa.Column("confidence", _json_type(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("review_state", sa.String(length=32), nullable=False),
        sa.Column("evidence_snapshot", _json_type(), nullable=False),
        sa.CheckConstraint(
            f"proposed_primary_type IN ({_quoted(PRIMARY_TYPES)})",
            name="ck_extraction_reclass_primary_type",
        ),
        sa.CheckConstraint(
            "review_state IN ('unreviewed', 'accepted', 'rejected', 'superseded')",
            name="ck_extraction_reclass_review_state",
        ),
        sa.ForeignKeyConstraint(
            ["reclassification_run_id"],
            ["extraction_reclassification_runs.reclassification_run_id"],
            name="fk_eri_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["old_rule_candidate_id"],
            ["rule_candidates.rule_candidate_id"],
            name="fk_eri_old_candidate",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_item_id"],
            ["extraction_items.extraction_item_id"],
            name="fk_eri_extraction_item",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("reclassification_item_id"),
    )
    op.create_index(
        "uq_extraction_reclass_candidate",
        "extraction_reclassification_items",
        ["reclassification_run_id", "old_rule_candidate_id"],
        unique=True,
    )

    with op.batch_alter_table("rule_versions") as batch_op:
        batch_op.add_column(sa.Column("source_extraction_item_id", _uuid_type(), nullable=True))
        batch_op.create_foreign_key(
            "fk_rv_source_extraction_item",
            "extraction_items",
            ["source_extraction_item_id"],
            ["extraction_item_id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "uq_rule_version_source_extraction_item",
        "rule_versions",
        ["source_extraction_item_id"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in ("extraction_reclassification_items", "extraction_items"):
        count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
        if count:
            raise RuntimeError(
                f"Refusing taxonomy rollback because {table_name} contains append-only evidence. Export it first."
            )
    linked_versions = bind.execute(
        sa.text("SELECT COUNT(*) FROM rule_versions WHERE source_extraction_item_id IS NOT NULL")
    ).scalar_one()
    if linked_versions:
        raise RuntimeError("Refusing taxonomy rollback because RuleVersion lineage depends on extraction items.")

    op.drop_index("uq_rule_version_source_extraction_item", table_name="rule_versions")
    with op.batch_alter_table("rule_versions") as batch_op:
        batch_op.drop_constraint("fk_rv_source_extraction_item", type_="foreignkey")
        batch_op.drop_column("source_extraction_item_id")
    op.drop_index("uq_extraction_reclass_candidate", table_name="extraction_reclassification_items")
    op.drop_table("extraction_reclassification_items")
    op.drop_index("ix_extraction_item_destination_state", table_name="extraction_items")
    op.drop_index("ix_extraction_item_article_type", table_name="extraction_items")
    op.drop_index("uq_extraction_item_fingerprint", table_name="extraction_items")
    op.drop_index("uq_extraction_item_run_index", table_name="extraction_items")
    op.drop_table("extraction_items")
    op.drop_index("uq_extraction_reclass_identity", table_name="extraction_reclassification_runs")
    op.drop_table("extraction_reclassification_runs")
