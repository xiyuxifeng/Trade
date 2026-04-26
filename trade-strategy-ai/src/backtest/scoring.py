"""NTL-S6-003: 回测评分适配层

职责：
- 复用 Stage 5 评分口径（compute_mfe_mae_return），不复制公式
- 提供回测专用评分接口 score_backtest_trade
- 支持 A 股交易规则（涨跌停、T+1）
"""

from __future__ import annotations

from typing import Any

from src.evaluation.metrics_calculator import (
    TradeConstraint,
    compute_mfe_mae_return,
)


def score_backtest_trade(
    *,
    bars: list[dict[str, Any]],
    entry_price: float,
    entry_date: str,
    target_price: float | None = None,
    stop_loss_price: float | None = None,
    symbol: str = "",
    constraint: TradeConstraint | None = None,
) -> dict[str, Any]:
    """对单笔回测交易进行评分。

    复用 Stage 5 评分口径 `compute_mfe_mae_return`，只做接口适配，
    不复制或改写评分公式。

    Args:
        bars: ohlcv_1d 日线数据列表
        entry_price: 入场价格
        entry_date: 入场日期（YYYY-MM-DD）
        target_price: 止盈价（可选）
        stop_loss_price: 止损价（可选）
        symbol: 股票代码（用于推断板块类型和涨跌停幅度）
        constraint: 交易规则约束（可选，默认使用 A 股标准规则）

    Returns:
        包含 mfe/mae/return_pct/exit_triggered/exit_date/halted_dates/eval_date 的字典
    """
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = compute_mfe_mae_return(
        bars=bars,
        entry_price=entry_price,
        entry_date=entry_date,
        target_price=target_price,
        stop_loss_price=stop_loss_price,
        symbol=symbol,
        constraint=constraint,
    )
    return {
        "mfe": mfe,
        "mae": mae,
        "return_pct": return_pct,
        "exit_triggered": exit_triggered,
        "exit_date": exit_date,
        "halted_dates": halted_dates,
        "eval_date": eval_date,
    }
