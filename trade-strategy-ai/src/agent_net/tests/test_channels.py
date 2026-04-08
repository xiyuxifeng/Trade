"""单元测试 - Agent 通道。"""

from __future__ import annotations

import asyncio
import pytest

from src.agent_net.channels import AgentChannel, InMemoryChannel
from src.agent_net.messages import AgentMessage, MessageType


class TestInMemoryChannel:
    """测试 InMemoryChannel 实现。"""

    @pytest.fixture
    def channel(self) -> InMemoryChannel:
        """创建测试通道。"""
        return InMemoryChannel()

    @pytest.fixture
    async def channel_with_agent(self) -> tuple[InMemoryChannel, asyncio.Queue]:
        """创建已订阅 agent 的通道。"""
        channel = InMemoryChannel()
        messages: asyncio.Queue[AgentMessage] = asyncio.Queue()

        async def handler(msg: AgentMessage) -> None:
            await messages.put(msg)

        await channel.subscribe("agent_1", handler)
        await channel.start_dispatch("agent_1")

        yield channel, messages

        await channel.close()

    @pytest.mark.asyncio
    async def test_send_and_receive(self, channel_with_agent: tuple[InMemoryChannel, asyncio.Queue]) -> None:
        """测试发送和接收消息。"""
        channel, messages = channel_with_agent

        msg = AgentMessage(
            type=MessageType.REQUEST,
            sender="agent_0",
            recipient="agent_1",
            subject="test",
            payload={"data": "hello"},
        )
        await channel.send(msg)

        received = await asyncio.wait_for(messages.get(), timeout=2.0)
        assert received.id == msg.id
        assert received.sender == "agent_0"
        assert received.subject == "test"

    @pytest.mark.asyncio
    async def test_broadcast(self, channel_with_agent: tuple[InMemoryChannel, asyncio.Queue]) -> None:
        """测试广播消息。"""
        channel, messages = channel_with_agent

        broadcast = AgentMessage(
            type=MessageType.EVENT,
            sender="agent_0",
            recipient=None,  # broadcast
            subject="system_event",
            payload={},
        )
        await channel.send(broadcast)

        received = await asyncio.wait_for(messages.get(), timeout=2.0)
        assert received.is_broadcast()
        assert received.subject == "system_event"

    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(self) -> None:
        """测试订阅和取消订阅。"""
        channel = InMemoryChannel()

        handler_count = 0

        async def handler(msg: AgentMessage) -> None:
            nonlocal handler_count
            handler_count += 1

        await channel.subscribe("agent_1", handler)
        await channel.subscribe("agent_2", handler)

        assert "agent_1" in channel._subscribers
        assert "agent_2" in channel._subscribers

        await channel.unsubscribe("agent_1")
        assert "agent_1" not in channel._subscribers
        assert "agent_2" in channel._subscribers

        await channel.close()

    @pytest.mark.asyncio
    async def test_close_channel(self, channel: InMemoryChannel) -> None:
        """测试关闭通道。"""
        handler_called = False

        async def handler(msg: AgentMessage) -> None:
            nonlocal handler_called
            handler_called = True

        await channel.subscribe("agent_1", handler)
        await channel.close()

        assert channel.is_closed is True

        # 发送消息应该失败
        msg = AgentMessage(
            type=MessageType.MESSAGE,
            sender="a",
            recipient="b",
            subject="",
            payload={},
        )
        with pytest.raises(RuntimeError, match="Channel is closed"):
            await channel.send(msg)

    @pytest.mark.asyncio
    async def test_queue_size(self, channel: InMemoryChannel) -> None:
        """测试队列大小。"""
        assert channel.queue_size == 0

        msg = AgentMessage(
            type=MessageType.MESSAGE,
            sender="a",
            recipient="b",
            subject="",
            payload={},
        )

        await channel.send(msg)
        await channel.send(msg)
        assert channel.queue_size == 2

        await channel.close()

    @pytest.mark.asyncio
    async def test_multiple_messages_order(self, channel_with_agent: tuple[InMemoryChannel, asyncio.Queue]) -> None:
        """测试多条消息的顺序。"""
        channel, messages = channel_with_agent

        for i in range(3):
            msg = AgentMessage(
                type=MessageType.MESSAGE,
                sender="agent_0",
                recipient="agent_1",
                subject=f"msg_{i}",
                payload={},
            )
            await channel.send(msg)

        received_ids = []
        for _ in range(3):
            msg = await asyncio.wait_for(messages.get(), timeout=2.0)
            received_ids.append(msg.subject)

        assert received_ids == ["msg_0", "msg_1", "msg_2"]

    @pytest.mark.asyncio
    async def test_agent_not_subscribed_error(self, channel: InMemoryChannel) -> None:
        """测试未订阅的 agent 无法接收消息。"""
        msg = AgentMessage(
            type=MessageType.MESSAGE,
            sender="a",
            recipient="agent_1",  # 未订阅的 agent
            subject="",
            payload={},
        )
        await channel.send(msg)

        # 因为 agent_1 没有订阅，消息不会被处理
        assert channel.queue_size == 1

        await channel.close()

    @pytest.mark.asyncio
    async def test_abstract_channel_cannot_instantiate(self) -> None:
        """测试 AgentChannel 是抽象类不能直接实例化。"""
        with pytest.raises(TypeError):
            AgentChannel()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_close_idempotent(self, channel: InMemoryChannel) -> None:
        """测试多次关闭是幂等的。"""
        await channel.close()
        await channel.close()
        assert channel.is_closed
