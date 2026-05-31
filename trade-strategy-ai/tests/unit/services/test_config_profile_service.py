from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.common.paths import project_root
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


def test_load_profile_runtime_config_clears_masked_secrets(tmp_path: Path) -> None:
    """Profile 运行态应清空已脱敏字段，避免把 `***` 当成真实 secret 运行。"""
    service, engine = _build_profile_service(tmp_path)

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
database:
  url: postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai
  echo: true
llm:
  provider: qwen
  model: ["qwen3-8b"]
  url: https://dashscope.aliyuncs.com/compatible-mode/v1
  api_key: secret-1
""",
        encoding="utf-8",
    )

    profile = asyncio.run(service.import_from_config_path(config_path, profile_id="profile-runtime", created_by="system"))
    runtime = asyncio.run(service.load_profile_runtime_config(profile.profile_id))

    assert runtime.profile_id == "profile-runtime"
    assert runtime.base_dir == project_root().resolve()
    assert runtime.config.llm.provider == "qwen"
    assert runtime.config.llm.model == ["qwen3-8b"]
    assert runtime.config.llm.api_key is None
    assert runtime.config.database.url is None
    assert runtime.profile_snapshot_id is not None

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


def test_profile_edit_payload_and_save_create_new_version_without_overwriting_history(tmp_path: Path) -> None:
    """编辑保存应生成新版本，并保留旧快照文件不变。"""
    service, engine = _build_profile_service(tmp_path)

    profile = asyncio.run(service.create_default_profile(environment="dev", created_by="system"))
    original_snapshot = asyncio.run(service.capture_profile_snapshot(profile.profile_id, job_id="job-001"))
    original_snapshot_path = Path(original_snapshot.payload["profile_snapshot_path"])
    original_snapshot_content = original_snapshot_path.read_text(encoding="utf-8")

    edit_payload = asyncio.run(service.build_profile_edit_payload(profile.profile_id))
    assert edit_payload.status == "ok"
    assert edit_payload.payload["validation"]["valid"] is True
    assert edit_payload.payload["validation"]["next_version"] == 2
    assert edit_payload.payload["section_guide"] == []

    saved = asyncio.run(
        service.save_profile_update(
            profile.profile_id,
            {
                "name": "默认配置",
                "environment": "dev",
                "sections": {"app": {"timezone": "Asia/Shanghai"}},
            },
            created_by="web",
        )
    )

    assert saved.status == "ok"
    assert saved.payload["profile"]["version"] == 2
    assert saved.payload["snapshot"]["profile_id"] == profile.profile_id
    assert original_snapshot_path.exists()
    assert original_snapshot_path.read_text(encoding="utf-8") == original_snapshot_content

    asyncio.run(engine.dispose())


def test_save_profile_update_rolls_back_when_snapshot_write_fails(tmp_path: Path) -> None:
    """保存更新时若快照写失败，应回滚 Profile 修改。"""
    service, engine = _build_profile_service(tmp_path)
    service._persist_snapshot_payload = lambda payload: (_ for _ in ()).throw(RuntimeError("snapshot failed"))  # type: ignore[method-assign]

    profile = asyncio.run(service.create_default_profile(environment="dev", created_by="system"))
    result = asyncio.run(
        service.save_profile_update(
            profile.profile_id,
            {
                "name": "新名称",
                "environment": "dev",
                "sections": {"app": {"timezone": "Asia/Shanghai"}},
            },
            created_by="web",
        )
    )
    persisted = asyncio.run(service.get_profile(profile.profile_id))

    assert result is None or result.status != "ok"
    assert persisted is not None
    assert persisted.name == "Default Profile"
    assert persisted.version == 1

    asyncio.run(engine.dispose())


def test_profile_edit_payload_keeps_existing_sections_when_missing(tmp_path: Path) -> None:
    """编辑草稿未传 sections 时，应继续沿用现有 sections。"""
    service, engine = _build_profile_service(tmp_path)

    profile = asyncio.run(service.create_default_profile(environment="dev", created_by="system"))
    asyncio.run(service.update_profile(profile.profile_id, sections={"app": {"timezone": "Asia/Shanghai"}}))
    edited = asyncio.run(
        service.build_profile_edit_payload(
            profile.profile_id,
            {
                "name": "默认配置-2",
                "environment": "dev",
            },
        )
    )

    assert edited.status == "ok"
    assert edited.payload["draft"]["sections"] == {"app": {"timezone": "Asia/Shanghai"}}
    assert edited.payload["validation"]["valid"] is True

    asyncio.run(engine.dispose())
