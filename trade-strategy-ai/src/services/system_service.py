from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.common.config import load_app_config
from src.health.db_checker import DatabaseHealthChecker
from src.services.base import BaseService, ServiceResult


class SystemService(BaseService):
    """系统与环境相关服务的占位基类。

    后续用于统一承载数据库检查、迁移、目录检查与调度状态查询。
    """

    service_name = "system"

    def __init__(self, db_checker: DatabaseHealthChecker | None = None) -> None:
        self._db_checker = db_checker or DatabaseHealthChecker()

    async def check_database(self) -> ServiceResult:
        """检查数据库连接状态。"""
        check = await self._db_checker.check()
        ok = check.status.value == "ok"
        return ServiceResult(
            status="ok" if ok else "error",
            message="database ok" if ok else "database failed",
            payload={"database": asdict(check)},
        )

    def check_key_directories(self, config_path: str | Path) -> ServiceResult:
        """检查配置相关的关键目录是否存在。"""
        loaded = load_app_config(config_path)
        config_file = Path(config_path).expanduser().resolve()
        base_dir = config_file.parent.parent if config_file.parent.name == "config" else config_file.parent

        directory_specs: dict[str, Path] = {
            "data": base_dir / "data",
            "logs": base_dir / "logs",
            "storage.output_dir": base_dir / loaded.config.storage.output_dir,
            "data.market_data_cache_dir": base_dir / loaded.config.data.market_data_cache_dir,
            "data.market_universe_snapshot_dir": base_dir / loaded.config.data.market_universe_snapshot_dir,
        }

        directories: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        for name, directory in directory_specs.items():
            exists = directory.exists()
            directories[name] = {"path": str(directory), "exists": exists}
            if not exists:
                missing.append(name)

        status = "ok" if not missing else "partial"
        message = "directories ok" if not missing else "some directories are missing"
        return ServiceResult(
            status=status,
            message=message,
            payload={
                "base_dir": str(base_dir),
                "config_path": str(config_file),
                "directories": directories,
            },
            warnings=missing,
        )
