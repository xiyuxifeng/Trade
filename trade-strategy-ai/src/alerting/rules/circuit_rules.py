"""F: Circuit Breaker 跳闸告警规则（S7-007）。"""

from __future__ import annotations

from src.alerting.models import AlertEvent, AlertLevel


def fire_circuit_breaker_open_alert(
    manager,
    provider: str,
    capability: str,
    session=None,
) -> None:
    """Circuit Breaker 跳闸时触发告警。

    Args:
        manager: AlertManager 实例
        provider: Provider 名称
        capability: 能力名称
        session: DB session（可选）
    """
    alert = AlertEvent(
        id=f"circuit_breaker_{provider}_{capability}",
        level=AlertLevel.WARNING,
        title=f"Circuit Breaker 跳闸：{provider}.{capability}",
        message=f"Provider {provider} 的 {capability} 熔断器已跳闸，请求进入降级模式。",
        tags=["circuit_breaker", "open", provider],
        metadata={
            "rule_name": "circuit_breaker_open",
            "provider": provider,
            "capability": capability,
        },
    )
    manager.fire_alert(alert, session=session)
