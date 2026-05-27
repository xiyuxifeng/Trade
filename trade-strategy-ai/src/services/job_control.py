from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_KNOWN_RUNTIME_STATE_KEYS = {
    "schema_version",
    "paused",
    "cancel_requested",
    "checkpoint",
    "cursor",
    "stage",
    "resume_from",
    "last_safe_point",
    "paused_at",
    "resumed_at",
    "cancelled_at",
    "retried_at",
}


@dataclass(slots=True)
class JobControlState:
    """Job runtime_state 的统一控制载体。"""

    schema_version: int = 1
    paused: bool = False
    cancel_requested: bool = False
    checkpoint: dict[str, Any] | None = None
    cursor: dict[str, Any] | None = None
    stage: str | None = None
    resume_from: str | None = None
    last_safe_point: str | None = None
    paused_at: str | None = None
    resumed_at: str | None = None
    cancelled_at: str | None = None
    retried_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_runtime_state(cls, runtime_state: Any | None) -> "JobControlState":
        """把 ORM/JSON 里的 runtime_state 归一化成可操作对象。"""
        if not isinstance(runtime_state, dict):
            return cls()
        payload = dict(runtime_state)
        extra = {key: value for key, value in payload.items() if key not in _KNOWN_RUNTIME_STATE_KEYS}
        return cls(
            schema_version=int(payload.get("schema_version") or 1),
            paused=bool(payload.get("paused") or False),
            cancel_requested=bool(payload.get("cancel_requested") or False),
            checkpoint=payload.get("checkpoint") if isinstance(payload.get("checkpoint"), dict) else None,
            cursor=payload.get("cursor") if isinstance(payload.get("cursor"), dict) else None,
            stage=str(payload.get("stage")) if payload.get("stage") is not None else None,
            resume_from=str(payload.get("resume_from")) if payload.get("resume_from") is not None else None,
            last_safe_point=str(payload.get("last_safe_point")) if payload.get("last_safe_point") is not None else None,
            paused_at=str(payload.get("paused_at")) if payload.get("paused_at") is not None else None,
            resumed_at=str(payload.get("resumed_at")) if payload.get("resumed_at") is not None else None,
            cancelled_at=str(payload.get("cancelled_at")) if payload.get("cancelled_at") is not None else None,
            retried_at=str(payload.get("retried_at")) if payload.get("retried_at") is not None else None,
            extra=extra,
        )

    def to_runtime_state(self) -> dict[str, Any]:
        """把控制态转回可直接落库的 JSON 结构。"""
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "paused": self.paused,
            "cancel_requested": self.cancel_requested,
        }
        if self.checkpoint is not None:
            payload["checkpoint"] = self.checkpoint
        if self.cursor is not None:
            payload["cursor"] = self.cursor
        if self.stage is not None:
            payload["stage"] = self.stage
        if self.resume_from is not None:
            payload["resume_from"] = self.resume_from
        if self.last_safe_point is not None:
            payload["last_safe_point"] = self.last_safe_point
        if self.paused_at is not None:
            payload["paused_at"] = self.paused_at
        if self.resumed_at is not None:
            payload["resumed_at"] = self.resumed_at
        if self.cancelled_at is not None:
            payload["cancelled_at"] = self.cancelled_at
        if self.retried_at is not None:
            payload["retried_at"] = self.retried_at
        payload.update(self.extra)
        return payload

    def clone_with(self, **updates: Any) -> "JobControlState":
        """基于当前状态生成一个更新后的控制态。"""
        payload = self.to_runtime_state()
        payload.update(updates)
        return self.from_runtime_state(payload)


class JobControlInterrupted(RuntimeError):
    """Job 在安全边界被暂停或取消时抛出的协作式中断。"""

    def __init__(self, control_action: str, message: str | None = None) -> None:
        self.control_action = control_action
        super().__init__(message or control_action)
