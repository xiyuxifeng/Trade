"""Add stage 1 models and extend signal tracking columns."""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "2026_04_23_0001"
down_revision = "2026_04_17_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trader_strategy_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("trader_id", sa.String(64), nullable=False),
        sa.Column("strategy_date", sa.Date(), nullable=False),
        sa.Column("version_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, default="draft"),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("source_article_ids", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence_refs", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("strategy_payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trader_strategy_versions_trader_status", "trader_strategy_versions", ["trader_id", "status"])
    op.create_index("ix_trader_strategy_versions_strategy_date", "trader_strategy_versions", ["strategy_date"])
    op.create_unique_constraint(
        "uq_trader_strategy_versions_trader_id_strategy_date_version_name",
        "trader_strategy_versions",
        ["trader_id", "strategy_date", "version_name"],
    )
    op.create_index(
        "ux_trader_strategy_versions_one_released_per_day",
        "trader_strategy_versions",
        ["trader_id", "strategy_date"],
        unique=True,
        postgresql_where=sa.text("status = 'released'"),
    )

    op.create_table(
        "hot_topics_snapshots",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(16), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, default="kaipan"),
        sa.Column("dataset_version", sa.String(32), nullable=False, default="v1"),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("raw_payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_hot_topics_snapshots_trade_date_slot", "hot_topics_snapshots", ["trade_date", "slot"])
    op.create_unique_constraint(
        "uq_hot_topics_snapshots_identity",
        "hot_topics_snapshots",
        ["trade_date", "slot", "source", "dataset_version"],
    )

    op.create_table(
        "topic_constituents_snapshots",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(16), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, default="kaipan"),
        sa.Column("dataset_version", sa.String(32), nullable=False, default="v1"),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("raw_payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_topic_constituents_snapshots_trade_date_slot",
        "topic_constituents_snapshots",
        ["trade_date", "slot"],
    )
    op.create_unique_constraint(
        "uq_topic_constituents_snapshots_identity",
        "topic_constituents_snapshots",
        ["trade_date", "slot", "source", "dataset_version"],
    )

    op.create_table(
        "strong_symbols_snapshots",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(16), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, default="kaipan"),
        sa.Column("dataset_version", sa.String(32), nullable=False, default="v1"),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("raw_payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_strong_symbols_snapshots_trade_date_slot", "strong_symbols_snapshots", ["trade_date", "slot"])
    op.create_unique_constraint(
        "uq_strong_symbols_snapshots_identity",
        "strong_symbols_snapshots",
        ["trade_date", "slot", "source", "dataset_version"],
    )

    op.add_column("signals", sa.Column("trader_id", sa.String(64), nullable=True))
    op.add_column("signals", sa.Column("strategy_version_id", sa.String(128), nullable=True))
    op.add_column("signals", sa.Column("source_topic_ids", JSONB, nullable=True))
    op.add_column("signals", sa.Column("evidence_refs", JSONB, nullable=True))
    op.add_column("signals", sa.Column("decision_mode", sa.String(32), nullable=True))
    op.add_column("signals", sa.Column("evaluation_result_id", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("signals", "evaluation_result_id")
    op.drop_column("signals", "decision_mode")
    op.drop_column("signals", "evidence_refs")
    op.drop_column("signals", "source_topic_ids")
    op.drop_column("signals", "strategy_version_id")
    op.drop_column("signals", "trader_id")

    op.drop_table("strong_symbols_snapshots")
    op.drop_table("topic_constituents_snapshots")
    op.drop_table("hot_topics_snapshots")
    op.drop_table("trader_strategy_versions")
