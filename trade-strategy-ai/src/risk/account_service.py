"""账户快照服务 - 从真实 TradeLog 构建 AccountSnapshot

替换 ManagerAgent.evaluate_signal() 中的硬编码模拟账户，
让交易记录真正影响风控决策。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.models.ohlcv_bar import OHLCVBar
from src.models.trade_log import TradeLog
from src.risk.types import AccountSnapshot, Position

logger = get_logger(__name__)

# 默认初始资金（可在 config 中覆盖）
DEFAULT_INITIAL_CASH = 100000.0


async def build_account_snapshot(
    *,
    session: AsyncSession,
    account_id: str,
    initial_cash: float = DEFAULT_INITIAL_CASH,
    as_of: datetime | None = None,
) -> AccountSnapshot:
    """从 TradeLog 构建真实的 AccountSnapshot。

    流程：
    1. 查询该账户的所有交易记录（截至 as_of）
    2. 按 symbol 聚合买卖，计算当前持仓
    3. 从 OHLCV 获取最新价格估算市值
    4. 计算现金 = 初始资金 - 买入总额 + 卖出总额
    5. 计算 PnL

    Args:
        session: 数据库会话
        account_id: 账户 ID
        initial_cash: 初始资金（默认 100,000）
        as_of: 截止时间（None 表示当前时间）

    Returns:
        AccountSnapshot
    """
    now = as_of or datetime.now(timezone.utc)

    # 1. 查询交易记录
    stmt = (
        select(TradeLog)
        .where(TradeLog.account_id == account_id)
        .order_by(TradeLog.executed_at.asc())
    )
    if as_of:
        stmt = stmt.where(TradeLog.executed_at <= as_of)

    result = await session.execute(stmt)
    trades = result.scalars().all()

    if not trades:
        logger.debug("账户无交易记录: account_id=%s, 返回空账户", account_id)
        return AccountSnapshot(
            account_id=account_id,
            timestamp=now,
            net_value=initial_cash,
            cash=initial_cash,
            total_position_value=0.0,
            positions=[],
            daily_pnl=0.0,
            total_pnl=0.0,
        )

    # 2. 按 symbol 聚合买卖，计算持仓
    positions_raw: dict[str, dict] = {}
    cash_flow = 0.0  # 累计资金流出（买入为正，卖出为负）

    for trade in trades:
        if trade.symbol not in positions_raw:
            positions_raw[trade.symbol] = {
                "quantity": 0.0,
                "total_cost": 0.0,
                "total_buy_qty": 0.0,
            }
        pos = positions_raw[trade.symbol]

        qty = float(trade.quantity)
        price = float(trade.price)
        amount = float(trade.amount)

        if trade.side == "buy":
            pos["quantity"] += qty
            pos["total_cost"] += amount
            pos["total_buy_qty"] += qty
            cash_flow += amount
        elif trade.side == "sell":
            pos["quantity"] -= qty
            # 按比例减少成本
            if pos["total_buy_qty"] > 0:
                sell_ratio = qty / pos["total_buy_qty"]
                pos["total_cost"] -= pos["total_cost"] * sell_ratio
                pos["total_buy_qty"] -= qty
            cash_flow -= amount

    # 过滤零持仓
    active_positions = {
        sym: p for sym, p in positions_raw.items()
        if abs(p["quantity"]) > 1e-8
    }

    # 3. 获取最新价格（从 OHLCV 取最近交易日收盘价）
    symbols = list(active_positions.keys())
    latest_prices: dict[str, float] = {}
    if symbols:
        latest_prices = await _get_latest_prices(session, symbols)

    # 4. 构建 Position 列表
    positions: list[Position] = []
    total_market_value = 0.0
    total_unrealized_pnl = 0.0

    for symbol, pos in active_positions.items():
        qty = pos["quantity"]
        avg_cost = pos["total_cost"] / qty if qty > 0 else 0.0
        current_price = latest_prices.get(symbol, avg_cost)
        market_value = qty * current_price
        unrealized_pnl = market_value - pos["total_cost"]
        unrealized_pnl_pct = (unrealized_pnl / pos["total_cost"] * 100) if pos["total_cost"] > 0 else 0.0

        total_market_value += market_value
        total_unrealized_pnl += unrealized_pnl

        positions.append(Position(
            symbol=symbol,
            quantity=qty,
            avg_cost=avg_cost,
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
        ))

    # 5. 计算账户汇总
    cash = initial_cash - cash_flow
    total_position_value = total_market_value
    net_value = cash + total_position_value
    total_pnl = net_value - initial_cash

    snapshot = AccountSnapshot(
        account_id=account_id,
        timestamp=now,
        net_value=net_value,
        cash=cash,
        total_position_value=total_position_value,
        positions=positions,
        daily_pnl=0.0,  # 日 PnL 需要两个快照对比，单次查询无法获得
        total_pnl=total_pnl,
    )
    logger.info(
        "账户快照构建完成: account=%s, net_value=%.2f, cash=%.2f, positions=%d, total_pnl=%.2f",
        account_id, net_value, cash, len(positions), total_pnl,
    )
    return snapshot


async def _get_latest_prices(
    session: AsyncSession,
    symbols: list[str],
) -> dict[str, float]:
    """获取各标的的最新收盘价。

    从 ohlcv_bars 表取每个 symbol 最近交易日的 close 价格。
    """
    if not symbols:
        return {}

    # 子查询：每个 symbol 的最新 trade_date
    latest_dates = (
        select(
            OHLCVBar.symbol,
            func.max(OHLCVBar.trade_date).label("max_date"),
        )
        .where(OHLCVBar.symbol.in_(symbols))
        .group_by(OHLCVBar.symbol)
        .subquery()
    )

    stmt = (
        select(OHLCVBar.symbol, OHLCVBar.close)
        .join(
            latest_dates,
            (OHLCVBar.symbol == latest_dates.c.symbol)
            & (OHLCVBar.trade_date == latest_dates.c.max_date),
        )
    )

    try:
        result = await session.execute(stmt)
        rows = result.all()
        return {row.symbol: float(row.close) for row in rows if row.close}
    except Exception as e:
        logger.exception("获取最新价格失败: 使用成本价估算, error=%s", e)
        return {}
