"""Stage 5 OHLCV identity and time contract alignment."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Sequence, Union
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa


revision: str = "2026_06_17_0008"
down_revision: Union[str, None] = "2026_06_16_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _unique_constraints(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name)}


def _trade_datetime(value, hour: int) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time(hour=hour), SHANGHAI).astimezone(UTC)


ohlcv_bars = sa.table(
    "ohlcv_bars",
    sa.column("id", sa.Uuid()),
    sa.column("symbol", sa.String(length=32)),
    sa.column("trade_date", sa.Date()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
    sa.column("source_symbol", sa.String(length=32)),
    sa.column("exchange", sa.String(length=16)),
    sa.column("asset_type", sa.String(length=16)),
    sa.column("frequency", sa.String(length=16)),
    sa.column("adjustment_policy", sa.String(length=32)),
    sa.column("source", sa.String(length=64)),
    sa.column("source_payload_fingerprint", sa.String(length=128)),
    sa.column("event_time", sa.DateTime(timezone=True)),
    sa.column("source_time", sa.DateTime(timezone=True)),
    sa.column("source_time_reason", sa.String(length=255)),
    sa.column("captured_at", sa.DateTime(timezone=True)),
    sa.column("ingested_at", sa.DateTime(timezone=True)),
    sa.column("available_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    existing_columns = _columns("ohlcv_bars")
    if "source_symbol" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("source_symbol", sa.String(length=32), nullable=True))
    if "exchange" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("exchange", sa.String(length=16), nullable=True))
    if "asset_type" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("asset_type", sa.String(length=16), nullable=True))
    if "frequency" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("frequency", sa.String(length=16), nullable=True))
    if "adjustment_policy" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("adjustment_policy", sa.String(length=32), nullable=True))
    if "source" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("source", sa.String(length=64), nullable=True))
    if "source_payload_fingerprint" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("source_payload_fingerprint", sa.String(length=128), nullable=True))
    if "event_time" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("event_time", sa.DateTime(timezone=True), nullable=True))
    if "source_time" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("source_time", sa.DateTime(timezone=True), nullable=True))
    if "source_time_reason" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("source_time_reason", sa.String(length=255), nullable=True))
    if "captured_at" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True))
    if "ingested_at" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True))
    if "available_at" not in existing_columns:
        op.add_column("ohlcv_bars", sa.Column("available_at", sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.select(ohlcv_bars.c.id, ohlcv_bars.c.symbol, ohlcv_bars.c.trade_date, ohlcv_bars.c.created_at, ohlcv_bars.c.updated_at)).fetchall()
    for row in rows:
        symbol = row.symbol or ""
        exchange = symbol.rsplit(".", 1)[-1] if "." in symbol else "UNKNOWN"
        captured_at = row.created_at or datetime.now(UTC)
        ingested_at = row.updated_at or captured_at
        bind.execute(
            ohlcv_bars.update()
            .where(ohlcv_bars.c.id == row.id)
            .values(
                source_symbol=symbol,
                exchange=exchange,
                asset_type="stock",
                frequency="1d",
                adjustment_policy="unadjusted",
                source=sa.func.coalesce(ohlcv_bars.c.source, "legacy_import"),
                source_time=None,
                source_time_reason="provider_time_unavailable",
                captured_at=captured_at,
                ingested_at=ingested_at,
                event_time=_trade_datetime(row.trade_date, 15),
                available_at=_trade_datetime(row.trade_date, 17),
            )
        )

    for column_name in (
        "source_symbol",
        "exchange",
        "asset_type",
        "frequency",
        "adjustment_policy",
        "source_time_reason",
        "captured_at",
        "ingested_at",
        "event_time",
        "available_at",
    ):
        op.alter_column("ohlcv_bars", column_name, nullable=False if column_name in {"source_symbol", "exchange", "asset_type", "frequency", "adjustment_policy", "source_time_reason", "captured_at", "ingested_at", "event_time", "available_at"} else True)

    existing_constraints = _unique_constraints("ohlcv_bars")
    if "uq_ohlcv_symbol_date" in existing_constraints:
        op.drop_constraint("uq_ohlcv_symbol_date", "ohlcv_bars", type_="unique")
    if "uq_ohlcv_identity_trade_date" not in existing_constraints:
        op.create_unique_constraint(
            "uq_ohlcv_identity_trade_date",
            "ohlcv_bars",
            ["symbol", "exchange", "asset_type", "frequency", "adjustment_policy", "trade_date"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT symbol, trade_date, COUNT(*) AS row_count
            FROM ohlcv_bars
            GROUP BY symbol, trade_date
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError("ohlcv_bars contains duplicate symbol/trade_date identities; Stage 5 downgrade would collapse canonical rows")

    existing_constraints = _unique_constraints("ohlcv_bars")
    if "uq_ohlcv_identity_trade_date" in existing_constraints:
        op.drop_constraint("uq_ohlcv_identity_trade_date", "ohlcv_bars", type_="unique")
    if "uq_ohlcv_symbol_date" not in existing_constraints:
        op.create_unique_constraint("uq_ohlcv_symbol_date", "ohlcv_bars", ["symbol", "trade_date"])

    for column_name in (
        "available_at",
        "ingested_at",
        "captured_at",
        "source_time_reason",
        "source_time",
        "event_time",
        "source_payload_fingerprint",
        "source",
        "adjustment_policy",
        "frequency",
        "asset_type",
        "exchange",
        "source_symbol",
    ):
        if column_name in _columns("ohlcv_bars"):
            op.drop_column("ohlcv_bars", column_name)
