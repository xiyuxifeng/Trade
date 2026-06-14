"""Stage 2 compatibility views for renamed legacy read paths."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "2026_06_14_0004"
down_revision = "2026_06_14_0003"
branch_labels = None
depends_on = None


def _drop_view(name: str) -> None:
    op.execute(sa.text(f"DROP VIEW IF EXISTS {name}"))


def upgrade() -> None:
    _drop_view("market_datasets")
    _drop_view("strategy_regime_selections")
    _drop_view("regime_rule_selections")

    op.execute(
        sa.text(
            """
            CREATE VIEW market_datasets AS
            SELECT
                dataset_snapshot_id AS id,
                content_fingerprint AS dataset_id,
                COALESCE(dataset_type, 'dataset_snapshot') AS dataset_type,
                trade_date,
                market,
                NULL::varchar(64) AS source,
                storage_ref::json AS storage_ref,
                NULL::varchar(128) AS snapshot_id,
                NULL::varchar(128) AS profile_id,
                CASE lifecycle_state::text
                    WHEN 'ready' THEN 'ok'
                    WHEN 'partial' THEN 'partial'
                    WHEN 'invalid' THEN 'unresolved'
                    ELSE 'ok'
                END::varchar(32) AS quality_status,
                created_at,
                updated_at
            FROM dataset_snapshots
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE VIEW strategy_regime_selections AS
            SELECT
                daily_rule_selection_id::varchar(64) AS selection_id,
                strategy_version_id::varchar(128) AS strategy_version_id,
                NULL::varchar(128) AS snapshot_id,
                NULL::varchar(64) AS market_regime_version,
                NULL::varchar(64) AS source_feature_version,
                NULL::varchar(64) AS applicability_profile_version,
                CASE
                    WHEN jsonb_typeof(selected_rules_json) = 'array' THEN jsonb_array_length(selected_rules_json)
                    ELSE 0
                END AS selected_rule_count,
                CASE
                    WHEN jsonb_typeof(reduced_rules_json) = 'array' THEN jsonb_array_length(reduced_rules_json)
                    ELSE 0
                END AS skipped_rule_count,
                CASE
                    WHEN jsonb_typeof(blocked_rules_json) = 'array' THEN jsonb_array_length(blocked_rules_json)
                    ELSE 0
                END AS blocked_rule_count,
                0::double precision AS confidence,
                quality_status::text::varchar(32) AS quality_status,
                NULL::varchar(255) AS selection_reason,
                '[]'::jsonb AS evidence_json,
                '{}'::jsonb AS override_json,
                created_by AS selected_by,
                '{}'::jsonb AS storage_ref,
                '{}'::jsonb AS artifact_ref,
                created_at,
                updated_at
            FROM daily_rule_selections
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE VIEW regime_rule_selections AS
            SELECT
                daily_rule_selection_item_id::varchar(64) AS item_id,
                daily_rule_selection_id::varchar(64) AS selection_id,
                rule_version_id::varchar(128) AS rule_id,
                COALESCE(decision, 'selected') AS decision,
                0::double precision AS score,
                NULL::varchar(255) AS reason,
                '[]'::jsonb AS evidence_json,
                NULL::varchar(64) AS regime_version,
                NULL::varchar(64) AS applicability_profile_version,
                0::integer AS sample_count,
                0::double precision AS profile_confidence,
                false AS override_applied,
                NULL::varchar(64) AS rule_applicability_profile_id,
                created_at,
                updated_at
            FROM daily_rule_selection_items
            """
        )
    )


def downgrade() -> None:
    _drop_view("regime_rule_selections")
    _drop_view("strategy_regime_selections")
    _drop_view("market_datasets")
