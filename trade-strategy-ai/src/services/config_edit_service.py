from __future__ import annotations

import copy
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable

import yaml

from src.common.config import AppConfig, load_app_config
from src.common.paths import resolve_project_path
from src.services.base import BaseService, ServiceResult
from src.services.config_service import ConfigService


def _deep_merge(base: Any, overlay: Any) -> Any:
    """递归合并配置草稿到当前配置。"""
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = copy.deepcopy(base)
        for key, value in overlay.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    return copy.deepcopy(overlay)


def _diff(before: Any, after: Any) -> Any:
    """生成递归 diff，便于前端展示保存前变化。"""
    if isinstance(before, dict) and isinstance(after, dict):
        keys = set(before) | set(after)
        result: dict[str, Any] = {}
        for key in sorted(keys):
            if key not in before:
                result[key] = {"before": None, "after": after[key]}
                continue
            if key not in after:
                result[key] = {"before": before[key], "after": None}
                continue
            nested = _diff(before[key], after[key])
            if nested is not None:
                result[key] = nested
        return result or None
    if before != after:
        return {"before": before, "after": after}
    return None


def _mask_diff(value: Any, mask_fn: Any, *, field_key: str | None = None) -> Any:
    """把 diff 结构中的值按字段名脱敏。"""
    if isinstance(value, dict):
        if set(value.keys()) <= {"before", "after"}:
            return {
                "before": _mask_diff(value.get("before"), mask_fn, field_key=field_key),
                "after": _mask_diff(value.get("after"), mask_fn, field_key=field_key),
            }
        return {key: _mask_diff(item, mask_fn, field_key=key) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_diff(item, mask_fn, field_key=field_key) for item in value]
    if field_key is None:
        return value
    return mask_fn({field_key: value})[field_key]


def _masked_equivalent(value: Any, mask_fn: Any, *, key: str | None = None) -> Any:
    """计算单个值的脱敏等价物，用于保留未修改的敏感字段。"""
    if key is None:
        return mask_fn({"value": copy.deepcopy(value)})["value"]
    return mask_fn({key: copy.deepcopy(value)})[key]


def _merge_preserving_masked_values(base: Any, overlay: Any, mask_fn: Any, *, key: str | None = None) -> Any:
    """合并草稿时保留与当前脱敏快照一致的原始敏感值。"""
    if base is not None and overlay == _masked_equivalent(base, mask_fn, key=key):
        return copy.deepcopy(base)

    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = copy.deepcopy(base)
        for key, value in overlay.items():
            merged[key] = _merge_preserving_masked_values(base.get(key), value, mask_fn, key=key)
        return merged

    if isinstance(base, list) and isinstance(overlay, list):
        if key == "api_keys" and base and len(base) == len(overlay):
            untouched = True
            for item in overlay:
                if isinstance(item, str):
                    untouched = untouched and item == "***"
                    continue
                if isinstance(item, dict):
                    untouched = untouched and item.get("key") == "***"
                    continue
                untouched = False
                break
            if untouched:
                return copy.deepcopy(base)
        if overlay == _masked_equivalent(base, mask_fn, key=key):
            return copy.deepcopy(base)
        return [
            _merge_preserving_masked_values(base[idx] if idx < len(base) else None, item, mask_fn)
            for idx, item in enumerate(overlay)
        ]

    return copy.deepcopy(overlay)


def _schema_sections(raw_config: dict[str, Any]) -> list[dict[str, Any]]:
    """把当前配置键转成 UI 可渲染的分组。"""
    sections: list[dict[str, Any]] = []
    for key, value in raw_config.items():
        sections.append(
            {
                "key": key,
                "title": key.replace("_", " ").title(),
                "summary": f"配置项：{key}",
                "type": "object" if isinstance(value, dict) else "value",
                "editable": True,
            }
        )
    return sections


def _is_within_path(path: Path, root: Path) -> bool:
    """判断路径是否位于指定根目录之下。"""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


class ConfigEditService(BaseService):
    """配置读取、验证、保存与恢复服务。"""

    service_name = "config-edit"

    def __init__(
        self,
        *,
        config_service: ConfigService | None = None,
        backup_root: str | Path | None = None,
        config_loader: Callable[[str | Path], Any] = load_app_config,
    ) -> None:
        self._config_service = config_service or ConfigService()
        self._backup_root = resolve_project_path(backup_root or "data/backups")
        self._config_loader = config_loader

    def _resolve_config_path(self, path: str | Path) -> Path:
        """解析配置路径。"""
        return resolve_project_path(path)

    def get_current_config(self, path: str | Path) -> ServiceResult:
        """返回脱敏后的当前配置。"""
        return self._load_masked_config(path)

    def get_edit_schema(self, path: str | Path) -> ServiceResult:
        """返回配置编辑 schema。"""
        return self._build_edit_schema(path)

    def validate_draft(self, path: str | Path, draft: dict[str, Any]) -> ServiceResult:
        """校验配置草稿。"""
        return self._validate_config_draft(path, draft)

    def save_config(
        self,
        path: str | Path,
        draft: dict[str, Any],
        *,
        confirmed: bool = False,
    ) -> ServiceResult:
        """保存配置。"""
        return self._save_config_with_backup(path, draft, confirmed=confirmed)

    def list_backups(self, config_path: str | Path) -> ServiceResult:
        """列出配置备份。"""
        return self._list_backups(config_path)

    def restore_backup(
        self,
        config_path: str | Path,
        backup_path: str | Path,
        *,
        confirmed: bool = False,
    ) -> ServiceResult:
        """恢复配置备份。"""
        return self._restore_backup(config_path, backup_path, confirmed=confirmed)

    def _load_raw_config(self, config_path: str | Path) -> dict[str, Any]:
        """读取原始配置。"""
        resolved = self._resolve_config_path(config_path)
        if not resolved.exists():
            return {}
        return self._config_service.load_raw_config(resolved)

    def _load_masked_config(self, config_path: str | Path) -> ServiceResult:
        """读取并脱敏配置。"""
        resolved = self._resolve_config_path(config_path)
        if not resolved.exists():
            return ServiceResult(status="error", message="config file missing", payload={"config_path": str(resolved)})

        loaded = self._config_loader(resolved)
        masked = self._config_service.mask_config(loaded.config.model_dump(mode="json"))
        return ServiceResult(
            status="ok",
            message="config loaded",
            payload={
                "config_path": str(resolved),
                "config": masked,
                "sections": _schema_sections(masked),
            },
        )

    def _build_edit_schema(self, config_path: str | Path) -> ServiceResult:
        """根据当前配置生成编辑 schema。"""
        resolved = self._resolve_config_path(config_path)
        raw_config = self._load_raw_config(resolved)
        if not raw_config:
            return ServiceResult(status="error", message="config file missing", payload={"config_path": str(resolved)})
        return ServiceResult(
            status="ok",
            message="config schema built",
            payload={
                "config_path": str(resolved),
                "sections": _schema_sections(raw_config),
            },
        )

    def _validate_config_draft(self, config_path: str | Path, draft: dict[str, Any]) -> ServiceResult:
        """校验草稿并返回脱敏 diff。"""
        resolved = self._resolve_config_path(config_path)
        current_raw = self._load_raw_config(resolved)
        merged = _merge_preserving_masked_values(current_raw, draft, self._config_service.mask_config)

        try:
            AppConfig.model_validate(merged)
        except Exception as exc:  # noqa: BLE001
            return ServiceResult(
                status="error",
                message="config draft invalid",
                payload={"config_path": str(resolved), "error": str(exc)},
            )

        masked_after = self._config_service.mask_config(merged)
        raw_diff = _diff(current_raw, merged) or {}
        diff = _mask_diff(raw_diff, self._config_service.mask_config)
        return ServiceResult(
            status="ok",
            message="config draft validated",
            payload={
                "config_path": str(resolved),
                "diff": diff,
                "masked_config": masked_after,
            },
        )

    def _backup_dir(self, config_path: Path) -> Path:
        """返回配置备份目录。"""
        return self._backup_root / config_path.stem

    def _backup_name(self, config_path: Path, *, timestamp: datetime | None = None) -> str:
        """构造备份文件名。"""
        moment = timestamp or datetime.now(UTC)
        return f"{config_path.stem}.{moment.strftime('%Y%m%d-%H%M%S')}.yaml"

    def _write_backup(self, config_path: Path, *, timestamp: datetime | None = None) -> Path:
        """把当前配置写入备份目录。"""
        backup_dir = self._backup_dir(config_path)
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / self._backup_name(config_path, timestamp=timestamp)
        if config_path.exists():
            backup_path.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            backup_path.write_text("", encoding="utf-8")
        return backup_path

    def _write_yaml(self, config_path: Path, payload: dict[str, Any]) -> None:
        """将配置以 YAML 形式写回磁盘。"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        with NamedTemporaryFile("w", encoding="utf-8", dir=config_path.parent, delete=False) as tmp_file:
            tmp_file.write(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            temp_path = Path(tmp_file.name)

        try:
            if temp_path is not None:
                os.replace(temp_path, config_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _restore_backup_content(self, config_path: Path, backup_path: Path) -> None:
        """把备份文件内容原样恢复到配置路径。"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        content = backup_path.read_text(encoding="utf-8")
        temp_path: Path | None = None
        with NamedTemporaryFile("w", encoding="utf-8", dir=config_path.parent, delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            temp_path = Path(tmp_file.name)

        try:
            if temp_path is not None:
                os.replace(temp_path, config_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _lock_path(self, config_path: Path) -> Path:
        """返回配置编辑锁路径。"""
        return self._backup_dir(config_path) / ".edit.lock"

    @contextmanager
    def _config_edit_lock(self, config_path: Path):
        """为单个配置文件建立互斥锁。"""
        lock_path = self._lock_path(config_path)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            yield None
            return

        try:
            os.write(fd, f"pid={os.getpid()}\ncreated_at={datetime.now(UTC).isoformat()}\n".encode("utf-8"))
            yield lock_path
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def _reload_advice(self, config_path: Path) -> dict[str, Any]:
        """返回保存或恢复后的重载建议。"""
        return {
            "reload_required": True,
            "reload_targets": ["api", "worker"],
            "restart_required": False,
            "restart_targets": [],
            "reload_message": f"{config_path.name} 已写入，API 和 Worker 需要重新加载配置。",
        }

    def _reload_and_validate(self, config_path: Path) -> ServiceResult:
        """保存或恢复后重新加载配置并校验文件。"""
        try:
            loaded = self._config_loader(config_path)
        except Exception as exc:  # noqa: BLE001
            return ServiceResult(
                status="error",
                message="config reload failed",
                payload={"config_path": str(config_path), "error": str(exc)},
            )

        masked = self._config_service.mask_config(loaded.config.model_dump(mode="json"))
        return ServiceResult(
            status="ok",
            message="config reloaded",
            payload={
                "config_path": str(config_path),
                "config": masked,
                **self._reload_advice(config_path),
            },
        )

    def _rollback_from_backup(self, config_path: Path, backup_path: Path) -> None:
        """把配置回滚到备份版本。"""
        self._restore_backup_content(config_path, backup_path)

    def _save_config_with_backup(
        self,
        config_path: str | Path,
        draft: dict[str, Any],
        *,
        confirmed: bool = False,
    ) -> ServiceResult:
        """保存配置前先备份当前版本。"""
        if not confirmed:
            return ServiceResult(status="error", message="confirmation required", payload={"confirmed": confirmed})

        resolved = self._resolve_config_path(config_path)
        cache_invalidated = False
        with self._config_edit_lock(resolved) as lock_path:
            if lock_path is None:
                return ServiceResult(
                    status="error",
                    message="config edit locked",
                    payload={"config_path": str(resolved), "lock_path": str(self._lock_path(resolved))},
                )

            backup_path: Path | None = None
            try:
                current_raw = self._load_raw_config(resolved)
                merged = _merge_preserving_masked_values(current_raw, draft, self._config_service.mask_config)

                try:
                    AppConfig.model_validate(merged)
                except Exception as exc:  # noqa: BLE001
                    return ServiceResult(
                        status="error",
                        message="config draft invalid",
                        payload={"config_path": str(resolved), "error": str(exc)},
                    )

                backup_path = self._write_backup(resolved)
                self._write_yaml(resolved, merged)
                cache_invalidated = True

                reloaded = self._reload_and_validate(resolved)
                if reloaded.status != "ok":
                    self._rollback_from_backup(resolved, backup_path)
                    return ServiceResult(
                        status="error",
                        message=reloaded.message or "config reload failed",
                        payload={
                            "config_path": str(resolved),
                            "backup_path": str(backup_path),
                            "error": reloaded.payload.get("error"),
                        },
                    )

                return ServiceResult(
                    status="ok",
                    message="config saved",
                    payload={
                        "config_path": str(resolved),
                        "backup_path": str(backup_path),
                        "config": reloaded.payload["config"],
                        **self._reload_advice(resolved),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                if backup_path is not None and backup_path.exists():
                    try:
                        self._rollback_from_backup(resolved, backup_path)
                    except Exception:  # noqa: BLE001
                        pass
                return ServiceResult(
                    status="error",
                    message="config save failed",
                    payload={"config_path": str(resolved), "error": str(exc)},
                )
            finally:
                if cache_invalidated:
                    try:
                        from api.dependencies import clear_cached_app_config

                        clear_cached_app_config()
                    except Exception:  # noqa: BLE001
                        pass

    def _list_backups(self, config_path: str | Path) -> ServiceResult:
        """列出某个配置的备份文件。"""
        resolved = self._resolve_config_path(config_path)
        backup_dir = self._backup_dir(resolved)
        if not backup_dir.exists():
            return ServiceResult(status="ok", message="backups listed", payload={"config_path": str(resolved), "count": 0, "items": []})

        items: list[dict[str, Any]] = []
        for backup_path in sorted(backup_dir.glob("*.yaml"), key=lambda path: path.stat().st_mtime, reverse=True):
            stat = backup_path.stat()
            items.append(
                {
                    "path": str(backup_path),
                    "name": backup_path.name,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                }
            )
        return ServiceResult(
            status="ok",
            message="backups listed",
            payload={"config_path": str(resolved), "count": len(items), "items": items},
        )

    def _restore_backup(
        self,
        config_path: str | Path,
        backup_path: str | Path,
        *,
        confirmed: bool = False,
    ) -> ServiceResult:
        """把指定备份恢复到配置文件。"""
        if not confirmed:
            return ServiceResult(status="error", message="confirmation required", payload={"confirmed": confirmed})

        resolved_config = self._resolve_config_path(config_path)
        resolved_backup = self._resolve_config_path(backup_path)
        if not resolved_backup.exists():
            return ServiceResult(
                status="error",
                message="backup file missing",
                payload={"config_path": str(resolved_config), "backup_path": str(resolved_backup)},
            )
        if not _is_within_path(resolved_backup, self._backup_root):
            return ServiceResult(
                status="error",
                message="backup path outside backup root",
                payload={"config_path": str(resolved_config), "backup_path": str(resolved_backup)},
            )

        cache_invalidated = False
        with self._config_edit_lock(resolved_config) as lock_path:
            if lock_path is None:
                return ServiceResult(
                    status="error",
                    message="config edit locked",
                    payload={"config_path": str(resolved_config), "lock_path": str(self._lock_path(resolved_config))},
                )

            current_backup: Path | None = None
            try:
                current_backup = self._write_backup(resolved_config)
                self._restore_backup_content(resolved_config, resolved_backup)
                cache_invalidated = True

                reloaded = self._reload_and_validate(resolved_config)
                if reloaded.status != "ok":
                    if current_backup is not None:
                        self._rollback_from_backup(resolved_config, current_backup)
                    return ServiceResult(
                        status="error",
                        message=reloaded.message or "config reload failed",
                        payload={
                            "config_path": str(resolved_config),
                            "backup_path": str(resolved_backup),
                            "current_backup_path": str(current_backup) if current_backup is not None else None,
                            "error": reloaded.payload.get("error"),
                        },
                    )

                return ServiceResult(
                    status="ok",
                    message="config restored",
                    payload={
                        "config_path": str(resolved_config),
                        "backup_path": str(resolved_backup),
                        "current_backup_path": str(current_backup) if current_backup is not None else None,
                        "config": reloaded.payload["config"],
                        **self._reload_advice(resolved_config),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                if current_backup is not None and current_backup.exists():
                    try:
                        self._rollback_from_backup(resolved_config, current_backup)
                    except Exception:  # noqa: BLE001
                        pass
                return ServiceResult(
                    status="error",
                    message="config restore failed",
                    payload={
                        "config_path": str(resolved_config),
                        "backup_path": str(resolved_backup),
                        "current_backup_path": str(current_backup) if current_backup is not None else None,
                        "error": str(exc),
                    },
                )
            finally:
                if cache_invalidated:
                    try:
                        from api.dependencies import clear_cached_app_config

                        clear_cached_app_config()
                    except Exception:  # noqa: BLE001
                        pass


def get_config_edit_service() -> ConfigEditService:
    """构建 settings API 使用的 ConfigEditService。"""
    return ConfigEditService()
