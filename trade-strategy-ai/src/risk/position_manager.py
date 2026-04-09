"""头寸管理 - P4-006"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.risk.types import PositionSizeType
from src.strategy.types import Signal, SignalSide, PositionSize
from src.risk.types import AccountSnapshot
from src.shared.exceptions import PositionLimitExceeded

# 兼容性别名（供 __init__.py 使用）
PositionSizeMode = PositionSizeType


@dataclass
class PositionConfig:
    """头寸配置"""
    # 固定金额模式
    fixed_amount: float = 10_000.0

    # 固定比例模式
    fixed_ratio_pct: float = 0.05  # 5%

    # 波动率调整模式
    target_volatility: float = 0.15
    vol_window: int = 20

    # 通用限制
    max_position_pct: float = 0.20  # 最大占总净值比例
    max_single_position: float = 50_000.0  # 最大单标的金额


class PositionManager:
    """头寸管理器

    根据账户净值、风险偏好计算持仓数量。
    """

    def __init__(
        self,
        mode: PositionSizeType = PositionSizeType.FIXED_RATIO,
        config: PositionConfig | None = None,
    ):
        self._mode = mode
        self._config = config or PositionConfig()

    def calculate_size(
        self,
        signal: Signal,
        account: AccountSnapshot,
        market_data: dict,
    ) -> PositionSize:
        """计算头寸

        Args:
            signal: 交易信号
            account: 账户快照
            market_data: 市场数据（需包含 close）

        Returns:
            PositionSize 头寸规格

        Raises:
            PositionLimitExceeded: 头寸超限时抛出
        """
        # HOLD 信号返回零头寸
        if signal.side == SignalSide.HOLD:
            return PositionSize(type=self._mode, value=0.0)

        price = market_data.get("close", 0.0)
        if price <= 0:
            return PositionSize(type=self._mode, value=0.0)

        # 根据模式计算
        if self._mode == PositionSizeType.FIXED_AMOUNT:
            raw_value = self._config.fixed_amount
        elif self._mode == PositionSizeType.VOLATILITY_ADJUSTED:
            raw_value = self._calculate_volatility_adjusted(account, market_data)
        else:  # FIXED_RATIO
            raw_value = account.net_value * self._config.fixed_ratio_pct

        # 应用限制
        max_by_pct = account.net_value * self._config.max_position_pct
        max_value = min(raw_value, max_by_pct, self._config.max_single_position)

        # 计算股数
        shares = math.floor(max_value / price)

        return PositionSize(
            type=self._mode,
            value=float(shares),
            max_amount=max_value,
        )

    def _calculate_volatility_adjusted(
        self,
        account: AccountSnapshot,
        market_data: dict,
    ) -> float:
        """波动率调整计算"""
        atr = market_data.get("atr", 0.0)
        price = market_data.get("close", 0.0)

        if atr <= 0 or price <= 0:
            return account.net_value * self._config.fixed_ratio_pct

        # 波动率调整：目标波动率 / ATR比率 * 账户净值
        atr_ratio = atr / price
        if atr_ratio <= 0:
            return account.net_value * self._config.fixed_ratio_pct

        adjusted_value = (self._config.target_volatility / atr_ratio) * account.net_value

        # 限制在合理范围
        return min(adjusted_value, account.net_value * self._config.max_position_pct)