from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import desc, select

from src.models.data_audit_event import DataAuditEvent
from src.services.base import BaseService, ServiceResult
from src.services.job_service import _sanitize_audit_data, _to_plain


def _normalize_date(value: date | str | None) -> date | None:
    """把日期参数统一成 date。"""
    if value in {None, ""}:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _parse_event_id(event_id: str | UUID) -> UUID:
    """将字符串 event_id 转成 UUID。"""
    if isinstance(event_id, UUID):
        return event_id
    return UUID(str(event_id))


def _extract_request_context(payload: Any) -> dict[str, Any]:
    """提取 permission denied 日志中的请求上下文。"""
    if not isinstance(payload, dict):
        return {}

    request = payload.get("request")
    response = payload.get("response")
    principal = payload.get("principal")
    if not isinstance(request, dict):
        request = {}
    if not isinstance(response, dict):
        response = {}
    if not isinstance(principal, dict):
        principal = {}

    return {
        "request": {
            "method": request.get("method"),
            "path": request.get("path"),
        },
        "response": {
            "status_code": response.get("status_code"),
            "detail": response.get("detail"),
        },
        "principal": {
            "role": principal.get("role"),
            "api_key_label": principal.get("api_key_label"),
            "authenticated": principal.get("authenticated"),
            "source": principal.get("source"),
        },
    }


class SecurityAuditQueryService(BaseService):
    """安全审计查询服务。"""

    service_name = "security-audit-query"

    def __init__(self, *, session_scope_factory: Callable[[], Any] | None = None) -> None:
        self._session_scope_factory = session_scope_factory

    def _ensure_session_factory(self) -> Callable[[], Any]:
        """确保存在数据库 session_scope 工厂。"""
        if self._session_scope_factory is not None:
            return self._session_scope_factory

        from src.db.session import session_scope

        self._session_scope_factory = session_scope
        return session_scope

    def _error(
        self,
        *,
        status: str,
        error_type: str,
        message: str,
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """构造结构化错误结果。"""
        return ServiceResult(
            status=status,  # type: ignore[arg-type]
            message=message,
            payload={
                "error": {
                    "type": error_type,
                    "message": message,
                    "detail": detail,
                    "metadata": metadata or {},
                }
            },
        )

    def _serialize_permission_denied_event(self, event: DataAuditEvent) -> dict[str, Any]:
        """把权限拒绝日志整理成 UI 可直接消费的结构。"""
        request_context = _extract_request_context(event.payload)
        return {
            "id": str(event.id),
            "event_type": event.event_type,
            "actor": event.actor,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "dataset_version": event.dataset_version,
            "source": event.source,
            "request_context": request_context,
            "payload": _sanitize_audit_data(event.payload),
            "event_at": _to_plain(event.event_at),
            "created_at": _to_plain(event.created_at),
            "updated_at": _to_plain(event.updated_at),
        }

    async def _load_rows(
        self,
        session: Any,
        *,
        actor: str | None,
        source: str | None,
        path: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> list[DataAuditEvent]:
        """加载满足基础条件的权限拒绝日志。"""
        stmt = (
            select(DataAuditEvent)
            .where(DataAuditEvent.event_type == "permission_denied")
            .order_by(desc(DataAuditEvent.event_at), desc(DataAuditEvent.created_at), desc(DataAuditEvent.id))
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        filtered: list[DataAuditEvent] = []
        for event in rows:
            if actor and event.actor != actor:
                continue
            if source and event.source != source:
                continue

            request_context = _extract_request_context(event.payload)
            request = request_context.get("request", {})
            request_path = request.get("path") if isinstance(request, dict) else None
            if path and request_path != path:
                continue

            event_time = event.event_at if event.event_at.tzinfo is not None else event.event_at.replace(tzinfo=UTC)
            event_date = event_time.astimezone(UTC).date()
            if start_date is not None and event_date < start_date:
                continue
            if end_date is not None and event_date > end_date:
                continue

            filtered.append(event)

        return filtered

    async def list_permission_denied_logs(
        self,
        *,
        actor: str | None = None,
        source: str | None = None,
        path: str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ServiceResult:
        """查询权限拒绝日志。"""
        if skip < 0 or limit < 1:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="skip must be >= 0 and limit must be >= 1",
                metadata={"skip": skip, "limit": limit},
            )

        try:
            normalized_start_date = _normalize_date(start_date)
            normalized_end_date = _normalize_date(end_date)
        except ValueError as exc:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid date",
                detail=str(exc),
                metadata={"start_date": start_date, "end_date": end_date},
            )

        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            rows = await self._load_rows(
                session,
                actor=actor,
                source=source,
                path=path,
                start_date=normalized_start_date,
                end_date=normalized_end_date,
            )

        total = len(rows)
        page_items = rows[skip : skip + limit]
        serialized_items = [self._serialize_permission_denied_event(item) for item in page_items]
        source_counts: dict[str, int] = {}
        for item in rows:
            source_key = str(item.source or "unknown")
            source_counts[source_key] = source_counts.get(source_key, 0) + 1

        unique_paths = len(
            {
                str(request_context.get("request", {}).get("path"))
                for item in rows
                for request_context in [_extract_request_context(item.payload)]
                if request_context.get("request", {}).get("path")
            }
        )
        unique_actors = len({item.actor for item in rows})

        return ServiceResult(
            status="ok",
            message="permission denied logs listed",
            payload={
                "filters": {
                    "actor": actor,
                    "source": source,
                    "path": path,
                    "start_date": normalized_start_date.isoformat() if normalized_start_date else None,
                    "end_date": normalized_end_date.isoformat() if normalized_end_date else None,
                },
                "summary": {
                    "total": total,
                    "unique_actors": unique_actors,
                    "unique_paths": unique_paths,
                    "source_counts": source_counts,
                },
                "page": {
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                    "count": len(serialized_items),
                },
                "items": serialized_items,
            },
        )

    async def get_permission_denied_log(self, event_id: str | UUID) -> ServiceResult:
        """查询单条权限拒绝日志。"""
        session_scope = self._ensure_session_factory()
        try:
            event_uuid = _parse_event_id(event_id)
        except ValueError:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid event_id",
                detail=str(event_id),
                metadata={"event_id": str(event_id)},
            )

        async with session_scope() as session:
            event = await session.get(DataAuditEvent, event_uuid)
            if event is None or event.event_type != "permission_denied":
                return ServiceResult(status="partial", message="permission denied log not found", payload={"event_id": str(event_id)})

        return ServiceResult(
            status="ok",
            message="permission denied log loaded",
            payload={
                "item": self._serialize_permission_denied_event(event),
            },
        )


def get_security_audit_query_service() -> SecurityAuditQueryService:
    """返回安全审计查询服务。"""
    return SecurityAuditQueryService()
