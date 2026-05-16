"""Create market data storage tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "2026_05_16_0002"
down_revision = "2026_05_16_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False, server_default=sa.text("'CN'")),
        sa.Column("profile_id", sa.String(length=128), nullable=True),
        sa.Column("data_version", sa.String(length=32), nullable=False, server_default=sa.text("'v1'")),
        sa.Column("slot", sa.String(length=16), nullable=False, server_default=sa.text("'17-30'")),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default=sa.text("'partial'")),
        sa.Column("provider_sources", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("section_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("available_section_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("partial_section_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("missing_section_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("storage_ref", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("summary_artifact_ref", sa.JSON(), nullable=True),
        sa.Column("quality_artifact_ref", sa.JSON(), nullable=True),
        sa.Column("data_quality", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_snapshots")),
        sa.UniqueConstraint("snapshot_id", name="uq_market_snapshots_snapshot_id"),
    )
    op.create_index("ix_market_snapshots_trade_date_market", "market_snapshots", ["trade_date", "market"])
    op.create_index("ix_market_snapshots_profile_trade_date", "market_snapshots", ["profile_id", "trade_date"])
    op.create_index("ix_market_snapshots_quality_status_trade_date", "market_snapshots", ["quality_status", "trade_date"])

    op.create_table(
        "market_snapshot_sections",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("section_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("source_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("missing_reason", sa.String(length=255), nullable=True),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default=sa.text("'missing'")),
        sa.Column("section_version", sa.String(length=32), nullable=True),
        sa.Column("storage_ref", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["market_snapshots.snapshot_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("snapshot_id", "section_id", name="uq_market_snapshot_sections_snapshot_section"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_snapshot_sections")),
    )
    op.create_index("ix_market_snapshot_sections_snapshot_quality", "market_snapshot_sections", ["snapshot_id", "quality_status"])
    op.create_index("ix_market_snapshot_sections_section_quality", "market_snapshot_sections", ["section_id", "quality_status"])

    op.create_table(
        "market_datasets",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("dataset_type", sa.String(length=64), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False, server_default=sa.text("'CN'")),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("storage_ref", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("profile_id", sa.String(length=128), nullable=True),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default=sa.text("'ok'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["market_snapshots.snapshot_id"], ondelete="SET NULL"),
        sa.UniqueConstraint("dataset_id", name="uq_market_datasets_dataset_id"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_datasets")),
    )
    op.create_index("ix_market_datasets_trade_date_market", "market_datasets", ["trade_date", "market"])
    op.create_index("ix_market_datasets_snapshot_id", "market_datasets", ["snapshot_id"])
    op.create_index("ix_market_datasets_type_trade_date", "market_datasets", ["dataset_type", "trade_date"])

    op.create_table(
        "market_snapshot_items",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("section_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("item_key", sa.String(length=128), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=True),
        sa.Column("source_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default=sa.text("'ok'")),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["market_snapshots.snapshot_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["market_datasets.dataset_id"], ondelete="SET NULL"),
        sa.UniqueConstraint("snapshot_id", "section_id", "item_key", name="uq_market_snapshot_items_identity"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_snapshot_items")),
    )
    op.create_index("ix_market_snapshot_items_snapshot_section", "market_snapshot_items", ["snapshot_id", "section_id"])
    op.create_index("ix_market_snapshot_items_snapshot_symbol", "market_snapshot_items", ["snapshot_id", "symbol"])
    op.create_index("ix_market_snapshot_items_dataset_id", "market_snapshot_items", ["dataset_id"])
    op.create_index("ix_market_snapshot_items_section_quality", "market_snapshot_items", ["section_id", "quality_status"])

    op.create_table(
        "market_data_quality_reports",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("overall_status", sa.String(length=32), nullable=False, server_default=sa.text("'partial'")),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("section_summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("report_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("storage_ref", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["market_snapshots.snapshot_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("snapshot_id", name="uq_market_data_quality_reports_snapshot_id"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_data_quality_reports")),
    )
    op.create_index("ix_market_data_quality_reports_status_created_at", "market_data_quality_reports", ["overall_status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_market_data_quality_reports_status_created_at", table_name="market_data_quality_reports")
    op.drop_table("market_data_quality_reports")

    op.drop_index("ix_market_snapshot_items_section_quality", table_name="market_snapshot_items")
    op.drop_index("ix_market_snapshot_items_dataset_id", table_name="market_snapshot_items")
    op.drop_index("ix_market_snapshot_items_snapshot_symbol", table_name="market_snapshot_items")
    op.drop_index("ix_market_snapshot_items_snapshot_section", table_name="market_snapshot_items")
    op.drop_table("market_snapshot_items")

    op.drop_index("ix_market_datasets_type_trade_date", table_name="market_datasets")
    op.drop_index("ix_market_datasets_snapshot_id", table_name="market_datasets")
    op.drop_index("ix_market_datasets_trade_date_market", table_name="market_datasets")
    op.drop_table("market_datasets")

    op.drop_index("ix_market_snapshot_sections_section_quality", table_name="market_snapshot_sections")
    op.drop_index("ix_market_snapshot_sections_snapshot_quality", table_name="market_snapshot_sections")
    op.drop_table("market_snapshot_sections")

    op.drop_index("ix_market_snapshots_quality_status_trade_date", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_profile_trade_date", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_trade_date_market", table_name="market_snapshots")
    op.drop_table("market_snapshots")

