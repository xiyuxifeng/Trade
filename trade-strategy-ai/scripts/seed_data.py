from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents.data_agent.skills.import_trade_logs import (
    import_trade_logs_from_csv,
    store_trade_logs,
)
from src.agents.data_agent.skills.store_db import store_articles_jsonl_to_db
from src.audit.service import AuditService, default_dataset_version
from src.common.config import AppConfig
from src.common.utils import ensure_dir


@dataclass(slots=True)
class SeedDataStats:
    """Summary of the initialization data that was imported."""

    article_jsonl_paths: list[str] = field(default_factory=list)
    trade_log_paths: list[str] = field(default_factory=list)
    article_records_read: int = 0
    articles_inserted: int = 0
    articles_updated: int = 0
    articles_skipped_duplicates: int = 0
    article_tasks_generated: int = 0
    trade_log_rows_seen: int = 0
    trade_logs_imported: int = 0

    def model_dump(self) -> dict[str, Any]:
        """Serialize the stats into a plain dictionary for CLI output."""

        return {
            "article_jsonl_paths": self.article_jsonl_paths,
            "trade_log_paths": self.trade_log_paths,
            "article_records_read": self.article_records_read,
            "articles_inserted": self.articles_inserted,
            "articles_updated": self.articles_updated,
            "articles_skipped_duplicates": self.articles_skipped_duplicates,
            "article_tasks_generated": self.article_tasks_generated,
            "trade_log_rows_seen": self.trade_log_rows_seen,
            "trade_logs_imported": self.trade_logs_imported,
        }


def _resolve_path(base_dir: Path, value: str | Path | None) -> Path | None:
    """Resolve a possibly relative path against the project root."""

    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _discover_article_jsonl_paths(*, base_dir: Path, config: AppConfig) -> list[Path]:
    """Find crawl JSONL files from configured sources or on-disk crawl output."""

    paths: list[Path] = []
    for src in config.crawl.sources:
        if not src.enabled:
            continue
        candidate = base_dir / "data" / "processed" / "crawl" / src.source / src.author_id / "articles.jsonl"
        if candidate.exists():
            paths.append(candidate)

    if paths:
        return paths

    crawl_root = base_dir / "data" / "processed" / "crawl"
    if crawl_root.exists():
        paths.extend(sorted(crawl_root.rglob("articles.jsonl")))
    return paths


def _discover_trade_log_paths(*, base_dir: Path, config: AppConfig) -> list[Path]:
    """Find configured trade log files to seed into the database."""

    paths: list[Path] = []
    for trader in config.traders:
        for raw_path in trader.trade_log_sources.csv_paths:
            path = _resolve_path(base_dir, raw_path)
            if path is not None and path.exists():
                paths.append(path)
    return paths


async def seed_project_data(
    *,
    config: AppConfig,
    base_dir: Path,
    article_jsonl_paths: list[Path] | None = None,
    trade_log_paths: list[Path] | None = None,
    audit_service: AuditService | None = None,
) -> SeedDataStats:
    """Seed the local database from crawl output and configured trade logs."""

    ensure_dir(base_dir / config.storage.output_dir)
    audit = audit_service or AuditService()
    dataset_version = default_dataset_version(prefix="seed")

    stats = SeedDataStats()
    discovered_articles = article_jsonl_paths or _discover_article_jsonl_paths(base_dir=base_dir, config=config)
    stats.article_jsonl_paths = [str(path) for path in discovered_articles]
    if discovered_articles:
        article_stats = await store_articles_jsonl_to_db(base_dir=base_dir, jsonl_paths=discovered_articles)
        stats.article_records_read = article_stats.read_records
        stats.articles_inserted = article_stats.inserted_articles
        stats.articles_updated = article_stats.updated_articles
        stats.articles_skipped_duplicates = article_stats.skipped_duplicates
        stats.article_tasks_generated = article_stats.generated_tasks

    discovered_trade_logs = trade_log_paths or _discover_trade_log_paths(base_dir=base_dir, config=config)
    stats.trade_log_paths = [str(path) for path in discovered_trade_logs]
    for path in discovered_trade_logs:
        trade_logs, trade_stats = import_trade_logs_from_csv(csv_path=path, source="seed_data")
        stats.trade_log_rows_seen += trade_stats.rows_seen
        if trade_logs:
            await store_trade_logs(trade_logs)
            stats.trade_logs_imported += len(trade_logs)

    await audit.record(
        event_type="seed_project_data",
        actor="cli.seed_data",
        entity_type="database",
        entity_id=None,
        dataset_version=dataset_version,
        payload=stats.model_dump(),
        source="seed-data",
    )

    return stats
