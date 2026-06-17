"""Stage 5 Kaipan slot, provenance, and immutable MarketSnapshot contract."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_06_17_0009"
down_revision: Union[str, None] = "2026_06_17_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _unique_constraints(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name)}


def _indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    snapshot_columns = _columns("market_snapshots")
    if "source_time" not in snapshot_columns:
        op.add_column("market_snapshots", sa.Column("source_time", sa.DateTime(timezone=True), nullable=True))
    if "ingested_at" not in snapshot_columns:
        op.add_column("market_snapshots", sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True))
    if "frozen_at" not in snapshot_columns:
        op.add_column("market_snapshots", sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True))

    section_columns = _columns("market_snapshot_sections")
    if "trade_date" not in section_columns:
        op.add_column("market_snapshot_sections", sa.Column("trade_date", sa.Date(), nullable=True))
    if "slot" not in section_columns:
        op.add_column("market_snapshot_sections", sa.Column("slot", sa.String(length=16), nullable=True))
    if "source_dataset" not in section_columns:
        op.add_column("market_snapshot_sections", sa.Column("source_dataset", sa.String(length=64), nullable=True))
    if "captured_at" not in section_columns:
        op.add_column("market_snapshot_sections", sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True))
    if "ingested_at" not in section_columns:
        op.add_column("market_snapshot_sections", sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True))
    if "available_at" not in section_columns:
        op.add_column("market_snapshot_sections", sa.Column("available_at", sa.DateTime(timezone=True), nullable=True))
    if "raw_payload_fingerprint" not in section_columns:
        op.add_column("market_snapshot_sections", sa.Column("raw_payload_fingerprint", sa.String(length=64), nullable=True))
    if "normalization_version" not in section_columns:
        op.add_column("market_snapshot_sections", sa.Column("normalization_version", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE market_snapshots
            SET source_time = COALESCE(source_time, available_at),
                ingested_at = COALESCE(ingested_at, effective_at, available_at, captured_at, created_at),
                frozen_at = COALESCE(frozen_at, effective_at, ingested_at, available_at, captured_at, created_at)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE market_snapshot_sections AS sec
            SET trade_date = snap.trade_date,
                slot = snap.slot,
                source_dataset = COALESCE(sec.source_dataset, sec.section_id),
                captured_at = COALESCE(sec.captured_at, snap.captured_at),
                ingested_at = COALESCE(sec.ingested_at, snap.ingested_at, snap.effective_at, snap.available_at, snap.captured_at),
                available_at = COALESCE(sec.available_at, snap.available_at),
                raw_payload_fingerprint = COALESCE(sec.raw_payload_fingerprint, md5(sec.snapshot_id || ':' || sec.section_id || ':' || CAST(sec.payload_json AS TEXT))),
                normalization_version = COALESCE(sec.normalization_version, 'kaipan-normalizer-v2')
            FROM market_snapshots AS snap
            WHERE sec.snapshot_id = snap.snapshot_id
            """
        )
    )

    for column_name in ("ingested_at", "frozen_at"):
        op.alter_column("market_snapshots", column_name, nullable=False)
    for column_name in (
        "trade_date",
        "slot",
        "source_dataset",
        "captured_at",
        "ingested_at",
        "available_at",
        "raw_payload_fingerprint",
        "normalization_version",
    ):
        op.alter_column("market_snapshot_sections", column_name, nullable=False)

    existing_constraints = _unique_constraints("market_snapshots")
    if "uq_market_snapshots_market_date_slot_version" in existing_constraints:
        op.drop_constraint("uq_market_snapshots_market_date_slot_version", "market_snapshots", type_="unique")
    existing_indexes = _indexes("market_snapshots")
    if "ix_market_snapshots_trade_date_slot" not in existing_indexes:
        op.create_index("ix_market_snapshots_trade_date_slot", "market_snapshots", ["trade_date", "slot"])


def downgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT market, trade_date, slot, data_version, COUNT(*) AS row_count
            FROM market_snapshots
            GROUP BY market, trade_date, slot, data_version
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError(
            "market_snapshots contains multiple frozen versions for the same market/trade_date/slot/data_version; "
            "Stage 5 Kaipan downgrade would collapse immutable snapshots"
        )

    existing_constraints = _unique_constraints("market_snapshots")
    if "uq_market_snapshots_market_date_slot_version" not in existing_constraints:
        op.create_unique_constraint(
            "uq_market_snapshots_market_date_slot_version",
            "market_snapshots",
            ["market", "trade_date", "slot", "data_version"],
        )
    existing_indexes = _indexes("market_snapshots")
    if "ix_market_snapshots_trade_date_slot" in existing_indexes:
        op.drop_index("ix_market_snapshots_trade_date_slot", table_name="market_snapshots")

    for column_name in (
        "normalization_version",
        "raw_payload_fingerprint",
        "available_at",
        "ingested_at",
        "captured_at",
        "source_dataset",
        "slot",
        "trade_date",
    ):
        if column_name in _columns("market_snapshot_sections"):
            op.drop_column("market_snapshot_sections", column_name)

    for column_name in ("frozen_at", "ingested_at", "source_time"):
        if column_name in _columns("market_snapshots"):
            op.drop_column("market_snapshots", column_name)
