from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.data_audit_event import DataAuditEvent
from src.services.security_audit_query_service import SecurityAuditQueryService


@pytest.mark.asyncio
async def test_security_audit_query_service_lists_permission_denied_logs(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'audit.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(DataAuditEvent.__table__.create)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async with session_factory() as session:
        session.add(
            DataAuditEvent(
                event_type="permission_denied",
                actor="anonymous",
                entity_type="http_request",
                entity_id="GET /api/ui/v1/job-audits",
                dataset_version=None,
                payload={
                    "request": {"method": "GET", "path": "/api/ui/v1/job-audits"},
                    "response": {"status_code": 403, "detail": "insufficient permissions"},
                    "principal": {"role": "anonymous", "api_key_label": None, "authenticated": False, "source": "anonymous"},
                },
                source="ui",
                event_at=datetime(2026, 5, 17, 9, 0, tzinfo=UTC),
                created_at=datetime(2026, 5, 17, 9, 0, tzinfo=UTC),
                updated_at=datetime(2026, 5, 17, 9, 0, tzinfo=UTC),
            )
        )
        session.add(
            DataAuditEvent(
                event_type="backup_project_state",
                actor="cli.backup_data",
                entity_type="backup",
                entity_id="backup-1",
                dataset_version="backup-1",
                payload={"request": {"method": "POST", "path": "/api/ui/v1/ops/backup"}},
                source="backup-data",
                event_at=datetime(2026, 5, 17, 8, 0, tzinfo=UTC),
                created_at=datetime(2026, 5, 17, 8, 0, tzinfo=UTC),
                updated_at=datetime(2026, 5, 17, 8, 0, tzinfo=UTC),
            )
        )
        await session.commit()

    service = SecurityAuditQueryService(session_scope_factory=_session_scope)
    result = await service.list_permission_denied_logs(path="/api/ui/v1/job-audits")

    assert result.status == "ok"
    assert result.payload["summary"]["total"] == 1
    assert result.payload["items"][0]["entity_id"] == "GET /api/ui/v1/job-audits"
    assert result.payload["items"][0]["request_context"]["response"]["status_code"] == 403
