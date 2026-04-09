"""止损计算 Skill"""
from typing import Any
from src.risk.types import StopLossLevel, StopLossMode

async def calculate_stop_loss(
    signal: Any,
    market_data: dict[str, Any],
    config: dict[str, Any]
) -> StopLossLevel:
    """
    计算止损水平

    Args:
        signal: 信号
        market_data: 市场数据
        config: 配置 {mode, level_pct}

    Returns:
        StopLossLevel
    """
    try:
        mode_str = config.get("mode", "fixed")
        # 转换字符串到 StopLossMode
        mode = StopLossMode(mode_str) if isinstance(mode_str, str) else mode_str
        level_pct = config.get("level_pct", 0.05)  # 默认 5%

        current_price = market_data.get("last_price", 0)
        if current_price <= 0:
            # 价格无效时返回 0.0，表示无法计算有效止损
            return StopLossLevel(
                mode=StopLossMode.FIXED,
                level=0.0,
                trigger_condition="invalid_price"
            )

        stop_price = current_price * (1 - level_pct)

        return StopLossLevel(
            mode=mode,
            level=stop_price,
            trigger_condition=f"price <= {stop_price}"
        )
    except Exception:
        # 降级：返回固定止损
        return StopLossLevel(
            mode=StopLossMode.FIXED,
            level=0.0,
            trigger_condition="error"
        )