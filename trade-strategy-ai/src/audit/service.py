from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, AsyncContextManager, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import session_scope
from src.models.data_audit_event import DataAuditEvent


SessionScopeFactory = Callable[[], AsyncContextManager[AsyncSession]]


def default_dataset_version(*, prefix: str) -> str:
    """Build a compact version string for batch-level audit records."""

    return f"{prefix}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"


class AuditService:
    """Persist batch-level audit events for write-heavy workflows."""

    def __init__(self, *, session_scope_factory: SessionScopeFactory | None = None) -> None:
        self._session_scope_factory = session_scope_factory or session_scope

    @asynccontextmanager
    async def _session(self) -> AsyncContextManager[AsyncSession]:
        async with self._session_scope_factory() as session:
            yield session

    async def record(
        self,
        *,
        event_type: str,
        actor: str,
        entity_type: str,
        entity_id: str | None,
        dataset_version: str | None,
        payload: dict[str, Any],
        source: str,
        event_at: datetime | None = None,
    ) -> DataAuditEvent:
        """Insert one audit event into the database."""

        event = DataAuditEvent(
            event_type=event_type,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            dataset_version=dataset_version,
            payload=payload,
            source=source,
            event_at=event_at or datetime.now(UTC),
        )
        async with self._session() as session:
            session.add(event)
            await session.flush()
        return event

