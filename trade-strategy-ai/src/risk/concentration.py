"""单股集中度检查 (P4-009)"""

from src.risk.types import ConcentrationCheck, ConcentrationConfig, Position


def check_position_concentration(
    positions: list[Position],
    net_value: float,
    config: ConcentrationConfig,
) -> list[ConcentrationCheck]:
    """检查所有持仓的集中度

    Args:
        positions: 持仓列表
        net_value: 账户净值
        config: 集中度配置

    Returns:
        集中度检查结果列表
    """
    results = []
    for pos in positions:
        pct = pos.market_value / net_value
        passed = (
            pct <= config.max_single_position_pct
            and pos.market_value <= config.max_single_position_amount
        )
        results.append(ConcentrationCheck(
            symbol=pos.symbol,
            market_value=pos.market_value,
            net_value=net_value,
            concentration_pct=pct,
            passed=passed,
            limit=config.max_single_position_pct,
            trigger_condition=(
                f"单股 {pos.symbol} 集中度 {pct:.2%} 超过限制 {config.max_single_position_pct:.2%}"
                if not passed else ""
            ),
        ))
    return results