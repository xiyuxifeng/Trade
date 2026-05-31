from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select

from config.database import run_async_with_cleanup
from scripts.init_db import init_db
from scripts.seed_data import seed_project_data
from src.agents.data_agent.skills.import_trade_logs import (
    import_trade_logs_from_csv,
    import_trade_logs_from_excel,
    import_trade_logs_from_html,
    import_trade_logs_from_pdf,
    store_trade_logs,
)
from src.common.config import apply_database_config_to_env, load_app_config
from src.models.crawl_state import CrawlState
from src.services.config_profile_service import ConfigProfileService
from src.services.base import BaseService, ServiceResult


def _to_plain(value: Any) -> Any:
    """把 dataclass / Pydantic / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dict__"):
        attrs = vars(value)
        if attrs:
            return _to_plain(attrs)
        class_attrs = {
            key: getattr(value, key)
            for key in dir(value)
            if not key.startswith("_") and not callable(getattr(value, key))
        }
        if class_attrs:
            return _to_plain(class_attrs)
    return value


def _project_base_dir(config_path: Path) -> Path:
    """根据配置文件推导项目根目录。"""
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


async def _await_if_needed(value: Any) -> Any:
    """兼容同步与异步返回值。"""
    if inspect.isawaitable(value):
        return await value
    return value


class SetupService(BaseService):
    """初始化、导入与基础迁移服务。"""

    service_name = "setup"

    def __init__(
        self,
        *,
        load_config_runner: Callable[[str | Path], Any] = load_app_config,
        apply_database_config_runner: Callable[[Any], None] = apply_database_config_to_env,
        seed_runner: Callable[..., Any] = seed_project_data,
        init_db_runner: Callable[..., Any] = init_db,
        csv_importer: Callable[..., Any] = import_trade_logs_from_csv,
        excel_importer: Callable[..., Any] = import_trade_logs_from_excel,
        html_importer: Callable[..., Any] = import_trade_logs_from_html,
        pdf_importer: Callable[..., Any] = import_trade_logs_from_pdf,
        store_trade_logs_runner: Callable[..., Any] = store_trade_logs,
        crawl_state_writer: Callable[..., Any] | None = None,
    ) -> None:
        self._load_config_runner = load_config_runner
        self._apply_database_config_runner = apply_database_config_runner
        self._seed_runner = seed_runner
        self._init_db_runner = init_db_runner
        self._csv_importer = csv_importer
        self._excel_importer = excel_importer
        self._html_importer = html_importer
        self._pdf_importer = pdf_importer
        self._store_trade_logs_runner = store_trade_logs_runner
        self._crawl_state_writer = crawl_state_writer or self._default_crawl_state_writer

    def _load_config(self, config_path: str | Path):
        """读取配置并同步数据库环境变量。"""
        loaded = self._load_config_runner(config_path)
        self._apply_database_config_runner(loaded.config)
        return loaded

    async def _load_runtime_context(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """加载 Web/CLI 运行时配置。

        Web 主路径优先使用 Profile runtime；CLI 调试保留 config_path。
        """
        resolved_profile_id = str(profile_id).strip() if isinstance(profile_id, str) and profile_id.strip() else None
        if resolved_profile_id is not None:
            runtime = await ConfigProfileService().load_profile_runtime_config(resolved_profile_id)
            self._apply_database_config_runner(runtime.config)
            return {
                "profile_id": runtime.profile_id,
                "profile_snapshot_id": runtime.profile_snapshot_id,
                "config_path": None,
                "config": runtime.config,
                "base_dir": runtime.base_dir,
            }

        resolved_config_path = config_path or Path("config/app.yaml")
        loaded = self._load_config(resolved_config_path)
        return {
            "profile_id": None,
            "profile_snapshot_id": None,
            "config_path": str(loaded.config_path),
            "config": loaded.config,
            "base_dir": _project_base_dir(loaded.config_path),
        }

    async def _default_crawl_state_writer(
        self,
        *,
        base_dir: Path,
        source: str,
        author_id: str,
        state_data: dict[str, Any],
    ) -> bool:
        """默认 crawl state 持久化实现。"""
        from src.db.session import session_scope

        async with session_scope() as session:
            result = await session.execute(
                select(CrawlState).where(
                    CrawlState.source == source,
                    CrawlState.author_id == author_id,
                )
            )
            existing = result.scalar_one_or_none()
            seen_urls = state_data.get("seen_urls", [])
            seen_hashes = state_data.get("seen_hashes", [])
            last_url = state_data.get("last_seen_article_url")
            last_published = state_data.get("last_seen_published_at")
            if existing is None:
                session.add(
                    CrawlState(
                        source=source,
                        author_id=author_id,
                        seen_urls=seen_urls,
                        seen_hashes=seen_hashes,
                        last_seen_article_url=last_url,
                        last_seen_published_at=datetime.fromisoformat(last_published) if last_published else None,
                        last_success_article_count=state_data.get("last_success_article_count", 0),
                    )
                )
            else:
                if len(existing.seen_urls or []) < len(seen_urls):
                    existing.seen_urls = seen_urls
                    existing.seen_hashes = seen_hashes
                    existing.last_seen_article_url = last_url
                    existing.last_seen_published_at = datetime.fromisoformat(last_published) if last_published else None
                    existing.last_success_article_count = state_data.get("last_success_article_count", 0)
            await session.commit()
        del base_dir
        return True

    def init_config(self, *, dest: str | Path, force: bool = False) -> ServiceResult:
        """生成默认配置模板。"""
        from src.services.config_service import ConfigService

        return ConfigService().write_default_template(dest, force=force)

    async def seed_data(self, *, config_path: str | Path) -> ServiceResult:
        """导入样例文章和交易记录。"""
        loaded = self._load_config(config_path)
        base_dir = _project_base_dir(loaded.config_path)
        stats = await _await_if_needed(self._seed_runner(config=loaded.config, base_dir=base_dir))
        return ServiceResult(
            status="ok",
            message="seed data completed",
            payload={
                "config_path": str(loaded.config_path),
                "base_dir": str(base_dir),
                "stats": _to_plain(stats),
            },
        )

    async def init_project(self, *, config_path: str | Path) -> ServiceResult:
        """执行迁移并导入样例数据。"""
        loaded = self._load_config(config_path)
        base_dir = _project_base_dir(loaded.config_path)
        self._init_db_runner(project_root=base_dir)
        stats = await _await_if_needed(self._seed_runner(config=loaded.config, base_dir=base_dir))
        return ServiceResult(
            status="ok",
            message="project initialization completed",
            payload={
                "config_path": str(loaded.config_path),
                "base_dir": str(base_dir),
                "stats": _to_plain(stats),
            },
        )

    async def import_trade_logs(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
        csv_path: str | Path,
        source: str = "csv_import",
        trader_account_map: dict[str, str] | None = None,
        dry_run: bool = False,
    ) -> ServiceResult:
        """导入交易记录。"""
        runtime = await self._load_runtime_context(profile_id=profile_id, config_path=config_path)
        csv_file = Path(csv_path)
        suffix = csv_file.suffix.lower()

        if suffix in {".xlsx", ".xlsm", ".xls"}:
            records, stats = self._excel_importer(
                xlsx_path=csv_file,
                source=source,
                trader_account_map=trader_account_map,
            )
            file_kind = "excel"
        elif suffix in {".html", ".htm"}:
            records, stats = self._html_importer(
                html_path=csv_file,
                source=source,
                trader_account_map=trader_account_map,
            )
            file_kind = "html"
        elif suffix == ".pdf":
            records, stats = self._pdf_importer(
                pdf_path=csv_file,
                source=source,
                trader_account_map=trader_account_map,
            )
            file_kind = "pdf"
        else:
            records, stats = self._csv_importer(
                csv_path=csv_file,
                source=source,
                trader_account_map=trader_account_map,
            )
            file_kind = "csv"

        stored_count = 0
        if not dry_run:
            stored_count = await _await_if_needed(self._store_trade_logs_runner(records))

        issues = []
        for issue in getattr(stats, "issues", []):
            issues.append(
                {
                    "severity": getattr(getattr(issue, "severity", None), "value", getattr(issue, "severity", None)),
                    "code": getattr(issue, "code", None),
                    "message": getattr(issue, "message", None),
                }
            )

        payload: dict[str, Any] = {
            "profile_id": runtime["profile_id"],
            "profile_snapshot_id": runtime["profile_snapshot_id"],
            "base_dir": str(runtime["base_dir"]),
            "csv_path": str(csv_file),
            "file_kind": file_kind,
            "source": source,
            "rows_seen": getattr(stats, "rows_seen", 0),
            "invalid": getattr(stats, "invalid", 0),
            "duplicates": getattr(stats, "duplicates", 0),
            "issues": issues,
            "parsed_count": len(records),
            "stored_count": stored_count,
            "dry_run": dry_run,
        }
        if runtime["config_path"] is not None:
            payload["config_path"] = runtime["config_path"]
        return ServiceResult(
            status="ok",
            message="trade logs imported" if not dry_run else "trade logs parsed",
            payload=payload,
        )

    async def migrate_crawl_state(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
    ) -> ServiceResult:
        """将 crawl state.json 迁移到数据库。"""
        runtime = await self._load_runtime_context(profile_id=profile_id, config_path=config_path)
        base_dir = Path(runtime["base_dir"])
        migrated = 0
        skipped = 0
        results: list[dict[str, Any]] = []

        for source_cfg in runtime["config"].crawl.sources:
            if not source_cfg.enabled:
                continue
            state_path = base_dir / "data" / "processed" / "crawl" / source_cfg.source / source_cfg.author_id / "state.json"
            if not state_path.exists():
                skipped += 1
                results.append(
                    {
                        "source": source_cfg.source,
                        "author_id": source_cfg.author_id,
                        "status": "skipped",
                        "reason": "state.json missing",
                    }
                )
                continue

            state_data = json.loads(state_path.read_text(encoding="utf-8"))
            ok = await _await_if_needed(
                self._crawl_state_writer(
                    base_dir=base_dir,
                    source=source_cfg.source,
                    author_id=source_cfg.author_id,
                    state_data=state_data,
                )
            )
            if ok:
                migrated += 1
                results.append(
                    {
                        "source": source_cfg.source,
                        "author_id": source_cfg.author_id,
                        "status": "migrated",
                        "urls": len(state_data.get("seen_urls", [])),
                        "hashes": len(state_data.get("seen_hashes", [])),
                    }
                )
            else:
                skipped += 1
                results.append(
                    {
                        "source": source_cfg.source,
                        "author_id": source_cfg.author_id,
                        "status": "skipped",
                        "reason": "writer returned false",
                    }
                )

        payload: dict[str, Any] = {
            "profile_id": runtime["profile_id"],
            "profile_snapshot_id": runtime["profile_snapshot_id"],
            "base_dir": str(base_dir),
            "migrated": migrated,
            "skipped": skipped,
            "results": results,
        }
        if runtime["config_path"] is not None:
            payload["config_path"] = runtime["config_path"]
        return ServiceResult(
            status="ok" if skipped == 0 else "partial",
            message="crawl state migrated" if skipped == 0 else "crawl state migrated partially",
            payload=payload,
        )
