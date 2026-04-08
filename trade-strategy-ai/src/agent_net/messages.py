"""Agent 消息格式定义。

提供统一的 Agent 间消息数据结构，包括：
- AgentMessage: 核心消息格式
- MessageType: 消息类型枚举
- ResponseStatus: 响应状态枚举
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class MessageType(Enum):
    """消息类型枚举。"""

    REQUEST = "request"  # 请求消息，需要响应
    RESPONSE = "response"  # 响应消息
    EVENT = "event"  # 事件消息，发布/订阅
    COMMAND = "command"  # 命令消息，单向指令
    MESSAGE = "message"  # 普通消息，单向传递


class ResponseStatus(Enum):
    """响应状态枚举。"""

    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"


@dataclass(slots=True)
class AgentMessage:
    """Agent 间传递的统一消息格式。

    Attributes:
        id: 消息唯一标识符
        type: 消息类型（request/response/event/command）
        sender: 发送方 agent ID
        recipient: 接收方 agent ID，None 表示广播
        subject: 消息主题/意图
        payload: 消息内容（字典形式，便于序列化）
        correlation_id: 关联 ID，用于 request/response 配对
        timestamp: 消息时间戳
        headers: 扩展头信息
        status: 响应状态（仅 response 类型）
        error: 错误信息（仅 error 响应）
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    type: MessageType = MessageType.REQUEST
    sender: str = ""
    recipient: str | None = None  # None = broadcast
    subject: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None  # for request/response pairing
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    headers: dict[str, str] = field(default_factory=dict)
    status: ResponseStatus | None = None
    error: str | None = None

    def to_response(self, status: ResponseStatus, payload: dict[str, Any] | None = None, error: str | None = None) -> "AgentMessage":
        """创建对此消息的响应消息。

        Args:
            status: 响应状态
            payload: 响应数据
            error: 错误信息

        Returns:
            新的响应消息
        """
        return AgentMessage(
            type=MessageType.RESPONSE,
            sender=self.recipient or "",
            recipient=self.sender,
            subject=f"re: {self.subject}",
            payload=payload or {},
            correlation_id=self.id,
            status=status,
            error=error,
        )

    def is_request(self) -> bool:
        """判断是否为请求消息。"""
        return self.type == MessageType.REQUEST

    def is_response(self) -> bool:
        """判断是否为响应消息。"""
        return self.type == MessageType.RESPONSE

    def is_event(self) -> bool:
        """判断是否为事件消息。"""
        return self.type == MessageType.EVENT

    def is_broadcast(self) -> bool:
        """判断是否为广播消息。"""
        return self.recipient is None

    def matches_correlation_id(self, other_id: str) -> bool:
        """判断是否匹配给定的关联 ID。"""
        return self.correlation_id == other_id
