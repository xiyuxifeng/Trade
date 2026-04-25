"""MFE / MAE / return_pct 计算器（NTL-S5-010）。

职责：
- 从 ohlcv_1d bars 计算持仓期间的 MFE（最大有利偏移）和 MAE（最大不利偏移）
- 计算入场到出场的收益率
- 判定止盈/止损触发
"""

from __future__ import annotations

from typing import Any


def _normalize_bar(bar: dict[str, Any]) -> dict[str, float]:
    """统一 bar 数据格式，兼容不同 key 命名（lowercase / uppercase）。"""
    return {
        "date": bar.get("date") or bar.get("Date") or "",
        "open": float(bar.get("open") or bar.get("Open") or 0),
        "high": float(bar.get("high") or bar.get("High") or 0),
        "low": float(bar.get("low") or bar.get("Low") or 0),
        "close": float(bar.get("close") or bar.get("Close") or 0),
    }


def _find_bar_index(bars: list[dict[str, Any]], target_date: str) -> int | None:
    """在 bars 中查找指定日期的 index，不存在则返回 None。"""
    for i, bar in enumerate(bars):
        normalized = _normalize_bar(bar)
        if normalized["date"] == target_date:
            return i
    return None


def _extract_rules_hit(signal_context_rules_snapshot: list[dict[str, Any]]) -> list[str]:
    """从 SignalContext.rules_snapshot 提取 rules_hit。

    当前简化实现：rules_snapshot 中的每条 rule 都视为参与了决策，
    将其 rule_id 收集为 rules_hit。
    后续可扩展：增加 matched=True 过滤，或从 Signal.triggered_rules 获取。
    """
    return [rule.get("rule_id") for rule in signal_context_rules_snapshot if rule.get("rule_id")]


def compute_mfe_mae_return(
    bars: list[dict[str, Any]],
    entry_price: float,
    entry_date: str,
    target_price: float | None = None,
    stop_loss_price: float | None = None,
) -> tuple[float, float, float, str | None, str | None]:
    """计算 MFE / MAE / return_pct。

    做多（buy）场景：
    - MFE = max(high_i) - entry_price（持仓期间最大盈利）
    - MAE = entry_price - min(low_i)（持仓期间最大亏损）

    exit 判定：从 entry_date bar 起遍历，遇到 high >= target_price
    则止盈触发（exit_triggered="target"）；遇到 low <= stop_loss_price
    则止损触发（exit_triggered="stop_loss"）。未触发则用最后 bar close。

    Args:
        bars: ohlcv_1d 日线数据 list
        entry_price: 入场价格（元）
        entry_date: 入场日期（YYYY-MM-DD）
        target_price: 止盈价（可选）
        stop_loss_price: 止损价（可选）

    Returns:
        (mfe, mae, return_pct, exit_triggered, exit_date)
        exit_triggered: "target" | "stop_loss" | None
        exit_date: 触发 exit 的日期或 None
    """
    if not bars or entry_price <= 0:
        return (0.0, 0.0, 0.0, None, None)

    # 找 entry bar index
    entry_idx = _find_bar_index(bars, entry_date)
    if entry_idx is None:
        # entry_date 不在 bars 中，从第一条开始（保守处理）
        entry_idx = 0

    mfe = 0.0
    mae = 0.0
    exit_triggered: str | None = None
    exit_date: str | None = None
    exit_price = entry_price  # 默认用 entry_price

    for i in range(entry_idx, len(bars)):
        bar = _normalize_bar(bars[i])
        high = bar["high"]
        low = bar["low"]
        close = bar["close"]
        bar_date = bar["date"]

        # 累计 MFE / MAE
        mfe = max(mfe, high - entry_price)
        mae = max(mae, entry_price - low)

        # 检查止盈
        if target_price is not None and high >= target_price:
            exit_triggered = "target"
            exit_price = close
            exit_date = bar_date
            break

        # 检查止损
        if stop_loss_price is not None and low <= stop_loss_price:
            exit_triggered = "stop_loss"
            exit_price = close
            exit_date = bar_date
            break

        # 未触发：持续更新 exit_price 为当前 bar close（仍持仓）
        exit_price = close
        exit_date = bar_date

    # 计算收益率
    return_pct = (exit_price / entry_price - 1) * 100

    return (mfe, mae, return_pct, exit_triggered, exit_date)
