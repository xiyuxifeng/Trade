"""总体风险敞口评估 (P4-011)"""

from __future__ import annotations

import numpy as np
from src.risk.types import (
    AccountSnapshot,
    PortfolioRiskAssessment,
    PortfolioRiskConfig,
    PortfolioRiskMetrics,
    Position,
    RiskLevel,
)


def classify_risk_level(
    var_pct: float,
    volatility: float,
    leverage: float,
) -> RiskLevel:
    """分类风险等级

    Args:
        var_pct: VaR 占净值比例
        volatility: 波动率
        leverage: 杠杆率

    Returns:
        风险等级
    """
    if var_pct >= 0.15 or volatility >= 0.35 or leverage >= 1.2:
        return RiskLevel.CRITICAL
    elif var_pct >= 0.08 or volatility >= 0.20 or leverage >= 0.9:
        return RiskLevel.HIGH
    elif var_pct >= 0.03 or volatility >= 0.10 or leverage >= 0.6:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def calculate_var(
    positions: list[Position],
    returns: np.ndarray,
    confidence: float = 0.95,
    window: int = 20,
) -> float:
    """计算 Value at Risk

    基于历史收益率分布的分位数计算 VaR

    Args:
        positions: 持仓列表（用于计算总敞口）
        returns: 历史收益率数组
        confidence: 置信度
        window: 计算窗口

    Returns:
        VaR 金额
    """
    if len(returns) < window:
        return 0.0

    recent_returns = returns[-window:]
    var_pct = abs(np.percentile(recent_returns, (1 - confidence) * 100))

    # 计算总敞口
    total_exposure = sum(p.market_value for p in positions)
    return total_exposure * var_pct


def estimate_portfolio_volatility(
    positions: list[Position],
    returns: np.ndarray | None,
) -> float:
    """估算组合波动率

    Args:
        positions: 持仓列表
        returns: 历史收益率数组

    Returns:
        波动率（标准差）
    """
    if returns is None or len(returns) < 2:
        # 如果没有历史数据，使用持仓数量的倒数作为简化估计
        return 1.0 / max(len(positions), 1) if positions else 0.0
    return float(np.std(returns))


def assess_portfolio_risk(
    positions: list[Position],
    account: AccountSnapshot,
    historical_returns: np.ndarray | None,
    config: PortfolioRiskConfig,
) -> PortfolioRiskAssessment:
    """评估总体风险敞口

    Args:
        positions: 持仓列表
        account: 账户快照
        historical_returns: 历史收益率数组（可选）
        config: 组合风险配置

    Returns:
        组合风险评估结果
    """
    # 计算基础指标
    total_exposure = sum(p.market_value for p in positions)
    leverage = total_exposure / account.net_value if account.net_value > 0 else 0

    # 计算 VaR
    var = 0.0
    var_pct = 0.0
    if historical_returns is not None and len(historical_returns) > 0:
        var = calculate_var(positions, historical_returns, config.var_confidence, config.var_window)
        var_pct = var / account.net_value if account.net_value > 0 else 0

    # 估算波动率
    volatility = estimate_portfolio_volatility(positions, historical_returns)

    # 构建指标
    metrics = PortfolioRiskMetrics(
        var=var,
        var_pct=var_pct,
        volatility=volatility,
        leverage=leverage,
        net_value=account.net_value,
        total_exposure=total_exposure,
        positions_count=len(positions),
        risk_level=classify_risk_level(var_pct, volatility, leverage),
    )

    # 检查限制
    violations = []
    if var_pct > config.max_var_pct:
        violations.append(f"VaR {var_pct:.2%} 超过限制 {config.max_var_pct:.2%}")
    if volatility > config.max_volatility:
        violations.append(f"波动率 {volatility:.2%} 超过限制 {config.max_volatility:.2%}")
    if leverage > config.max_leverage:
        violations.append(f"杠杆率 {leverage:.2%} 超过限制 {config.max_leverage:.2%}")

    return PortfolioRiskAssessment(
        metrics=metrics,
        var_limit=config.max_var_pct,
        volatility_limit=config.max_volatility,
        leverage_limit=config.max_leverage,
        passed=len(violations) == 0,
        violations=violations,
    )