"""行业敞口控制 (P4-010)"""

from src.risk.types import (
    IndustryExposureCheck,
    IndustryExposureConfig,
    IndustryExposureResult,
    Position,
)


def check_industry_exposure(
    positions: list[Position],
    industry_map: dict[str, tuple[str, str]],  # symbol -> (一级代码, 一级名称)
    net_value: float,
    config: IndustryExposureConfig,
) -> IndustryExposureResult:
    """检查行业敞口

    Args:
        positions: 持仓列表
        industry_map: 股票行业映射
        net_value: 账户净值
        config: 行业敞口配置

    Returns:
        行业敞口检查结果
    """
    # 按行业聚合市值
    sector_values: dict[str, float] = {}
    sector_names: dict[str, str] = {}
    sector_positions: dict[str, list[str]] = {}

    for pos in positions:
        if pos.symbol in industry_map:
            sector_code, sector_name = industry_map[pos.symbol]
            sector_values[sector_code] = sector_values.get(sector_code, 0) + pos.market_value
            sector_names[sector_code] = sector_name
            sector_positions.setdefault(sector_code, []).append(pos.symbol)

    # 计算各行业占比并检查
    checks = []
    for sector_code, market_value in sector_values.items():
        pct = market_value / net_value
        limit = config.max_sector_pct
        passed = pct <= limit
        sector_name = sector_names.get(sector_code, sector_code)
        checks.append(IndustryExposureCheck(
            sector_code=sector_code,
            sector_name=sector_name,
            exposure_pct=pct,
            passed=passed,
            limit=limit,
        ))

    return IndustryExposureResult(
        total_exposure=sum(sector_values.values()),
        checks=checks,
        industry_map=industry_map,
    )


def get_sw_industry(symbol: str) -> tuple[str, str] | None:
    """获取申万行业分类（通过 AKShare）

    Args:
        symbol: 股票代码，如 "000001.SZ"

    Returns:
        (一级行业代码, 一级行业名称) 或 None
    """
    try:
        import akshare as ak

        # 转换代码格式：000001.SZ -> 000001
        code = symbol.split(".")[0]

        # 获取行业成分股
        df = ak.stock_board_industry_cons_em(symbol=code)
        if df is not None and len(df) > 0:
            # 获取行业名称
            industry_name = df.iloc[0].get("板块名称", "")
            # 这里需要另一个接口获取一级行业代码
            # 简化处理：使用板块名称作为行业标识
            return (code, industry_name)
        return None
    except Exception:
        return None