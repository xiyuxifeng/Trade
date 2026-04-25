"""Fix ranking_entries unique constraint to include trader_id.

Changes uq_ranking_entry from (trade_date, strategy_version_id, symbol)
to (trade_date, trader_id, strategy_version_id, symbol).

This ensures different traders don't conflict on Phase 0 entries
(which share strategy_version_id='').
"""

from __future__ import annotations

from alembic import op


revision = "2026_04_26_0001"
down_revision = "2026_04_25_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old constraint (trade_date, strategy_version_id, symbol)
    op.drop_constraint("uq_ranking_entry", "ranking_entries", type_="unique")
    # Create new constraint with trader_id added
    op.create_unique_constraint(
        "uq_ranking_entry",
        "ranking_entries",
        ["trade_date", "trader_id", "strategy_version_id", "symbol"],
    )


def downgrade() -> None:
    # Revert to old constraint
    op.drop_constraint("uq_ranking_entry", "ranking_entries", type_="unique")
    op.create_unique_constraint(
        "uq_ranking_entry",
        "ranking_entries",
        ["trade_date", "strategy_version_id", "symbol"],
    )
