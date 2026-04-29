"""add ohlcv_bars and indicators tables

Revision ID: 2026_04_29_0001
Revises: 2026_04_26_0001
Create Date: 2026-04-29
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_04_29_0001"
down_revision: Union[str, None] = "2026_04_26_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 ohlcv_bars 表
    op.create_table(
        "ohlcv_bars",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("turnover", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "trade_date", name="uq_ohlcv_symbol_date"),
    )
    op.create_index("ix_ohlcv_symbol", "ohlcv_bars", ["symbol"], unique=False)
    op.create_index("ix_ohlcv_trade_date", "ohlcv_bars", ["trade_date"], unique=False)

    # 创建 indicators 表
    op.create_table(
        "indicators",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("rsi", sa.Float(), nullable=True),
        sa.Column("macd_histogram", sa.Float(), nullable=True),
        sa.Column("bb_width", sa.Float(), nullable=True),
        sa.Column("cci", sa.Float(), nullable=True),
        sa.Column("ma50", sa.Float(), nullable=True),
        sa.Column("ma200", sa.Float(), nullable=True),
        sa.Column("stoch_k", sa.Float(), nullable=True),
        sa.Column("volume_ratio", sa.Float(), nullable=True),
        sa.Column("price_vs_ma", sa.Float(), nullable=True),
        sa.Column("atr_ratio", sa.Float(), nullable=True),
        sa.Column("close_position", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "trade_date", name="uq_indicator_symbol_date"),
    )
    op.create_index("ix_indicator_symbol", "indicators", ["symbol"], unique=False)
    op.create_index("ix_indicator_trade_date", "indicators", ["trade_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_indicator_trade_date", table_name="indicators")
    op.drop_index("ix_indicator_symbol", table_name="indicators")
    op.drop_table("indicators")
    op.drop_index("ix_ohlcv_trade_date", table_name="ohlcv_bars")
    op.drop_index("ix_ohlcv_symbol", table_name="ohlcv_bars")
    op.drop_table("ohlcv_bars")
