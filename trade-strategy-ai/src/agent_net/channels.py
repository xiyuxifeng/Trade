"""Agent 通道接口定义。

提供 Agent 间通信的抽象接口和内存实现：
- AgentChannel: 抽象通道接口
- InMemoryChannel: 基于 asyncio.Queue 的内存通道
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from src.common.logger import get_logger
from src.agent_net.messages import AgentMessage


logger = get_logger("agent_net.channel")


class AgentChannel(ABC):
    """Agent 通道抽象接口。

    定义 Agent 间消息传递的标准接口，支持：
    - 点对点发送
    - 订阅/取消订阅
    - 上下文管理器用于资源清理
    """

    @abstractmethod
    async def send(self, message: AgentMessage) -> None:
        """发送一条消息。

        Args:
            message: 要发送的消息
        """
        ...

    @abstractmethod
    async def subscribe(
        self,
        agent_id: str,
        handler: Callable[[AgentMessage], Awaitable[None]],
    ) -> None:
        """订阅消息。

        Args:
            agent_id: 订阅者 ID
            handler: 消息处理函数
        """
        ...

    @abstractmethod
    async def unsubscribe(self, agent_id: str) -> None:
        """取消订阅。

        Args:
            agent_id: 要取消订阅的 ID
        """
        ...

    @abstractmethod
    @asynccontextmanager
    async def receive(self, agent_id: str) -> AsyncIterator[AgentMessage]:
        """创建消息接收上下文管理器。

        Args:
            agent_id: 接收者 ID

        Yields:
            接收到的消息
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭通道，释放资源。"""
        ...


class InMemoryChannel(AgentChannel):
    """内存消息通道，基于 asyncio.Queue 实现。

    特性：
    - 支持多订阅者
    - 支持广播（recipient=None）
    - 消息持久化在队列中直到被消费
    - 线程安全（asyncio.Queue 本身是协程安全的）
    """

    def __init__(self, maxsize: int = 0) -> None:
        """初始化内存通道。

        Args:
            maxsize: 队列最大尺寸，0 表示无限制
        """
        self._queue: asyncio.Queue[AgentMessage] = asyncio.Queue(maxsize=maxsize)
        self._subscribers: dict[str, Callable[[AgentMessage], Awaitable[None]]] = {}
        self._running_tasks: set[asyncio.Task[None]] = set()
        self._closed = False
        self._lock = asyncio.Lock()

    async def send(self, message: AgentMessage) -> None:
        """发送消息到队列。

        Args:
            message: 要发送的消息

        Raises:
            RuntimeError: 通道已关闭
        """
        if self._closed:
            raise RuntimeError("Channel is closed")

        logger.debug(
            "sending message: msg_id=%s sender=%s recipient=%s subject=%s",
            message.id,
            message.sender,
            message.recipient,
            message.subject,
        )
        await self._queue.put(message)

    async def subscribe(
        self,
        agent_id: str,
        handler: Callable[[AgentMessage], Awaitable[None]],
    ) -> None:
        """订阅消息。

        Args:
            agent_id: 订阅者 ID
            handler: 消息处理函数
        """
        async with self._lock:
            if agent_id in self._subscribers:
                logger.warning("agent %s already subscribed", agent_id)
                return

            self._subscribers[agent_id] = handler
            logger.info("agent %s subscribed", agent_id)

    async def unsubscribe(self, agent_id: str) -> None:
        """取消订阅。

        Args:
            agent_id: 要取消订阅的 ID
        """
        async with self._lock:
            if agent_id in self._subscribers:
                del self._subscribers[agent_id]
                logger.info("agent %s unsubscribed", agent_id)

    @asynccontextmanager
    async def receive(self, agent_id: str) -> AsyncIterator[AgentMessage]:
        """创建消息接收上下文管理器。

        当作异步迭代器使用：
        async with channel.receive(agent_id) as msg_iter:
            async for message in msg_iter:
                await handle(message)

        Args:
            agent_id: 接收者 ID

        Yields:
            消息异步迭代器
        """
        if agent_id not in self._subscribers:
            raise KeyError(f"Agent {agent_id} is not subscribed")

        async def message_iterator() -> AsyncIterator[AgentMessage]:
            while not self._closed:
                try:
                    message = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # 广播消息或指定给该 agent 的消息
                if message.is_broadcast() or message.recipient == agent_id:
                    yield message

        yield message_iterator()

    async def _dispatch_loop(self, agent_id: str) -> None:
        """分发消息到指定 agent 的内部循环。"""
        handler = self._subscribers.get(agent_id)
        if handler is None:
            return

        while not self._closed:
            try:
                message = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue

            # 广播消息或指定给该 agent 的消息
            if message.is_broadcast() or message.recipient == agent_id:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(
                        "handler error: agent=%s msg_id=%s error=%s",
                        agent_id,
                        message.id,
                        str(e),
                    )

    async def start_dispatch(self, agent_id: str) -> None:
        """启动消息分发循环。

        Args:
            agent_id: 要启动分发的 agent ID
        """
        if agent_id not in self._subscribers:
            raise KeyError(f"Agent {agent_id} is not subscribed")

        task = asyncio.create_task(self._dispatch_loop(agent_id))
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)

    async def stop_dispatch(self, agent_id: str) -> None:
        """停止消息分发循环。

        Args:
            agent_id: 要停止分发的 agent ID
        """
        # 取消该 agent 相关的运行任务
        for task in list(self._running_tasks):
            if agent_id in str(task.get_coro()):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def close(self) -> None:
        """关闭通道，释放资源。"""
        self._closed = True

        # 取消所有运行中的任务
        for task in list(self._running_tasks):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._running_tasks.clear()
        self._subscribers.clear()

        logger.info("channel closed")

    @property
    def is_closed(self) -> bool:
        """检查通道是否已关闭。"""
        return self._closed

    @property
    def queue_size(self) -> int:
        """获取队列当前大小。"""
        return self._queue.qsize()
