"""止盈策略 - P4-008"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.risk.types import TakeProfitMode, TakeProfitLevel, ScalingLevel
from src.strategy.types import Signal


class TakeProfitCalculator:
    """止盈计算器

    支持四种止盈模式:
    - FIXED: 固定止盈
    - SCALING: 分批止盈
    - TRAILING: 移动止损
    - TIME: 时间止盈
    """

    def __init__(self, config: TakeProfitConfig | None = None):
        self._config = config or TakeProfitConfig()

    def calculate(
        self,
        entry_price: float,
        signal: Signal,
        market_data: dict,
    ) -> list[TakeProfitLevel]:
        """计算止盈

        Args:
            entry_price: 入场价格
            signal: 交易信号
            market_data: 市场数据

        Returns:
            TakeProfitLevel 列表（可能多个级别）
        """
        from src.strategy.types import SignalSide

        if signal.side not in (SignalSide.BUY, SignalSide.SELL):
            return []

        if self._config.mode == TakeProfitMode.FIXED:
            return [self._calculate_fixed(entry_price)]
        elif self._config.mode == TakeProfitMode.SCALING:
            return self._calculate_scaling(entry_price)
        elif self._config.mode == TakeProfitMode.TRAILING:
            return [self._calculate_trailing(entry_price, market_data)]
        elif self._config.mode == TakeProfitMode.TIME:
            return [self._calculate_time(entry_price)]

        return []

    def _calculate_fixed(self, entry_price: float) -> TakeProfitLevel:
        """固定止盈"""
        level = entry_price * (1 + self._config.fixed_pct)
        return TakeProfitLevel(
            mode=TakeProfitMode.FIXED,
            level=round(level, 2),
            close_pct=1.0,  # 全卖
            trigger_condition=f"价格上涨 {self._config.fixed_pct * 100}%",
        )

    def _calculate_scaling(self, entry_price: float) -> list[TakeProfitLevel]:
        """分批止盈"""
        levels = []
        for scaling in self._config.scaling_levels:
            target_price = entry_price * (1 + scaling.target_pct)
            levels.append(TakeProfitLevel(
                mode=TakeProfitMode.SCALING,
                level=round(target_price, 2),
                close_pct=scaling.close_pct,
                trigger_condition=f"价格上涨 {scaling.target_pct * 100}%，卖出 {scaling.close_pct * 100}%",
            ))
        return levels

    def _calculate_trailing(self, entry_price: float, market_data: dict) -> TakeProfitLevel:
        """移动止损止盈"""
        high_price = market_data.get("high", entry_price)
        if high_price <= entry_price:
            high_price = entry_price

        level = high_price * (1 - self._config.trailing_pct)
        return TakeProfitLevel(
            mode=TakeProfitMode.TRAILING,
            level=round(level, 2),
            close_pct=1.0,
            trigger_condition=f"从高点回撤 {self._config.trailing_pct * 100}%",
        )

    def _calculate_time(self, entry_price: float) -> TakeProfitLevel:
        """时间止盈"""
        return TakeProfitLevel(
            mode=TakeProfitMode.TIME,
            level=entry_price,  # 时间止盈不设具体价格
            close_pct=1.0,
            trigger_condition=f"持有 {self._config.target_hold_days} 天后止盈",
        )