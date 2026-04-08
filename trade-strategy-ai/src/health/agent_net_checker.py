"""Agent 网络健康检查器。"""
from __future__ import annotations

from src.agent_net.agent_net import AgentNetwork
from src.agent_net.circuit_breaker import get_global_breaker_registry
from src.common.logger import get_logger
from src.health.models import ComponentCheck, HealthStatus

logger = get_logger("health.agent_net")


class AgentNetHealthChecker:
    """检查 Agent 网络注册状态和通道健康。"""

    name: str = "agent_net"

    async def check(self) -> ComponentCheck:
        """获取 Agent 网络状态。"""
        try:
            net = await AgentNetwork.get_instance()
            agents = net._agents
            channel = net._default_channel

            registered_count = len(agents)
            queue_depth = channel.qsize() if hasattr(channel, "qsize") else 0

            # 检查是否有任何熔断器处于 OPEN 状态
            registry = get_global_breaker_registry()
            open_circuits = [
                name for name, cb in registry._breakers.items()
                if cb.state.value == "open"
            ]

            status = HealthStatus.ERROR if open_circuits else HealthStatus.OK

            return ComponentCheck(
                name=self.name,
                status=status,
                details={
                    "registered_agents": registered_count,
                    "active_channels": len(net._channels),
                    "queue_depth": queue_depth,
                    "open_circuits": open_circuits,
                },
            )
        except Exception as e:
            logger.error("agent_net health check failed: %s", e)
            return ComponentCheck(
                name=self.name,
                status=HealthStatus.ERROR,
                error=str(e),
            )