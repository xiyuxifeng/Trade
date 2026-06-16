"""Add Stage 4 canonical rule governance source links and fingerprint backfill."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.services.rule_governance_service import fingerprint_rule_payload


revision = "2026_06_16_0007"
down_revision = "2026_06_14_0006"
branch_labels = None
depends_on = None


rule_candidates = sa.table(
    "rule_candidates",
    sa.column("rule_candidate_id", postgresql.UUID(as_uuid=True)),
    sa.column("canonical_payload", postgresql.JSONB(astext_type=sa.Text())),
    sa.column("candidate_fingerprint", sa.String(length=64)),
)

rule_versions = sa.table(
    "rule_versions",
    sa.column("rule_version_id", postgresql.UUID(as_uuid=True)),
    sa.column("rule_type", sa.String(length=64)),
    sa.column("instrument_scope", postgresql.JSONB(astext_type=sa.Text())),
    sa.column("condition_json", postgresql.JSONB(astext_type=sa.Text())),
    sa.column("action_json", postgresql.JSONB(astext_type=sa.Text())),
    sa.column("parameter_json", postgresql.JSONB(astext_type=sa.Text())),
    sa.column("data_dependencies", postgresql.JSONB(astext_type=sa.Text())),
    sa.column("canonical_fingerprint", sa.String(length=64)),
)


def _version_payload(row) -> dict:
    parameter_json = row.parameter_json or {}
    instrument_scope = row.instrument_scope or {}
    data_dependencies = row.data_dependencies or {}
    return {
        "rule_type": row.rule_type,
        "instrument_focus": instrument_scope.get("instrument_focus") or [],
        "timeframe": parameter_json.get("timeframe"),
        "holding_period": parameter_json.get("holding_period"),
        "condition": row.condition_json or {},
        "action": row.action_json or {},
        "risk_controls": parameter_json.get("risk_controls") or [],
        "data_dependencies": data_dependencies.get("required") or [],
        "market_state_applicability": parameter_json.get("market_state_applicability") or {},
    }


def upgrade() -> None:
    op.create_table(
        "rule_version_source_links",
        sa.Column("rule_version_source_link_id", sa.Uuid(), nullable=False),
        sa.Column("rule_version_id", sa.Uuid(), nullable=False),
        sa.Column("rule_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("link_reason", sa.String(length=32), nullable=False, server_default=sa.text("'formal_source'")),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["rule_candidate_id"], ["rule_candidates.rule_candidate_id"], name="fk_rvsl_rule_candidate", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_version_id"], ["rule_versions.rule_version_id"], name="fk_rvsl_rule_version", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rule_version_source_link_id", name=op.f("pk_rule_version_source_links")),
    )
    op.create_index("uq_rvsl_rule_version_candidate", "rule_version_source_links", ["rule_version_id", "rule_candidate_id"], unique=True)
    op.create_index("uq_rvsl_candidate_version", "rule_version_source_links", ["rule_candidate_id", "rule_version_id"], unique=True)

    bind = op.get_bind()
    candidate_rows = bind.execute(sa.select(rule_candidates)).fetchall()
    for row in candidate_rows:
        payload = row.canonical_payload or {}
        exact = fingerprint_rule_payload(payload).exact_fingerprint
        bind.execute(
            rule_candidates.update()
            .where(rule_candidates.c.rule_candidate_id == row.rule_candidate_id)
            .values(candidate_fingerprint=exact)
        )

    version_rows = bind.execute(sa.select(rule_versions)).fetchall()
    for row in version_rows:
        exact = fingerprint_rule_payload(_version_payload(row)).exact_fingerprint
        bind.execute(
            rule_versions.update()
            .where(rule_versions.c.rule_version_id == row.rule_version_id)
            .values(canonical_fingerprint=exact)
        )

    op.execute(
        sa.text(
            """
            UPDATE rule_families
            SET canonical_fingerprint = canonical_fingerprint
            WHERE canonical_fingerprint IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE rule_family_memberships
            SET parameter_distance = parameter_distance
            WHERE parameter_distance IS NOT NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO rule_version_source_links (
                rule_version_source_link_id,
                rule_version_id,
                rule_candidate_id,
                link_reason,
                created_by,
                updated_by
            )
            SELECT gen_random_uuid(),
                   rv.rule_version_id,
                   rv.source_candidate_id,
                   'formal_source',
                   COALESCE(rv.created_by, 'migration'),
                   COALESCE(rv.updated_by, 'migration')
            FROM rule_versions AS rv
            WHERE rv.source_candidate_id IS NOT NULL
            ON CONFLICT DO NOTHING
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE rule_candidates
            SET candidate_fingerprint = candidate_fingerprint
            WHERE candidate_fingerprint IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("uq_rvsl_candidate_version", table_name="rule_version_source_links")
    op.drop_index("uq_rvsl_rule_version_candidate", table_name="rule_version_source_links")
    op.drop_table("rule_version_source_links")
