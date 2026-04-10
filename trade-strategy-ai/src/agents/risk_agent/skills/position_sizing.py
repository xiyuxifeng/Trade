# src/agents/risk_agent/skills/position_sizing.py
"""头寸计算 Skill"""
from typing import Any
from src.strategy.types import PositionSize, PositionSizeType
from src.risk.types import AccountSnapshot

async def calculate_position_size(
    signal: Any,
    account: AccountSnapshot,
    config: dict[str, Any]
) -> PositionSize:
    """
    计算头寸大小

    Args:
        signal: 信号
        account: 账户快照
        config: 配置 {type, value, max_amount}

    Returns:
        PositionSize
    """
    try:
        size_type_str = config.get("type", "fixed_ratio")
        # 转换字符串到 PositionSizeType
        size_type = PositionSizeType(size_type_str) if isinstance(size_type_str, str) else size_type_str
        value = config.get("value", 0.1)  # 默认 10%
        max_amount = config.get("max_amount", 100000.0)

        # 根据账户净值计算头寸
        position_value = account.net_value * value

        # 不超过最大限制
        if position_value > max_amount:
            position_value = max_amount

        return PositionSize(
            type=size_type,
            value=value,
            max_amount=max_amount
        )
    except Exception:
        # 降级：返回默认头寸
        return PositionSize(
            type=PositionSizeType.FIXED_RATIO,
            value=0.1,
            max_amount=100000.0
        )