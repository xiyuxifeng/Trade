from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.audit.service import AuditService
from src.models.data_audit_event import DataAuditEvent


@pytest.mark.asyncio
async def test_audit_service_records_event(tmp_path: Path) -> None:
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

    service = AuditService(session_scope_factory=_session_scope)
    event = await service.record(
        event_type="seed_project_data",
        actor="cli.seed_data",
        entity_type="database",
        entity_id=None,
        dataset_version="seed-20260406-001",
        payload={"paths": ["data/processed/crawl/tgb/10461311/articles.jsonl"]},
        source="seed-data",
        event_at=datetime(2026, 4, 6, 10, 0, tzinfo=UTC),
    )

    assert event.event_type == "seed_project_data"
    assert event.actor == "cli.seed_data"
    assert event.dataset_version == "seed-20260406-001"

    async with session_factory() as session:
        loaded = await session.get(DataAuditEvent, event.id)
        assert loaded is not None
        assert loaded.source == "seed-data"
        assert loaded.payload["paths"] == ["data/processed/crawl/tgb/10461311/articles.jsonl"]
