"""Add trade_logs composite unique constraint.

The composite key (account_id, symbol, executed_at, quantity, price) prevents
duplicate trade records from being inserted even if external_id is NULL.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260407_001"
down_revision = "20260406_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_trade_logs_composite_key",
        "trade_logs",
        ["account_id", "symbol", "executed_at", "quantity", "price"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_trade_logs_composite_key", "trade_logs", type_="unique")
