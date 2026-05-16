from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.config import ConfigError
from src.common.paths import resolve_project_path
from src.services.base import BaseService, ServiceResult
from src.services.config_profile_service import ConfigProfileService
from src.services.config_service import ConfigService


def _profile_to_payload(profile: Any) -> dict[str, Any]:
    """把 ORM Profile 转成稳定的 JSON payload。"""
    return {
        "profile_id": profile.profile_id,
        "name": profile.name,
        "environment": profile.environment,
        "version": profile.version,
        "sections": profile.sections,
        "secret_refs": profile.secret_refs,
        "validation_status": profile.validation_status,
        "created_by": profile.created_by,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "archived_at": profile.archived_at.isoformat() if profile.archived_at else None,
    }


class ConfigMigrationService(BaseService):
    """把旧 `config_path` 迁移到正式 Profile 的收口服务。"""

    service_name = "config-migration"

    _required_source_sections = (
        "database",
        "storage",
        "llm",
        "crawl",
        "data",
        "traders",
    )

    def __init__(
        self,
        *,
        config_service: ConfigService | None = None,
        profile_service: ConfigProfileService | None = None,
    ) -> None:
        self._config_service = config_service or ConfigService()
        self._profile_service = profile_service or ConfigProfileService(config_service=self._config_service)

    def _resolve(self, config_path: str | Path) -> Path:
        """解析配置路径。"""
        return resolve_project_path(config_path)

    def _source_keys(self, raw_config: dict[str, Any]) -> list[str]:
        """返回原始 config 中的顶层键。"""
        return sorted(str(key) for key in raw_config.keys())

    def _missing_sections(self, raw_config: dict[str, Any]) -> list[str]:
        """返回原始 config 中缺失的核心分区。"""
        return [section for section in self._required_source_sections if section not in raw_config]

    def preview_migration(
        self,
        config_path: str | Path,
        *,
        profile_id: str | None = None,
        created_by: str = "system",
        name: str | None = None,
        environment: str | None = None,
    ) -> ServiceResult:
        """预览迁移结果，包含脱敏后的配置和缺失项。"""
        resolved = self._resolve(config_path)
        if not resolved.exists():
            return ServiceResult(status="error", message="config file missing", payload={"config_path": str(resolved)})

        try:
            raw_config = self._config_service.load_raw_config(resolved)
            loaded = self._config_service.load_config(resolved)
        except ConfigError as exc:
            return ServiceResult(status="error", message=str(exc), payload={"config_path": str(resolved)})

        masked_config = self._config_service.mask_config(loaded.config.model_dump(mode="json"))
        resolved_profile_id = profile_id or resolved.stem
        missing_sections = self._missing_sections(raw_config)
        profile_environment = str(environment or raw_config.get("environment") or "default")
        validation_status = "validated" if not missing_sections else "draft"

        return ServiceResult(
            status="ok",
            message="migration preview ready",
            payload={
                "config_path": str(resolved),
                "profile_id": resolved_profile_id,
                "profile_name": name or resolved_profile_id,
                "environment": profile_environment,
                "created_by": created_by,
                "validation_status": validation_status,
                "masked_preview": masked_config,
                "source_keys": self._source_keys(raw_config),
                "required_sections": list(self._required_source_sections),
                "missing_sections": missing_sections,
                "compatibility": {
                    "legacy_entry": "config_path",
                    "canonical_target": "profile",
                    "retained": True,
                    "retire_condition": "all runtime and UI paths switch to Profile as canonical input",
                },
            },
        )

    async def migrate_config_path(
        self,
        config_path: str | Path,
        *,
        profile_id: str | None = None,
        created_by: str = "system",
        name: str | None = None,
        environment: str | None = None,
    ) -> ServiceResult:
        """把 config_path 迁移并保存为正式 Profile。"""
        preview = self.preview_migration(
            config_path,
            profile_id=profile_id,
            created_by=created_by,
            name=name,
            environment=environment,
        )
        if preview.status != "ok":
            return preview

        resolved = self._resolve(config_path)
        resolved_profile_id = str(preview.payload["profile_id"])
        profile = await self._profile_service.import_from_config_path(
            resolved,
            profile_id=resolved_profile_id,
            created_by=created_by,
            name=str(preview.payload["profile_name"]),
            environment=str(preview.payload["environment"]),
            validation_status=str(preview.payload["validation_status"]),
        )
        snapshot_result = await self._profile_service.capture_profile_snapshot(
            profile.profile_id,
            source=str(resolved),
            config_path=resolved,
        )
        if snapshot_result.status != "ok":
            return ServiceResult(
                status="error",
                message=snapshot_result.message or "profile snapshot capture failed",
                payload={
                    **preview.payload,
                    "profile": _profile_to_payload(profile),
                    "snapshot_error": snapshot_result.payload,
                },
                warnings=snapshot_result.warnings,
            )

        return ServiceResult(
            status="ok",
            message="config migrated to profile",
            payload={
                **preview.payload,
                "profile": _profile_to_payload(profile),
                "snapshot": snapshot_result.payload,
            },
        )
