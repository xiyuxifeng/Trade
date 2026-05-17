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
    """把字符串 event_id 转成 UUID。"""
    if isinstance(event_id, UUID):
        return event_id
    return UUID(str(event_id))


class DataAuditQueryService(BaseService):
    """数据写入审计查询服务。"""

    service_name = "data-audit-query"

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

    def _serialize_event(self, event: DataAuditEvent) -> dict[str, Any]:
        """把审计事件整理成 UI 可直接消费的结构。"""
        return {
            "id": str(event.id),
            "event_type": event.event_type,
            "actor": event.actor,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "dataset_version": event.dataset_version,
            "source": event.source,
            "payload": _sanitize_audit_data(event.payload),
            "event_at": _to_plain(event.event_at),
            "created_at": _to_plain(event.created_at),
            "updated_at": _to_plain(event.updated_at),
        }

    async def _load_rows(
        self,
        session: Any,
        *,
        event_type: str | None,
        actor: str | None,
        source: str | None,
        entity_type: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> list[DataAuditEvent]:
        """加载满足条件的审计日志。"""
        stmt = select(DataAuditEvent).order_by(desc(DataAuditEvent.event_at), desc(DataAuditEvent.created_at), desc(DataAuditEvent.id))
        if event_type:
            stmt = stmt.where(DataAuditEvent.event_type == event_type)
        if actor:
            stmt = stmt.where(DataAuditEvent.actor == actor)
        if source:
            stmt = stmt.where(DataAuditEvent.source == source)
        if entity_type:
            stmt = stmt.where(DataAuditEvent.entity_type == entity_type)

        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        filtered: list[DataAuditEvent] = []
        for event in rows:
            event_time = event.event_at if event.event_at.tzinfo is not None else event.event_at.replace(tzinfo=UTC)
            event_date = event_time.astimezone(UTC).date()
            if start_date is not None and event_date < start_date:
                continue
            if end_date is not None and event_date > end_date:
                continue
            filtered.append(event)
        return filtered

    async def list_data_audits(
        self,
        *,
        event_type: str | None = None,
        actor: str | None = None,
        source: str | None = None,
        entity_type: str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ServiceResult:
        """查询数据写入审计事件。"""
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
                event_type=event_type,
                actor=actor,
                source=source,
                entity_type=entity_type,
                start_date=normalized_start_date,
                end_date=normalized_end_date,
            )

        total = len(rows)
        page_items = rows[skip : skip + limit]
        serialized_items = [self._serialize_event(item) for item in page_items]
        event_type_counts: dict[str, int] = {}
        entity_type_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        for item in rows:
            event_type_counts[item.event_type] = event_type_counts.get(item.event_type, 0) + 1
            entity_type_counts[item.entity_type] = entity_type_counts.get(item.entity_type, 0) + 1
            source_counts[item.source] = source_counts.get(item.source, 0) + 1

        return ServiceResult(
            status="ok",
            message="data audits listed",
            payload={
                "filters": {
                    "event_type": event_type,
                    "actor": actor,
                    "source": source,
                    "entity_type": entity_type,
                    "start_date": normalized_start_date.isoformat() if normalized_start_date else None,
                    "end_date": normalized_end_date.isoformat() if normalized_end_date else None,
                },
                "summary": {
                    "total": total,
                    "event_type_counts": event_type_counts,
                    "entity_type_counts": entity_type_counts,
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

    async def get_data_audit(self, event_id: str | UUID) -> ServiceResult:
        """查询单条数据审计事件。"""
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
            if event is None:
                return ServiceResult(status="partial", message="data audit not found", payload={"event_id": str(event_id)})

        return ServiceResult(status="ok", message="data audit loaded", payload={"item": self._serialize_event(event)})


def get_data_audit_query_service() -> DataAuditQueryService:
    """返回数据审计查询服务。"""
    return DataAuditQueryService()
