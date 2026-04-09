"""风险监控与告警 (P4-012)"""

from __future__ import annotations

from typing import Any
import numpy as np

from src.alerting.models import AlertEvent, AlertLevel
from src.risk.concentration import check_position_concentration
from src.risk.industry_exposure import check_industry_exposure
from src.risk.portfolio_risk import assess_portfolio_risk
from src.risk.types import (
    AccountSnapshot,
    ConcentrationConfig,
    IndustryExposureConfig,
    PortfolioRiskConfig,
    Position,
)


def _create_alert(
    level: AlertLevel,
    title: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> AlertEvent:
    """创建告警事件"""
    return AlertEvent(
        level=level,
        title=title,
        message=message,
        source="RiskMonitor",
        metadata=metadata or {},
    )


class RiskMonitor:
    """风险监控器

    集成所有风控检查，触发告警
    """

    def __init__(
        self,
        alert_manager: Any,  # AlertManager (not used for sending, kept for interface compatibility)
        concentration_config: ConcentrationConfig,
        industry_config: IndustryExposureConfig,
        portfolio_config: PortfolioRiskConfig,
    ):
        """初始化风险监控器

        Args:
            alert_manager: 告警管理器（保留参数，暂不使用）
            concentration_config: 集中度配置
            industry_config: 行业敞口配置
            portfolio_config: 组合风险配置
        """
        self._alert_manager = alert_manager
        self._concentration = concentration_config
        self._industry = industry_config
        self._portfolio = portfolio_config

    def check_and_alert(
        self,
        account: AccountSnapshot,
        positions: list[Position],
        industry_map: dict[str, tuple[str, str]],
        historical_returns: np.ndarray | None = None,
    ) -> list[AlertEvent]:
        """执行所有风控检查并发送告警

        Args:
            account: 账户快照
            positions: 持仓列表
            industry_map: 股票行业映射
            historical_returns: 历史收益率数组（可选）

        Returns:
            触发的告警列表
        """
        alerts: list[AlertEvent] = []

        # 1. 单股集中度检查
        concentration_results = check_position_concentration(
            positions, account.net_value, self._concentration
        )
        for check in concentration_results:
            if not check.passed:
                alert = _create_alert(
                    level=AlertLevel.WARNING,
                    title=f"单股集中度超限: {check.symbol}",
                    message=check.trigger_condition,
                    metadata={"symbol": check.symbol, "concentration_pct": check.concentration_pct},
                )
                alerts.append(alert)

        # 2. 行业敞口检查
        industry_result = check_industry_exposure(
            positions, industry_map, account.net_value, self._industry
        )
        for check in industry_result.checks:
            if not check.passed:
                alert = _create_alert(
                    level=AlertLevel.WARNING,
                    title=f"行业敞口超限: {check.sector_name}",
                    message=f"{check.sector_name} 敞口 {check.exposure_pct:.2%} 超过限制 {check.limit:.2%}",
                    metadata={"sector_code": check.sector_code, "exposure_pct": check.exposure_pct},
                )
                alerts.append(alert)

        # 3. 总体风险评估
        risk_assessment = assess_portfolio_risk(
            positions, account, historical_returns, self._portfolio
        )
        if not risk_assessment.passed:
            for violation in risk_assessment.violations:
                alert = _create_alert(
                    level=AlertLevel.CRITICAL,
                    title="组合风险超限",
                    message=violation,
                    metadata={"metrics": risk_assessment.metrics.__dict__},
                )
                alerts.append(alert)

        return alerts