from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.models.step_timeline import JobTimeline, StepTimelineItem, StepTimelineStatus
from src.services.base import BaseService


class StepTimelineService(BaseService):
    """把 Job audit events 归一化为结构化 timeline。"""

    service_name = "step_timeline"

    def build_job_timeline(self, *, job: dict[str, Any]) -> JobTimeline:
        """根据 Job 及其 audit events 构建 timeline。"""
        items = [
            self._build_item(job=job, event=event, order=index + 1)
            for index, event in enumerate(self._sorted_events(job.get("audit_events") or []))
        ]
        return JobTimeline(
            job_id=str(job.get("id") or "unknown"),
            job_status=str(job.get("status") or "unknown"),
            items=items,
            metadata={
                "started_at": self._plain_datetime(job.get("started_at")),
                "finished_at": self._plain_datetime(job.get("finished_at")),
            },
        )

    def _sorted_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按事件时间排序，保证 timeline 稳定。"""
        return sorted(
            events,
            key=lambda event: (
                self._coerce_datetime(event.get("event_at") or event.get("created_at"))
                or datetime.min.replace(tzinfo=UTC),
                str(event.get("operation") or ""),
            ),
        )

    def _build_item(self, *, job: dict[str, Any], event: dict[str, Any], order: int) -> StepTimelineItem:
        """把单条 audit event 转成 timeline item。"""
        operation = str(event.get("operation") or "unknown")
        event_at = self._coerce_datetime(event.get("event_at") or event.get("created_at"))
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        details = payload.get("details") if isinstance(payload, dict) and isinstance(payload.get("details"), dict) else {}
        status = self._resolve_status(job=job, operation=operation)
        started_at, finished_at = self._resolve_time_window(operation=operation, event_at=event_at, status=status)
        artifact_refs = self._extract_artifact_refs(details)

        return StepTimelineItem(
            step_id=self._resolve_step_id(operation=operation, order=order),
            step_name=operation,
            title=self._resolve_title(operation),
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=self._duration_ms(started_at, finished_at),
            error=self._extract_error(event=event, operation=operation, status=status),
            artifact_refs=artifact_refs,
            order=order,
            operation=operation,
            actor=str(event.get("actor") or job.get("created_by") or "system"),
            source=str(event.get("source") or "system"),
            metadata={
                "event_at": self._plain_datetime(event_at),
            },
        )

    def _resolve_step_id(self, *, operation: str, order: int) -> str:
        """生成稳定的 step_id。"""
        if operation == "heartbeat":
            return f"job.heartbeat.{order}"
        if operation == "bind_artifact":
            return f"job.bind_artifact.{order}"
        return f"job.{operation}"

    def _resolve_title(self, operation: str) -> str:
        """生成给用户看的标题。"""
        return {
            "create": "Job 创建",
            "start": "Job 启动",
            "heartbeat": "Job 心跳",
            "complete": "Job 完成",
            "fail": "Job 失败",
            "cancel": "Job 取消",
            "bind_artifact": "产物绑定",
        }.get(operation, f"Job {operation}")

    def _resolve_status(self, *, job: dict[str, Any], operation: str) -> str:
        """根据 Job 状态和事件类型推导 timeline 状态。"""
        job_status = str(job.get("status") or "unknown")
        if operation == "fail":
            return StepTimelineStatus.failed.value
        if operation == "cancel" or job_status == StepTimelineStatus.cancelled.value:
            return StepTimelineStatus.cancelled.value
        if operation in {"start", "heartbeat"} and job_status == StepTimelineStatus.running.value:
            return StepTimelineStatus.running.value
        if operation == "complete" and job_status == StepTimelineStatus.success.value:
            return StepTimelineStatus.success.value
        if operation == "start":
            return StepTimelineStatus.success.value
        return StepTimelineStatus.success.value

    def _resolve_time_window(
        self,
        *,
        operation: str,
        event_at: datetime | None,
        status: str,
    ) -> tuple[datetime | None, datetime | None]:
        """给 timeline item 生成开始/结束时间窗口。"""
        if event_at is None:
            return None, None
        if operation == "start" and status == StepTimelineStatus.running.value:
            return event_at, None
        return event_at, event_at

    def _extract_error(self, *, event: dict[str, Any], operation: str, status: str) -> dict[str, Any] | None:
        """把失败信息收敛成结构化 error。"""
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        details = payload.get("details") if isinstance(payload, dict) and isinstance(payload.get("details"), dict) else {}
        error = details.get("error") or payload.get("error")
        if operation not in {"fail", "cancel"} and status != StepTimelineStatus.failed.value:
            return error if isinstance(error, dict) else None
        if isinstance(error, dict):
            return error
        if isinstance(details.get("reason"), str):
            return {"message": details["reason"]}
        if isinstance(payload.get("message"), str):
            return {"message": payload["message"]}
        return {"message": f"job {operation}"}

    def _extract_artifact_refs(self, details: dict[str, Any]) -> list[dict[str, Any]]:
        """把审计 payload 里的 artifact 转成 contract 引用。"""
        artifact = details.get("artifact")
        if not isinstance(artifact, dict):
            return []
        return [artifact]

    def _coerce_datetime(self, value: Any) -> datetime | None:
        """把字符串或 datetime 统一成 aware datetime。"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        return None

    def _plain_datetime(self, value: Any) -> str | None:
        """把时间转换成 JSON 友好的字符串。"""
        parsed = self._coerce_datetime(value)
        return parsed.isoformat() if parsed is not None else None

    def _duration_ms(self, started_at: datetime | None, finished_at: datetime | None) -> int | None:
        """计算耗时毫秒数。"""
        if started_at is None or finished_at is None:
            return None
        return max(0, int((finished_at - started_at).total_seconds() * 1000))
