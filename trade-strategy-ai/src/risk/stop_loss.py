"""止损设置 - P4-007"""
from __future__ import annotations

from dataclasses import dataclass

from src.risk.types import StopLossMode, StopLossLevel
from src.strategy.types import Signal


@dataclass
class StopLossConfig:
    """止损配置"""
    mode: StopLossMode = StopLossMode.VOLATILITY

    # 固定止损
    fixed_pct: float = 0.05  # 5%

    # 波动率止损
    atr_multiplier: float = 2.0
    atr_window: int = 14

    # 回撤止损
    drawdown_pct: float = 0.10

    # 时间止损
    max_hold_days: int = 10


class StopLossCalculator:
    """止损计算器

    支持四种止损模式:
    - FIXED: 固定止损（百分比）
    - VOLATILITY: 波动率止损（ATR）
    - TRAILING: 回撤止损
    - TIME: 时间止损
    """

    def __init__(self, config: StopLossConfig):
        self._config = config

    def calculate(
        self,
        entry_price: float,
        signal: Signal,
        market_data: dict,
    ) -> StopLossLevel | None:
        """计算止损

        Args:
            entry_price: 入场价格
            signal: 交易信号
            market_data: 市场数据（需包含 atr, close 等）

        Returns:
            StopLossLevel 止损级别，或 None（不需要止损）
        """
        from src.strategy.types import SignalSide

        if signal.side != SignalSide.BUY and signal.side != SignalSide.SELL:
            return None

        if self._config.mode == StopLossMode.FIXED:
            return self._calculate_fixed(entry_price)
        elif self._config.mode == StopLossMode.VOLATILITY:
            return self._calculate_volatility(entry_price, market_data)
        elif self._config.mode == StopLossMode.TRAILING:
            return self._calculate_trailing(entry_price, market_data)
        elif self._config.mode == StopLossMode.TIME:
            return self._calculate_time(entry_price, market_data)

        return None

    def _calculate_fixed(self, entry_price: float) -> StopLossLevel:
        """固定止损"""
        level = entry_price * (1 - self._config.fixed_pct)
        return StopLossLevel(
            mode=StopLossMode.FIXED,
            level=round(level, 2),
            trigger_condition=f"价格跌破 {self._config.fixed_pct * 100}%",
        )

    def _calculate_volatility(self, entry_price: float, market_data: dict) -> StopLossLevel:
        """波动率止损"""
        atr = market_data.get("atr", 0.0)
        if atr <= 0:
            # 无 ATR 数据时回退到固定止损
            return self._calculate_fixed(entry_price)

        level = entry_price - (atr * self._config.atr_multiplier)
        return StopLossLevel(
            mode=StopLossMode.VOLATILITY,
            level=round(level, 2),
            trigger_condition=f"价格跌破 入口-{self._config.atr_multiplier}*ATR",
        )

    def _calculate_trailing(self, entry_price: float, market_data: dict) -> StopLossLevel:
        """回撤止损"""
        high_price = market_data.get("high", entry_price)
        if high_price <= entry_price:
            high_price = entry_price

        level = high_price * (1 - self._config.drawdown_pct)
        return StopLossLevel(
            mode=StopLossMode.TRAILING,
            level=round(level, 2),
            trigger_condition=f"从高点回撤 {self._config.drawdown_pct * 100}%",
        )

    def _calculate_time(self, entry_price: float, market_data: dict) -> StopLossLevel:
        """时间止损"""
        return StopLossLevel(
            mode=StopLossMode.TIME,
            level=entry_price,  # 时间止损不设具体价格
            trigger_condition=f"持有超过 {self._config.max_hold_days} 天",
        )
