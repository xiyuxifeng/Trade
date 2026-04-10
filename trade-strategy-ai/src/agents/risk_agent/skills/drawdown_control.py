# src/agents/risk_agent/skills/drawdown_control.py
"""回撤控制 Skill"""
from typing import Any
from src.risk.risk_monitor import RiskMonitor
from src.risk.types import AccountSnapshot

# RiskMonitor 实例（需要配置参数）
# 注意：实际使用时需要注入配置，这里简化处理
_risk_monitor = None  # 延迟初始化

def get_risk_monitor() -> RiskMonitor:
    global _risk_monitor
    if _risk_monitor is None:
        from src.risk.types import ConcentrationConfig, IndustryExposureConfig, PortfolioRiskConfig
        from src.alerting.models import AlertManager
        _risk_monitor = RiskMonitor(
            alert_manager=AlertManager(),
            concentration_config=ConcentrationConfig(),
            industry_config=IndustryExposureConfig(),
            portfolio_config=PortfolioRiskConfig(),
        )
    return _risk_monitor

async def drawdown_control(
    account: AccountSnapshot,
    signal: Any
) -> dict[str, Any]:
    """
    回撤控制检查

    Args:
        account: 账户快照
        signal: 信号

    Returns:
        {passed: bool, reason: str | None}
    """
    try:
        monitor = get_risk_monitor()
        alerts = monitor.check_and_alert(
            account=account,
            positions=account.positions,
            industry_map={},
            historical_returns=None
        )

        # 检查是否有回撤相关告警
        drawdown_alerts = [a for a in alerts if "drawdown" in a.title.lower() or "concentration" in a.title.lower()]
        if drawdown_alerts:
            return {
                "passed": False,
                "reason": drawdown_alerts[0].message
            }
        return {"passed": True, "reason": None}
    except Exception:
        # 降级：拒绝
        return {"passed": False, "reason": "drawdown check failed"}