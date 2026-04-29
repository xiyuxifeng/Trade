"""B: Provider 失败告警规则（S7-007）。"""

from __future__ import annotations

from src.alerting.models import AlertEvent, AlertLevel


def fire_provider_failure_alert(
    manager,
    provider: str,
    capability: str,
    error: str,
    session=None,
) -> None:
    """Provider 调用失败时触发告警。

    Args:
        manager: AlertManager 实例
        provider: Provider 名称（kaipan / akshare）
        capability: 能力名称（hot_topics / topic_constituents / strong_symbols 等）
        error: 错误信息
        session: DB session（可选）
    """
    alert = AlertEvent(
        id=f"provider_failure_{provider}_{capability}",
        level=AlertLevel.WARNING,
        title=f"Provider 失败：{provider}.{capability}",
        message=f"Provider {provider} 调用 {capability} 失败：{error}",
        tags=["provider", provider],
        metadata={
            "rule_name": "provider_failure",
            "provider": provider,
            "capability": capability,
            "error": error,
        },
    )
    manager.fire_alert(alert, session=session)
