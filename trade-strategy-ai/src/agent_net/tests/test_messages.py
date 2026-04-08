"""单元测试 - Agent 消息格式。"""

from __future__ import annotations

import pytest
from datetime import datetime, UTC

from src.agent_net.messages import AgentMessage, MessageType, ResponseStatus


class TestAgentMessage:
    """测试 AgentMessage 数据结构。"""

    def test_create_basic_message(self) -> None:
        """测试创建基本消息。"""
        msg = AgentMessage(
            type=MessageType.REQUEST,
            sender="agent_1",
            recipient="agent_2",
            subject="test_request",
            payload={"key": "value"},
        )

        assert msg.type == MessageType.REQUEST
        assert msg.sender == "agent_1"
        assert msg.recipient == "agent_2"
        assert msg.subject == "test_request"
        assert msg.payload == {"key": "value"}
        assert msg.correlation_id is None
        assert msg.status is None
        assert msg.error is None
        assert isinstance(msg.id, str)
        assert isinstance(msg.timestamp, datetime)

    def test_create_message_with_correlation_id(self) -> None:
        """测试创建带关联 ID 的消息。"""
        msg = AgentMessage(
            type=MessageType.REQUEST,
            sender="agent_1",
            recipient="agent_2",
            subject="test",
            payload={},
            correlation_id="corr_123",
        )

        assert msg.correlation_id == "corr_123"

    def test_to_response_ok(self) -> None:
        """测试创建成功响应。"""
        request = AgentMessage(
            type=MessageType.REQUEST,
            sender="agent_1",
            recipient="agent_2",
            subject="test",
            payload={},
            correlation_id="corr_123",
        )

        response = request.to_response(ResponseStatus.OK, {"result": "success"})

        assert response.type == MessageType.RESPONSE
        assert response.sender == "agent_2"
        assert response.recipient == "agent_1"
        assert response.subject == "re: test"
        # correlation_id 应该是原始消息的 id，而不是原始消息的 correlation_id
        assert response.correlation_id == request.id
        assert response.status == ResponseStatus.OK
        assert response.payload == {"result": "success"}
        assert response.error is None

    def test_to_response_error(self) -> None:
        """测试创建错误响应。"""
        request = AgentMessage(
            type=MessageType.REQUEST,
            sender="agent_1",
            recipient="agent_2",
            subject="test",
            payload={},
        )

        response = request.to_response(ResponseStatus.ERROR, error="Something went wrong")

        assert response.status == ResponseStatus.ERROR
        assert response.error == "Something went wrong"

    def test_is_request(self) -> None:
        """测试 is_request 方法。"""
        msg = AgentMessage(type=MessageType.REQUEST, sender="a", recipient="b", subject="", payload={})
        assert msg.is_request() is True

        msg = AgentMessage(type=MessageType.RESPONSE, sender="a", recipient="b", subject="", payload={})
        assert msg.is_request() is False

    def test_is_response(self) -> None:
        """测试 is_response 方法。"""
        msg = AgentMessage(type=MessageType.RESPONSE, sender="a", recipient="b", subject="", payload={})
        assert msg.is_response() is True

        msg = AgentMessage(type=MessageType.EVENT, sender="a", recipient=None, subject="", payload={})
        assert msg.is_response() is False

    def test_is_event(self) -> None:
        """测试 is_event 方法。"""
        msg = AgentMessage(type=MessageType.EVENT, sender="a", recipient=None, subject="", payload={})
        assert msg.is_event() is True

    def test_is_broadcast(self) -> None:
        """测试广播消息判断。"""
        broadcast = AgentMessage(type=MessageType.EVENT, sender="a", recipient=None, subject="", payload={})
        assert broadcast.is_broadcast() is True

        unicast = AgentMessage(type=MessageType.EVENT, sender="a", recipient="b", subject="", payload={})
        assert unicast.is_broadcast() is False

    def test_matches_correlation_id(self) -> None:
        """测试关联 ID 匹配。"""
        msg = AgentMessage(
            type=MessageType.RESPONSE,
            sender="b",
            recipient="a",
            subject="",
            payload={},
            correlation_id="corr_123",
        )

        assert msg.matches_correlation_id("corr_123") is True
        assert msg.matches_correlation_id("corr_456") is False

    def test_message_type_enum_values(self) -> None:
        """测试消息类型枚举值。"""
        assert MessageType.REQUEST.value == "request"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.EVENT.value == "event"
        assert MessageType.COMMAND.value == "command"
        assert MessageType.MESSAGE.value == "message"

    def test_response_status_enum_values(self) -> None:
        """测试响应状态枚举值。"""
        assert ResponseStatus.OK.value == "ok"
        assert ResponseStatus.ERROR.value == "error"
        assert ResponseStatus.TIMEOUT.value == "timeout"
        assert ResponseStatus.NOT_FOUND.value == "not_found"
        assert ResponseStatus.UNSUPPORTED.value == "unsupported"

    def test_unique_message_ids(self) -> None:
        """测试每条消息都有唯一 ID。"""
        msg1 = AgentMessage(type=MessageType.REQUEST, sender="a", recipient="b", subject="", payload={})
        msg2 = AgentMessage(type=MessageType.REQUEST, sender="a", recipient="b", subject="", payload={})

        assert msg1.id != msg2.id
