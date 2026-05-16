from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.config_profile import ConfigProfile


def _build_profile_service(tmp_path: Path):
    """创建可用于 ConfigProfileService 单测的临时 SQLite 服务实例。"""
    from src.services.config_profile_service import ConfigProfileService

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'profiles.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(ConfigProfile.__table__.create)

    asyncio.run(_init_schema())

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

    service = ConfigProfileService(session_scope_factory=_session_scope, snapshot_root=tmp_path / "profile_snapshots")
    return service, engine


def test_create_default_profile(tmp_path: Path) -> None:
    """默认 Profile 应可创建。"""
    service, engine = _build_profile_service(tmp_path)

    profile = asyncio.run(service.create_default_profile(environment="dev", created_by="system"))

    assert profile.profile_id == "default"
    assert profile.environment == "dev"
    assert profile.validation_status == "draft"
    assert profile.archived_at is None

    asyncio.run(engine.dispose())


def test_import_profile_from_config_path_masks_secrets(tmp_path: Path) -> None:
    """从 config_path 导入时应脱敏并生成 secret_refs。"""
    service, engine = _build_profile_service(tmp_path)

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
environment: dev
llm:
  api_key: secret-1
database:
  url: postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai
storage:
  output_dir: data/processed
""",
        encoding="utf-8",
    )

    profile = asyncio.run(
        service.import_from_config_path(config_path, profile_id="profile-dev", created_by="system")
    )
    snapshot = asyncio.run(service.capture_profile_snapshot(profile.profile_id, job_id="job-001"))

    assert profile.profile_id == "profile-dev"
    assert profile.environment == "dev"
    assert profile.sections["llm"]["api_key"] == "***"
    assert profile.secret_refs["llm.api_key"] == "masked"
    assert profile.validation_status == "validated"
    assert snapshot.status == "ok"
    assert snapshot.payload["profile_id"] == "profile-dev"
    assert Path(snapshot.payload["profile_snapshot_path"]).exists()

    asyncio.run(engine.dispose())


def test_profile_update_and_archive_increment_version(tmp_path: Path) -> None:
    """Profile 更新与归档应提升版本并保留历史快照边界。"""
    service, engine = _build_profile_service(tmp_path)

    profile = asyncio.run(service.create_default_profile(environment="dev", created_by="system"))
    updated = asyncio.run(service.update_profile(profile.profile_id, sections={"llm": {"model": "gpt-5"}}))
    archived = asyncio.run(service.archive_profile(profile.profile_id, archived_by="admin"))

    assert updated.version == 2
    assert updated.sections["llm"]["model"] == "gpt-5"
    assert archived.archived_at is not None
    assert archived.validation_status == "archived"
    assert archived.version == 3

    asyncio.run(engine.dispose())
