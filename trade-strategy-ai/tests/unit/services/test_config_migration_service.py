from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.config_profile import ConfigProfile


def _build_profile_service(tmp_path: Path):
    """构造用于迁移服务单测的临时 Profile 服务。"""
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


class _FailingSnapshotProfileService:
    async def import_from_config_path(
        self,
        config_path,
        *,
        profile_id,
        created_by,
        name=None,
        environment=None,
        validation_status=None,
    ):
        del config_path, profile_id, created_by, name, environment, validation_status
        from types import SimpleNamespace

        return SimpleNamespace(
            profile_id="profile-dev",
            name="profile-dev",
            environment="dev",
            version=1,
            sections={"llm": {"api_key": "***"}},
            secret_refs={"llm.api_key": "masked"},
            validation_status="draft",
            created_by="tester",
            created_at=None,
            updated_at=None,
            archived_at=None,
        )

    async def capture_profile_snapshot(self, profile_id: str, *, job_id: str | None = None):
        del profile_id, job_id
        from src.services.base import ServiceResult

        return ServiceResult(status="error", message="snapshot failed", payload={"reason": "boom"})


def test_preview_migration_reports_missing_sections_and_masks_preview(tmp_path: Path) -> None:
    """迁移预览应展示缺失项并脱敏输出。"""
    from src.services.config_migration_service import ConfigMigrationService

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
environment: dev
storage:
  output_dir: data/processed
llm:
  api_key: secret-1
""",
        encoding="utf-8",
    )

    service = ConfigMigrationService()
    result = service.preview_migration(config_path, profile_id="profile-dev", created_by="tester")

    assert result.status == "ok"
    assert result.payload["profile_id"] == "profile-dev"
    assert result.payload["validation_status"] == "draft"
    assert "database" in result.payload["missing_sections"]
    assert "crawl" in result.payload["missing_sections"]
    assert result.payload["masked_preview"]["llm"]["api_key"] == "***"
    assert result.payload["compatibility"]["legacy_entry"] == "config_path"


def test_migrate_config_path_saves_profile_and_snapshot(tmp_path: Path) -> None:
    """迁移保存时应写入 Profile 和 snapshot。"""
    from src.services.config_migration_service import ConfigMigrationService

    profile_service, engine = _build_profile_service(tmp_path)
    service = ConfigMigrationService(profile_service=profile_service)

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
environment: dev
storage:
  output_dir: data/processed
llm:
  api_key: secret-1
""",
        encoding="utf-8",
    )

    result = asyncio.run(
        service.migrate_config_path(
            config_path,
            profile_id="profile-dev",
            created_by="tester",
        )
    )

    assert result.status == "ok"
    assert result.payload["profile"]["profile_id"] == "profile-dev"
    assert result.payload["profile"]["validation_status"] == "draft"
    assert result.payload["profile"]["sections"]["llm"]["api_key"] == "***"
    assert Path(result.payload["snapshot"]["snapshot_path"]).exists()

    asyncio.run(engine.dispose())


def test_migrate_config_path_surfaces_snapshot_failure_without_crashing(tmp_path: Path) -> None:
    """迁移过程中 snapshot 失败时应返回错误，而不是二次异常。"""
    from src.services.config_migration_service import ConfigMigrationService

    service = ConfigMigrationService(profile_service=_FailingSnapshotProfileService())

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
environment: dev
storage:
  output_dir: data/processed
llm:
  api_key: secret-1
""",
        encoding="utf-8",
    )

    result = asyncio.run(
        service.migrate_config_path(
            config_path,
            profile_id="profile-dev",
            created_by="tester",
        )
    )

    assert result.status == "error"
    assert result.message == "snapshot failed"
    assert result.payload["profile"]["profile_id"] == "profile-dev"
    assert result.payload["snapshot_error"]["reason"] == "boom"
