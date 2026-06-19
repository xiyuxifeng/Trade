"""stage6 rule applicability profile formal contract

Revision ID: 2026_06_19_0013
Revises: 2026_06_19_0012
Create Date: 2026-06-19
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2026_06_19_0013"
down_revision: Union[str, None] = "2026_06_19_0012"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def _uuid_type() -> sa.types.TypeEngine:
    return postgresql.UUID(as_uuid=True).with_variant(sa.Uuid(), "sqlite")


def upgrade() -> None:
    op.add_column("rule_applicability_profiles", sa.Column("rule_version_fingerprint", sa.String(length=128), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("rule_version_no", sa.Integer(), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("rule_family_id", _uuid_type(), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("rule_family_fingerprint", sa.String(length=128), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("frozen_rule_version_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("rule_applicability_profiles", sa.Column("frozen_rule_version_fingerprints", _json_type(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("rule_applicability_profiles", sa.Column("dataset_fingerprint", sa.String(length=128), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("market_state_model_version", sa.String(length=64), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("market_state_source_version", sa.String(length=64), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("profile_version_no", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("rule_applicability_profiles", sa.Column("source_backtest_run_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("rule_applicability_profiles", sa.Column("source_backtest_result_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("rule_applicability_profiles", sa.Column("source_result_fingerprints", _json_type(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("rule_applicability_profiles", sa.Column("market_snapshot_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("rule_applicability_profiles", sa.Column("market_snapshot_fingerprints", _json_type(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("rule_applicability_profiles", sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("rule_applicability_profiles", sa.Column("eligible_sample_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("rule_applicability_profiles", sa.Column("evaluated_sample_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("rule_applicability_profiles", sa.Column("coverage", sa.Float(), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("return_metric", sa.Float(), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("win_rate", sa.Float(), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("maximum_drawdown", sa.Float(), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("recommendation_status", sa.String(length=32), nullable=False, server_default="unavailable"))
    op.add_column("rule_applicability_profiles", sa.Column("data_level", sa.String(length=32), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("requested_level", sa.String(length=32), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("effective_level", sa.String(length=32), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("level_policy_version", sa.String(length=64), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="partial"))
    op.add_column("rule_applicability_profiles", sa.Column("insufficient_sample_status", sa.String(length=32), nullable=False, server_default="unknown"))
    op.add_column("rule_applicability_profiles", sa.Column("limitations", _json_type(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("rule_applicability_profiles", sa.Column("warnings", _json_type(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("rule_applicability_profiles", sa.Column("recommendation_policy_version", sa.String(length=64), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("review_reason", sa.Text(), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("created_by", sa.String(length=128), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("supersedes_profile_id", _uuid_type(), nullable=True))
    op.add_column("rule_applicability_profiles", sa.Column("superseded_by_profile_id", _uuid_type(), nullable=True))

    op.create_index("ix_rap_rule_version_review", "rule_applicability_profiles", ["rule_version_id", "review_status"])
    op.create_index("ix_rap_rule_family_review", "rule_applicability_profiles", ["rule_family_id", "review_status"])
    op.create_index("ix_rap_source_result", "rule_applicability_profiles", ["source_backtest_id", "profile_version_no"])
    op.drop_constraint("uq_rule_applicability_profiles_rule_profile_source", "rule_applicability_profiles", type_="unique")
    op.create_unique_constraint(
        "uq_rule_applicability_profiles_rule_profile_source",
        "rule_applicability_profiles",
        ["rule_id", "profile_version", "source_backtest_id", "profile_version_no"],
    )
    op.create_foreign_key("fk_rap_rule_family", "rule_applicability_profiles", "rule_families", ["rule_family_id"], ["rule_family_id"], ondelete="SET NULL")

    op.alter_column("rule_applicability_profiles", "frozen_rule_version_ids", server_default=None)
    op.alter_column("rule_applicability_profiles", "frozen_rule_version_fingerprints", server_default=None)
    op.alter_column("rule_applicability_profiles", "profile_version_no", server_default=None)
    op.alter_column("rule_applicability_profiles", "source_backtest_run_ids", server_default=None)
    op.alter_column("rule_applicability_profiles", "source_backtest_result_ids", server_default=None)
    op.alter_column("rule_applicability_profiles", "source_result_fingerprints", server_default=None)
    op.alter_column("rule_applicability_profiles", "market_snapshot_ids", server_default=None)
    op.alter_column("rule_applicability_profiles", "market_snapshot_fingerprints", server_default=None)
    op.alter_column("rule_applicability_profiles", "sample_count", server_default=None)
    op.alter_column("rule_applicability_profiles", "eligible_sample_count", server_default=None)
    op.alter_column("rule_applicability_profiles", "evaluated_sample_count", server_default=None)
    op.alter_column("rule_applicability_profiles", "recommendation_status", server_default=None)
    op.alter_column("rule_applicability_profiles", "quality_status", server_default=None)
    op.alter_column("rule_applicability_profiles", "insufficient_sample_status", server_default=None)
    op.alter_column("rule_applicability_profiles", "limitations", server_default=None)
    op.alter_column("rule_applicability_profiles", "warnings", server_default=None)

    op.create_table(
        "rule_applicability_profile_audits",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("audit_id", _uuid_type(), nullable=False),
        sa.Column("profile_id", _uuid_type(), nullable=False),
        sa.Column("transition", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source_surface", sa.String(length=128), nullable=False, server_default="/rules/backtests"),
        sa.Column("before_state_json", _json_type(), nullable=True),
        sa.Column("after_state_json", _json_type(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["rule_applicability_profiles.profile_id"], name="fk_rap_audit_profile", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_rap_audit_profile_created", "rule_applicability_profile_audits", ["profile_id", "created_at"])
    op.create_index("ix_rap_audit_transition", "rule_applicability_profile_audits", ["transition"])
    op.alter_column("rule_applicability_profile_audits", "created_at", server_default=None)
    op.alter_column("rule_applicability_profile_audits", "updated_at", server_default=None)
    op.alter_column("rule_applicability_profile_audits", "source_surface", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    audit_count = bind.execute(sa.text("SELECT COUNT(*) FROM rule_applicability_profile_audits")).scalar_one()
    if audit_count:
        raise RuntimeError(
            "Refusing to downgrade RT-S6-003 because formal RuleApplicabilityProfile audit data exists. "
            "Export or explicitly archive formal profiles before rollback."
        )
    op.drop_index("ix_rap_audit_transition", table_name="rule_applicability_profile_audits")
    op.drop_index("ix_rap_audit_profile_created", table_name="rule_applicability_profile_audits")
    op.drop_table("rule_applicability_profile_audits")
    op.drop_constraint("uq_rule_applicability_profiles_rule_profile_source", "rule_applicability_profiles", type_="unique")
    op.create_unique_constraint(
        "uq_rule_applicability_profiles_rule_profile_source",
        "rule_applicability_profiles",
        ["rule_id", "profile_version", "source_backtest_id"],
    )
    op.drop_constraint("fk_rap_rule_family", "rule_applicability_profiles", type_="foreignkey")
    op.drop_index("ix_rap_source_result", table_name="rule_applicability_profiles")
    op.drop_index("ix_rap_rule_family_review", table_name="rule_applicability_profiles")
    op.drop_index("ix_rap_rule_version_review", table_name="rule_applicability_profiles")
    for column in (
        "superseded_by_profile_id",
        "supersedes_profile_id",
        "created_by",
        "review_reason",
        "recommendation_policy_version",
        "warnings",
        "limitations",
        "insufficient_sample_status",
        "quality_status",
        "level_policy_version",
        "effective_level",
        "requested_level",
        "data_level",
        "recommendation_status",
        "maximum_drawdown",
        "win_rate",
        "return_metric",
        "coverage",
        "evaluated_sample_count",
        "eligible_sample_count",
        "sample_count",
        "market_snapshot_fingerprints",
        "market_snapshot_ids",
        "source_result_fingerprints",
        "source_backtest_result_ids",
        "source_backtest_run_ids",
        "profile_version_no",
        "market_state_source_version",
        "market_state_model_version",
        "dataset_fingerprint",
        "frozen_rule_version_fingerprints",
        "frozen_rule_version_ids",
        "rule_family_fingerprint",
        "rule_family_id",
        "rule_version_no",
        "rule_version_fingerprint",
    ):
        op.drop_column("rule_applicability_profiles", column)
