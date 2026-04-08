"""熔断器健康检查器。"""
from __future__ import annotations

from collections import Counter

from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus

logger = get_logger("health.circuit_breaker")


class CircuitBreakerHealthChecker:
    """检查全局熔断器状态分布。"""

    name: str = "circuit_breaker"

    async def check(self) -> ComponentCheck:
        """获取所有熔断器的状态。"""
        try:
            from src.agent_net.circuit_breaker import get_global_breaker_registry

            registry = get_global_breaker_registry()
            breakers = registry._breakers

            if not breakers:
                return ComponentCheck(
                    name=self.name,
                    status=HealthStatus.OK,
                    details={"total": 0, "states": {}},
                )

            states = {name: cb.state.value for name, cb in breakers.items()}
            state_counts = Counter(states.values())

            open_count = state_counts.get("open", 0)
            half_open_count = state_counts.get("half_open", 0)
            status = HealthStatus.ERROR if open_count > 0 else HealthStatus.WARNING if half_open_count > 0 else HealthStatus.OK

            return ComponentCheck(
                name=self.name,
                status=status,
                details={
                    "total": len(breakers),
                    "states": dict(state_counts),
                    "by_circuit": states,
                },
                error=f"{open_count} circuit(s) open" if open_count > 0 else None,
            )
        except Exception as e:
            logger.error("circuit_breaker health check failed: %s", e)
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.ERROR,
                error=str(e),
            )