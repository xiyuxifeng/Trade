from __future__ import annotations

import yaml
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from typing import Any

from src.common.config import LoadedConfig, load_app_config
from src.services.base import BaseService, ServiceResult
from src.services.defaults import DEFAULT_CONFIG_YAML


_SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "api_keys", "cookie"}


class ConfigService(BaseService):
    """配置相关服务的占位基类。

    后续用于统一承载配置读取、脱敏展示、模板生成与保存校验逻辑。
    """

    service_name = "config"

    def load_config(self, path: str | Path) -> LoadedConfig:
        """读取并解析配置文件。"""
        return load_app_config(path)

    def load_raw_config(self, path: str | Path) -> dict[str, Any]:
        """读取配置文件的原始 YAML 内容。"""
        config_path = Path(path).expanduser().resolve()
        with config_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def check_config_file(self, path: str | Path) -> ServiceResult:
        """检查配置文件是否存在。"""
        config_path = Path(path).expanduser().resolve()
        exists = config_path.exists()
        return ServiceResult(
            status="ok" if exists else "error",
            message="config file exists" if exists else "config file missing",
            payload={"path": str(config_path), "exists": exists},
        )

    def write_default_template(self, dest: str | Path, *, force: bool = False) -> ServiceResult:
        """写入默认配置模板。"""
        dest_path = Path(dest).expanduser().resolve()
        if dest_path.exists() and not force:
            return ServiceResult(
                status="error",
                message="config already exists",
                payload={"path": str(dest_path), "written": False, "exists": True},
                warnings=[f"config already exists: {dest_path}"],
            )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(DEFAULT_CONFIG_YAML.replace("\t", "  "), encoding="utf-8")
        return ServiceResult(
            status="ok",
            message="config template written",
            payload={"path": str(dest_path), "written": True, "exists": dest_path.exists()},
        )

    def mask_config(self, data: dict[str, Any]) -> dict[str, Any]:
        """递归脱敏配置数据。"""

        def _mask_url(value: str) -> str:
            """脱敏 URL 中的明文密码。"""
            parsed = urlsplit(value)
            if not parsed.scheme or parsed.password is None:
                return value

            host = parsed.hostname or ""
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"

            netloc = ""
            if parsed.username:
                netloc += parsed.username
                netloc += ":***"
                netloc += "@"
            netloc += host
            if parsed.port is not None:
                netloc += f":{parsed.port}"

            return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

        def _mask(value: Any, key: str | None = None) -> Any:
            if isinstance(value, dict):
                return {k: _mask(v, k) for k, v in value.items()}
            if isinstance(value, list):
                return [_mask(item, key) for item in value]
            if value is None:
                return None
            if isinstance(value, str) and not value.strip():
                return value
            if key is not None and key.lower() in _SENSITIVE_KEYS:
                return "***"
            if key is not None and key.lower() == "url" and isinstance(value, str):
                return _mask_url(value)
            return value

        return _mask(data)
