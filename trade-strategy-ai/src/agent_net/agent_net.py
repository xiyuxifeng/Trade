"""Agent 网络单例。

提供全局 Agent 通信管理：
- AgentNetwork: 单例，管理所有 Agent 的通信
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from src.common.logger import get_logger
from src.agent_net.channels import AgentChannel, InMemoryChannel
from src.agent_net.messages import AgentMessage, MessageType, ResponseStatus


logger = get_logger("agent_net")


class AgentNetwork:
    """全局 Agent 网络单例。

    管理 Agent 间的消息传递，提供：
    - Agent 注册
    - 点对点消息发送
    - 请求/响应模式
    - 发布/订阅模式
    """

    _instance: "AgentNetwork | None" = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        """初始化 Agent 网络（请使用 get_instance()）。"""
        self._channels: dict[str, AgentChannel] = {}
        self._default_channel: InMemoryChannel = InMemoryChannel()
        self._agents: dict[str, set[str]] = {}  # agent_id -> set of subscribed channels
        self._pending_responses: dict[str, asyncio.Future[AgentMessage]] = {}
        self._response_timeout: float = 30.0  # seconds
        self._closed = False

    @classmethod
    async def get_instance(cls) -> "AgentNetwork":
        """获取 AgentNetwork 单例（异步安全）。"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def get_instance_sync(cls) -> "AgentNetwork":
        """同步获取 AgentNetwork 单例（仅在事件循环外使用）。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def register_agent(
        self,
        agent_id: str,
        channel: AgentChannel | None = None,
    ) -> None:
        """注册一个 Agent。

        Args:
            agent_id: Agent 唯一标识
            channel: Agent 专属通道，None 则使用默认通道
        """
        if agent_id in self._agents:
            logger.warning("agent %s already registered", agent_id)
            return

        ch = channel or self._default_channel
        await ch.subscribe(agent_id, self._create_handler(agent_id))
        self._agents[agent_id] = {id(ch)}
        logger.info("agent %s registered", agent_id)

    async def unregister_agent(self, agent_id: str) -> None:
        """注销一个 Agent。

        Args:
            agent_id: Agent 唯一标识
        """
        if agent_id not in self._agents:
            return

        for ch_id in self._agents[agent_id]:
            if ch_id in self._channels:
                ch = self._channels[ch_id]
                await ch.unsubscribe(agent_id)

        del self._agents[agent_id]
        logger.info("agent %s unregistered", agent_id)

    def _create_handler(self, agent_id: str) -> Callable[[AgentMessage], Awaitable[None]]:
        """创建 Agent 的消息处理器。"""
        async def handle(message: AgentMessage) -> None:
            logger.debug(
                "message received: agent=%s msg_id=%s type=%s sender=%s",
                agent_id,
                message.id,
                message.type.value,
                message.sender,
            )

            # 如果是响应消息且有待处理的请求
            if message.is_response() and message.correlation_id:
                future = self._pending_responses.pop(message.correlation_id, None)
                if future and not future.done():
                    future.set_result(message)
                    return

            # 其他消息类型由 Agent 自己处理（通过子类化或回调）
            # 这里暂时不做处理，留给后续扩展

        return handle

    async def send(
        self,
        sender: str,
        recipient: str,
        subject: str,
        payload: dict[str, Any] | None = None,
        channel_name: str | None = None,
    ) -> None:
        """发送消息（单向）。

        Args:
            sender: 发送方 ID
            recipient: 接收方 ID
            subject: 消息主题
            payload: 消息内容
            channel_name: 指定通道名称
        """
        if self._closed:
            raise RuntimeError("AgentNetwork is closed")

        message = AgentMessage(
            type=MessageType.MESSAGE,
            sender=sender,
            recipient=recipient,
            subject=subject,
            payload=payload or {},
        )

        channel = self._get_channel(channel_name)
        await channel.send(message)

        logger.debug(
            "message sent: sender=%s recipient=%s subject=%s",
            sender,
            recipient,
            subject,
        )

    async def request(
        self,
        sender: str,
        recipient: str,
        subject: str,
        payload: dict[str, Any] | None = None,
        timeout: float | None = None,
        channel_name: str | None = None,
    ) -> AgentMessage:
        """发送请求并等待响应。

        Args:
            sender: 发送方 ID
            recipient: 接收方 ID
            subject: 消息主题
            payload: 消息内容
            timeout: 超时时间（秒），None 使用默认超时
            channel_name: 指定通道名称

        Returns:
            响应消息

        Raises:
            asyncio.TimeoutError: 请求超时
            RuntimeError: AgentNetwork 已关闭
        """
        if self._closed:
            raise RuntimeError("AgentNetwork is closed")

        message = AgentMessage(
            type=MessageType.REQUEST,
            sender=sender,
            recipient=recipient,
            subject=subject,
            payload=payload or {},
        )

        # 创建 Future 等待响应
        future: asyncio.Future[AgentMessage] = asyncio.get_event_loop().create_future()
        self._pending_responses[message.id] = future

        channel = self._get_channel(channel_name)
        await channel.send(message)

        logger.debug(
            "request sent, waiting for response: sender=%s recipient=%s subject=%s correlation_id=%s",
            sender,
            recipient,
            subject,
            message.id,
        )

        # 等待响应
        timeout = timeout or self._response_timeout
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            logger.debug(
                "response received: correlation_id=%s status=%s",
                message.id,
                response.status.value if response.status else None,
            )
            return response
        except asyncio.TimeoutError:
            self._pending_responses.pop(message.id, None)
            logger.warning(
                "request timeout: sender=%s recipient=%s subject=%s timeout=%s",
                sender,
                recipient,
                subject,
                timeout,
            )
            raise

    async def broadcast(
        self,
        sender: str,
        subject: str,
        payload: dict[str, Any] | None = None,
        channel_name: str | None = None,
    ) -> None:
        """广播消息。

        Args:
            sender: 发送方 ID
            subject: 消息主题
            payload: 消息内容
            channel_name: 指定通道名称
        """
        if self._closed:
            raise RuntimeError("AgentNetwork is closed")

        message = AgentMessage(
            type=MessageType.EVENT,
            sender=sender,
            recipient=None,  # broadcast
            subject=subject,
            payload=payload or {},
        )

        channel = self._get_channel(channel_name)
        await channel.send(message)

        logger.debug(
            "broadcast sent: sender=%s subject=%s",
            sender,
            subject,
        )

    def _get_channel(self, name: str | None) -> AgentChannel:
        """获取通道。"""
        if name is None:
            return self._default_channel
        if name not in self._channels:
            self._channels[name] = InMemoryChannel()
        return self._channels[name]

    async def create_channel(self, name: str) -> AgentChannel:
        """创建命名通道。

        Args:
            name: 通道名称

        Returns:
            创建的通道
        """
        if name in self._channels:
            raise ValueError(f"Channel '{name}' already exists")
        channel = InMemoryChannel()
        self._channels[name] = channel
        logger.info("channel %s created", name)
        return channel

    async def close_channel(self, name: str) -> None:
        """关闭命名通道。

        Args:
            name: 通道名称
        """
        if name not in self._channels:
            return
        channel = self._channels[name]
        await channel.close()
        del self._channels[name]
        logger.info("channel %s closed", name)

    async def close(self) -> None:
        """关闭 Agent 网络。"""
        self._closed = True

        # 关闭所有通道
        await self._default_channel.close()
        for channel in self._channels.values():
            await channel.close()
        self._channels.clear()
        self._agents.clear()

        # 取消所有待处理的响应
        for future in self._pending_responses.values():
            if not future.done():
                future.cancel()
        self._pending_responses.clear()

        logger.info("agent network closed")

    @property
    def is_closed(self) -> bool:
        """检查网络是否已关闭。"""
        return self._closed

    def set_response_timeout(self, timeout: float) -> None:
        """设置默认响应超时时间。

        Args:
            timeout: 超时时间（秒）
        """
        self._response_timeout = timeout


# 便捷函数
async def get_agent_net() -> AgentNetwork:
    """获取 AgentNetwork 单例。"""
    return await AgentNetwork.get_instance()


def get_agent_net_sync() -> AgentNetwork:
    """同步获取 AgentNetwork 单例。"""
    return AgentNetwork.get_instance_sync()
