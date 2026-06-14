"""Stage 2 metadata alignment for alert history and trade logs."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "2026_06_14_0002"
down_revision = "2026_06_03_0001"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _constraint_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    names = {item["name"] for item in inspector.get_unique_constraints(table_name) if item.get("name")}
    names.update(item["name"] for item in inspector.get_check_constraints(table_name) if item.get("name"))
    names.update(item["name"] for item in inspector.get_foreign_keys(table_name) if item.get("name"))
    return names


def _ensure_null_free(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    count = bind.execute(
        sa.text(f"SELECT count(*) FROM {table_name} WHERE {column_name} IS NULL")
    ).scalar_one()
    if count:
        raise RuntimeError(f"{table_name}.{column_name} contains NULL rows and cannot be tightened safely")


def upgrade() -> None:
    trade_log_columns = _column_names("trade_logs")
    trade_log_constraints = _constraint_names("trade_logs")

    for column_name in ("tags", "status", "aggregated_count"):
        _ensure_null_free("alert_history", column_name)
    op.alter_column("alert_history", "tags", existing_type=sa.JSON(), nullable=False)
    op.alter_column("alert_history", "status", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("alert_history", "aggregated_count", existing_type=sa.Integer(), nullable=False)

    if "source" not in trade_log_columns:
        op.add_column("trade_logs", sa.Column("source", sa.String(length=50), nullable=False, server_default=sa.text("'legacy'")))
    if "market" not in trade_log_columns:
        op.add_column("trade_logs", sa.Column("market", sa.String(length=32), nullable=False, server_default=sa.text("'CN'")))
    if "position_side" not in trade_log_columns:
        op.add_column("trade_logs", sa.Column("position_side", sa.String(length=10), nullable=False, server_default=sa.text("'long'")))
    if "order_type" not in trade_log_columns:
        op.add_column("trade_logs", sa.Column("order_type", sa.String(length=20), nullable=True))
    if "currency" not in trade_log_columns:
        op.add_column("trade_logs", sa.Column("currency", sa.String(length=8), nullable=False, server_default=sa.text("'CNY'")))
    if "strategy_tag" not in trade_log_columns:
        op.add_column("trade_logs", sa.Column("strategy_tag", sa.String(length=128), nullable=True))
    if "rationale" not in trade_log_columns:
        op.add_column("trade_logs", sa.Column("rationale", sa.Text(), nullable=True))

    for column_name, type_ in (
        ("account_id", sa.String(length=64)),
        ("side", sa.String(length=8)),
        ("fee", sa.Numeric(18, 6)),
    ):
        _ensure_null_free("trade_logs", column_name)
        op.alter_column("trade_logs", column_name, existing_type=type_, nullable=False)

    if "uq_trade_logs_external_id" not in trade_log_constraints:
        op.create_unique_constraint("uq_trade_logs_external_id", "trade_logs", ["external_id"])


def downgrade() -> None:
    bind = op.get_bind()
    trade_log_count = bind.execute(sa.text("SELECT count(*) FROM trade_logs")).scalar_one()
    if trade_log_count:
        raise RuntimeError("trade_logs contains rows; RT-S2-002 metadata downgrade requires empty canonical-aligned trade_logs")

    if "uq_trade_logs_external_id" in _constraint_names("trade_logs"):
        op.drop_constraint("uq_trade_logs_external_id", "trade_logs", type_="unique")

    for column_name in ("rationale", "strategy_tag", "currency", "order_type", "position_side", "market", "source"):
        if column_name in _column_names("trade_logs"):
            op.drop_column("trade_logs", column_name)

    op.alter_column("trade_logs", "fee", existing_type=sa.Numeric(18, 6), nullable=True)
    op.alter_column("trade_logs", "side", existing_type=sa.String(length=8), nullable=True)
    op.alter_column("trade_logs", "account_id", existing_type=sa.String(length=64), nullable=True)

    op.alter_column("alert_history", "aggregated_count", existing_type=sa.Integer(), nullable=True)
    op.alter_column("alert_history", "status", existing_type=sa.String(length=32), nullable=True)
    op.alter_column("alert_history", "tags", existing_type=sa.JSON(), nullable=True)
