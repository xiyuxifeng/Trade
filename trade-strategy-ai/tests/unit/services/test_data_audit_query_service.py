from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.data_audit_event import DataAuditEvent
from src.services.data_audit_query_service import DataAuditQueryService


@pytest.mark.asyncio
async def test_data_audit_query_service_lists_backup_history(tmp_path: Path) -> None:
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
                event_type="backup_project_state",
                actor="ui.ops",
                entity_type="backup",
                entity_id="backup-1",
                dataset_version="backup-1",
                payload={
                    "tables": ["jobs", "artifacts"],
                    "row_counts": {"jobs": 1, "artifacts": 2},
                    "include_processed": True,
                    "processed_copied": True,
                    "artifacts_copied": True,
                },
                source="ui",
                event_at=datetime(2026, 5, 17, 8, 0, tzinfo=UTC),
                created_at=datetime(2026, 5, 17, 8, 0, tzinfo=UTC),
                updated_at=datetime(2026, 5, 17, 8, 0, tzinfo=UTC),
            )
        )
        session.add(
            DataAuditEvent(
                event_type="restore_project_state",
                actor="ui.ops",
                entity_type="backup",
                entity_id="backup-1",
                dataset_version="backup-1",
                payload={
                    "tables": ["jobs", "artifacts"],
                    "row_counts": {"jobs": 1, "artifacts": 2},
                    "include_processed": True,
                    "processed_restored": True,
                    "artifacts_restored": True,
                },
                source="ui",
                event_at=datetime(2026, 5, 17, 9, 0, tzinfo=UTC),
                created_at=datetime(2026, 5, 17, 9, 0, tzinfo=UTC),
                updated_at=datetime(2026, 5, 17, 9, 0, tzinfo=UTC),
            )
        )
        await session.commit()

    service = DataAuditQueryService(session_scope_factory=_session_scope)
    result = await service.list_data_audits(entity_type="backup")

    assert result.status == "ok"
    assert result.payload["summary"]["total"] == 2
    assert result.payload["items"][0]["event_type"] == "restore_project_state"
    assert result.payload["items"][1]["event_type"] == "backup_project_state"
    assert result.payload["items"][0]["payload"]["artifacts_restored"] is True

