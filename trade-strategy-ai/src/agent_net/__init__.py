"""Agent 网络模块。

提供多 Agent 协调的通信基础设施：
- 消息格式 (messages)
- 通道接口 (channels)
- Agent 网络 (agent_net)
- 重试策略 (retry)
- 熔断器 (circuit_breaker)

用法:
    from src.agent_net import AgentNetwork, AgentMessage, RetryPolicy

    net = await AgentNetwork.get_instance()
    await net.register_agent("agent_1")
    await net.send("agent_1", "agent_2", "hello", {"msg": "world"})
"""

from src.agent_net.messages import (
    AgentMessage,
    MessageType,
    ResponseStatus,
)

from src.agent_net.channels import (
    AgentChannel,
    InMemoryChannel,
)

from src.agent_net.agent_net import (
    AgentNetwork,
    get_agent_net,
    get_agent_net_sync,
)

from src.agent_net.retry import (
    RetryPolicy,
    RetryExhaustedError,
    BackoffStrategy,
    with_retry,
    retry_async,
    DEFAULT_RETRY_POLICY,
    QUICK_RETRY_POLICY,
    PERSISTENT_RETRY_POLICY,
)

from src.agent_net.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError,
    circuit_breaker,
    CircuitBreakerRegistry,
    get_global_breaker_registry,
)


__all__ = [
    # messages
    "AgentMessage",
    "MessageType",
    "ResponseStatus",
    # channels
    "AgentChannel",
    "InMemoryChannel",
    # agent_net
    "AgentNetwork",
    "get_agent_net",
    "get_agent_net_sync",
    # retry
    "RetryPolicy",
    "RetryExhaustedError",
    "BackoffStrategy",
    "with_retry",
    "retry_async",
    "DEFAULT_RETRY_POLICY",
    "QUICK_RETRY_POLICY",
    "PERSISTENT_RETRY_POLICY",
    # circuit_breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitOpenError",
    "circuit_breaker",
    "CircuitBreakerRegistry",
    "get_global_breaker_registry",
]
