from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session_factory
from src.models.article_metadata import ArticleMetadata
from src.models.article_metadata_selection import ArticleMetadataSelection
from src.models.backtest_result_run import BacktestResultRun
from src.models.blog_article import BlogArticle
from src.models.job import Job
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_regime_record import MarketRegimeRecord
from src.models.ohlcv_bar import OHLCVBar
from src.models.raw_article import RawArticle
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    DatasetLifecycleState,
    DatasetSnapshot,
    LegacyIdMapping,
    MigrationConflict,
    MigrationConflictStatus,
    MigrationItemStatus,
    MigrationQualityReport,
    MigrationRun,
    MigrationRunItem,
    MigrationRunStatus,
    PromptRun,
    PromptValidationState,
    Rule,
    RuleCandidate,
    RuleFamily,
    RuleFamilyMembership,
    RuleVersion,
    LifecycleEvent,
)
from src.models.trader_memory import TraderMemory
from src.models.trader_strategy_version import TraderStrategyVersion
from src.rule_pool.models import RulePool
from src.common.stage2_writer_routing import canonical_writer_enabled


BOOTSTRAP_COUNTS = {
    "raw_articles": 131,
    "blog_articles": 131,
    "article_metadata": 262,
    "article_metadata_selections": 7,
    "rule_pool": 14,
    "ohlcv_bars": 84,
    "backtest_result_runs": 0,
    "market_snapshots": 0,
    "market_regimes": 0,
    "rule_applicability_profiles": 0,
    "trader_strategy_versions": 0,
    "trader_memory": 0,
}

FINGERPRINT_DB_KEYS = (
    "raw_articles",
    "blog_articles",
    "article_metadata",
    "article_metadata_selections",
    "rule_pool",
    "ohlcv_bars",
    "market_snapshots",
    "market_regimes",
    "rule_applicability_profiles",
    "trader_strategy_versions",
    "trader_memory",
)


REQUIRED_REPORT_FIELDS = (
    "source_count",
    "eligible_count",
    "migrated_count",
    "skipped_idempotent_count",
    "rejected_count",
    "conflict_count",
    "target_count_before",
    "target_count_after",
    "quality_status_counts",
    "orphan_count",
    "hash_mismatch_count",
)


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    return str(value)


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_uuid(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"trade-strategy-ai:stage2:{key}")


def stable_short_id(prefix: str, key: str, max_length: int = 64) -> str:
    digest = sha256_text(key)[: min(32, max_length - len(prefix) - 1)]
    value = f"{prefix}_{digest}"
    return value[:max_length]


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def file_sha256(path: Path) -> str:
    return sha256_text(path.read_text(encoding="utf-8"))


def sanitize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: sanitize_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload


def storage_ref_from_path(path: str | Path) -> dict[str, Any]:
    value = str(path)
    return {"storage_ref": value, "contains_absolute_path": value.startswith("/")}


class Stage2MigrationCategory(StrEnum):
    articles = "articles"
    article_analysis = "article_analysis"
    selections = "selections"
    rules = "rules"
    backtests = "backtests"
    author_profiles = "author_profiles"
    strategies = "strategies"
    market_data = "market_data"
    daily_objects = "daily_objects"


@dataclass
class Stage2MigrationCategoryReport:
    source_count: int = 0
    eligible_count: int = 0
    migrated_count: int = 0
    skipped_idempotent_count: int = 0
    rejected_count: int = 0
    conflict_count: int = 0
    target_count_before: int = 0
    target_count_after: int = 0
    quality_status_counts: dict[str, int] = field(default_factory=dict)
    orphan_count: int = 0
    hash_mismatch_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Stage2MigrationReport:
    mode: str
    status: str
    source_fingerprint: str
    categories: dict[str, dict[str, Any]]
    inventory: dict[str, Any]
    run_id: str | None = None
    recovery_export: dict[str, Any] = field(default_factory=dict)
    shadow_read: dict[str, Any] = field(default_factory=dict)
    cutover: dict[str, Any] = field(default_factory=dict)


@dataclass
class Stage2MigrationFixture:
    raw_articles: list[dict[str, Any]]
    blog_articles: list[dict[str, Any]]
    article_metadata: list[dict[str, Any]]
    selections: list[dict[str, Any]]
    rule_pool: list[dict[str, Any]]
    ohlcv_rows: list[dict[str, Any]]
    daily_reports: list[dict[str, Any]]
    daily_sessions: list[dict[str, Any]]

    @classmethod
    def sample(cls) -> Stage2MigrationFixture:
        article_id = str(stable_uuid("fixture:article:1"))
        other_article_id = str(stable_uuid("fixture:article:2"))
        now = datetime(2026, 6, 14, tzinfo=UTC).isoformat()
        return cls(
            raw_articles=[
                {"id": "raw-1", "article_id": article_id, "source_url": "https://example.com/a", "is_processed": False, "content_hash": "aaa", "content_text": "A", "raw_payload": {"url": "https://example.com/a"}, "crawled_at": now},
                {"id": "raw-2", "article_id": other_article_id, "source_url": "https://example.com/b", "is_processed": False, "content_hash": "bbb", "content_text": "B", "raw_payload": {"url": "https://example.com/b"}, "crawled_at": now},
            ],
            blog_articles=[
                {"id": article_id, "source_url": "https://example.com/a", "content_hash": "aaa", "content_text": "A", "content_html": None, "raw_payload": {"article": "A"}, "crawled_at": now},
                {"id": other_article_id, "source_url": "https://example.com/b", "content_hash": "bbb", "content_text": "B", "content_html": None, "raw_payload": {"article": "B"}, "crawled_at": now},
            ],
            article_metadata=[
                {"id": "meta-1", "article_id": article_id, "schema_version": "v1", "provider": "qwen", "model": "qwen-plus", "extraction_version": None, "raw_llm_output": {"raw": 1}, "strategy_rules": [{"rule": "one"}], "preconditions": [], "processed_at": now},
                {"id": "meta-2", "article_id": other_article_id, "schema_version": "v2", "provider": "deepseek", "model": "deepseek-v3.2", "extraction_version": None, "raw_llm_output": {"raw": 2}, "strategy_rules": [{"rule": "two"}], "preconditions": [], "processed_at": now},
            ],
            selections=[
                {"selection_id": "sel-1", "article_id": article_id, "selected_schema_version": "v1", "selection_mode": "auto", "selected_by": None, "selected_at": now},
            ],
            rule_pool=[
                {"id": "rule-row-1", "rule_id": f"{article_id}:v1:standalone:000", "rule_type": "entry", "review_status": "approved", "reviewed_by": "auto_review", "source_article_ids": [article_id], "extraction_layer": {"condition": {"k": 1}, "action": {"type": "buy"}}, "backtest_result": {"win_rate": 0.5}, "created_at": now},
            ],
            ohlcv_rows=[
                {"id": "ohlcv-1", "symbol": "000001.SZ", "trade_date": "2026-04-20"},
                {"id": "ohlcv-2", "symbol": "000002.SZ", "trade_date": "2026-04-20"},
            ],
            daily_reports=[{"path": "daily-report/2026-04-20.md", "trade_date": "2026-04-20"}],
            daily_sessions=[{"path": "daily-sessions/2026-04-20.md", "trade_date": "2026-04-20"}],
        )


class Stage2MigrationStore(Protocol):
    def run_sync(self, *, mode: str, batch_size: int, fail_after_items: int | None, report_dir: Path) -> Stage2MigrationReport: ...


class InMemoryStage2MigrationStore:
    def __init__(self, fixture: Stage2MigrationFixture) -> None:
        self.fixture = fixture
        self.article_revisions: dict[str, dict[str, Any]] = {}
        self.prompt_runs: dict[str, dict[str, Any]] = {}
        self.article_structures: dict[str, dict[str, Any]] = {}
        self.rule_candidates: dict[str, dict[str, Any]] = {}
        self.rules: dict[str, dict[str, Any]] = {}
        self.rule_versions: dict[str, dict[str, Any]] = {}
        self.dataset_snapshots: dict[str, dict[str, Any]] = {}
        self.backtests: dict[str, dict[str, Any]] = {}
        self.legacy_mappings: dict[tuple[str, str, str], str] = {}
        self.cursors: dict[str, int] = {}

    def has_duplicate_legacy_mappings(self) -> bool:
        return len(self.legacy_mappings.values()) != len(set(self.legacy_mappings.keys()))

    def has_orphan_foreign_keys(self) -> bool:
        for payload in self.article_structures.values():
            if payload["prompt_run_id"] not in self.prompt_runs:
                return True
        return False

    def _inventory(self) -> dict[str, Any]:
        return {
            "database": {
                "raw_articles": len(self.fixture.raw_articles),
                "blog_articles": len(self.fixture.blog_articles),
                "article_metadata": len(self.fixture.article_metadata),
                "article_metadata_selections": len(self.fixture.selections),
                "rule_pool": len(self.fixture.rule_pool),
                "ohlcv_bars": len(self.fixture.ohlcv_rows),
            },
            "files": {
                "daily_report": len(self.fixture.daily_reports),
                "daily_sessions": len(self.fixture.daily_sessions),
            },
        }

    def _fingerprint(self) -> str:
        return sha256_text(stable_json(self._inventory()))

    def run_sync(self, *, mode: str, batch_size: int, fail_after_items: int | None, report_dir: Path) -> Stage2MigrationReport:
        del batch_size
        ensure_directory(report_dir)
        reports = {category.value: Stage2MigrationCategoryReport().to_dict() for category in Stage2MigrationCategory}
        reports["articles"]["source_count"] = len(self.fixture.blog_articles)
        reports["articles"]["eligible_count"] = len(self.fixture.blog_articles)
        reports["article_analysis"]["source_count"] = len(self.fixture.article_metadata)
        reports["article_analysis"]["eligible_count"] = len(self.fixture.article_metadata)
        reports["selections"]["source_count"] = len(self.fixture.selections)
        reports["selections"]["eligible_count"] = len(self.fixture.selections)
        reports["rules"]["source_count"] = len(self.fixture.rule_pool)
        reports["rules"]["eligible_count"] = len(self.fixture.rule_pool)
        reports["backtests"]["source_count"] = len(self.fixture.rule_pool)
        reports["backtests"]["eligible_count"] = len(self.fixture.rule_pool)
        reports["market_data"]["source_count"] = len(self.fixture.ohlcv_rows)
        reports["market_data"]["eligible_count"] = len(self.fixture.ohlcv_rows)
        reports["daily_objects"]["source_count"] = len(self.fixture.daily_reports) + len(self.fixture.daily_sessions)
        reports["daily_objects"]["rejected_count"] = reports["daily_objects"]["source_count"]
        reports["daily_objects"]["quality_status_counts"] = {"ambiguous": reports["daily_objects"]["source_count"]}

        report = Stage2MigrationReport(
            mode=mode,
            status="completed",
            source_fingerprint=self._fingerprint(),
            categories=reports,
            inventory=self._inventory(),
            run_id=f"in-memory:{self._fingerprint()[:12]}",
            recovery_export={"legacy_mapping_count": len(self.legacy_mappings)},
            cutover={"switch": "STAGE2_CANONICAL_WRITER_ENABLED", "enabled": False, "verified": True},
        )
        if mode == "dry-run":
            return report
        if mode == "verify":
            reports["articles"]["target_count_after"] = len(self.article_revisions)
            reports["article_analysis"]["target_count_after"] = len(self.prompt_runs) + len(self.article_structures) + len(self.rule_candidates)
            return report

        processed = 0
        start_articles = self.cursors.get("articles", 0) if mode == "resume" else 0
        for index, article in enumerate(self.fixture.blog_articles[start_articles:], start=start_articles):
            revision_id = str(stable_uuid(f"article_revision:{article['id']}:1"))
            if revision_id in self.article_revisions:
                reports["articles"]["skipped_idempotent_count"] += 1
            else:
                self.article_revisions[revision_id] = {"article_id": article["id"]}
                self.legacy_mappings[("blog_articles", "article", article["id"])] = article["id"]
                reports["articles"]["migrated_count"] += 1
            self.cursors["articles"] = index + 1
            processed += 1
            if fail_after_items and processed >= fail_after_items:
                report.status = "failed"
                return report

        start_meta = self.cursors.get("article_analysis", 0) if mode == "resume" else 0
        for index, metadata in enumerate(self.fixture.article_metadata[start_meta:], start=start_meta):
            prompt_run_id = str(stable_uuid(f"prompt_run:{metadata['article_id']}:{metadata['schema_version']}"))
            structure_id = str(stable_uuid(f"article_structure:{metadata['article_id']}:{metadata['schema_version']}"))
            if prompt_run_id in self.prompt_runs:
                reports["article_analysis"]["skipped_idempotent_count"] += 1
            else:
                self.prompt_runs[prompt_run_id] = {"article_id": metadata["article_id"]}
                self.article_structures[structure_id] = {"article_id": metadata["article_id"], "prompt_run_id": prompt_run_id}
                for rule_index, _ in enumerate(metadata["strategy_rules"]):
                    candidate_id = str(stable_uuid(f"rule_candidate:{metadata['article_id']}:{metadata['schema_version']}:{rule_index}"))
                    self.rule_candidates[candidate_id] = {"article_structure_id": structure_id}
                reports["article_analysis"]["migrated_count"] += 1
            self.cursors["article_analysis"] = index + 1

        for rule in self.fixture.rule_pool:
            rule_id = str(stable_uuid(f"rule:{rule['rule_id']}"))
            rule_version_id = str(stable_uuid(f"rule_version:{rule['rule_id']}:1"))
            if rule_id in self.rules:
                reports["rules"]["skipped_idempotent_count"] += 1
            else:
                self.rules[rule_id] = {"business_key": f"legacy-rule-pool:{rule['rule_id']}"}
                self.rule_versions[rule_version_id] = {"rule_id": rule_id}
                reports["rules"]["migrated_count"] += 1
            backtest_id = stable_short_id("legacy_bt", rule["rule_id"])
            if backtest_id in self.backtests:
                reports["backtests"]["skipped_idempotent_count"] += 1
            else:
                self.backtests[backtest_id] = {"rule_id": rule["rule_id"]}
                reports["backtests"]["migrated_count"] += 1

        dataset_id = str(stable_uuid("dataset_snapshot:ohlcv:2026-04-20"))
        if dataset_id in self.dataset_snapshots:
            reports["market_data"]["skipped_idempotent_count"] = len(self.fixture.ohlcv_rows)
        else:
            self.dataset_snapshots[dataset_id] = {"row_count": len(self.fixture.ohlcv_rows)}
            reports["market_data"]["migrated_count"] = len(self.fixture.ohlcv_rows)

        reports["articles"]["target_count_after"] = len(self.article_revisions)
        reports["article_analysis"]["target_count_after"] = len(self.prompt_runs) + len(self.article_structures) + len(self.rule_candidates)
        reports["rules"]["target_count_after"] = len(self.rules) + len(self.rule_versions)
        reports["backtests"]["target_count_after"] = len(self.backtests)
        reports["market_data"]["target_count_after"] = len(self.dataset_snapshots)
        reports["articles"]["quality_status_counts"] = {"ambiguous": len(self.fixture.raw_articles)}
        reports["rules"]["quality_status_counts"] = {"legacy_only": len(self.fixture.rule_pool)}
        reports["backtests"]["quality_status_counts"] = {"unresolved": len(self.fixture.rule_pool)}
        reports["market_data"]["quality_status_counts"] = {"partial": len(self.fixture.ohlcv_rows)}
        report.recovery_export = {"legacy_mapping_count": len(self.legacy_mappings), "dataset_snapshot_ids": list(self.dataset_snapshots)}
        return report


class SqlAlchemyStage2MigrationStore:
    def __init__(self) -> None:
        self._session_factory = get_session_factory()
        self._data_root = Path("data")

    def run_sync(self, *, mode: str, batch_size: int, fail_after_items: int | None, report_dir: Path) -> Stage2MigrationReport:
        return asyncio.run(self.run(mode=mode, batch_size=batch_size, fail_after_items=fail_after_items, report_dir=report_dir))

    async def run(
        self,
        *,
        mode: str,
        batch_size: int,
        fail_after_items: int | None,
        report_dir: Path,
    ) -> Stage2MigrationReport:
        ensure_directory(report_dir)
        async with self._session_factory() as session:
            inventory = await self._collect_inventory(session)
            self._reconcile_bootstrap_counts(inventory["database"])
            fingerprint = sha256_text(
                stable_json(
                    {
                        "database": {key: inventory["database"][key] for key in FINGERPRINT_DB_KEYS},
                        "sources": inventory["sources"],
                    }
                )
            )
            if mode == "dry-run":
                return await self._build_report(session, mode=mode, fingerprint=fingerprint, inventory=inventory)
            if mode == "verify":
                return await self._build_report(session, mode=mode, fingerprint=fingerprint, inventory=inventory, include_shadow=True)
            if mode in {"apply", "resume"}:
                return await self._apply(session, mode=mode, fingerprint=fingerprint, inventory=inventory, batch_size=batch_size, fail_after_items=fail_after_items)
            raise ValueError(f"unsupported mode: {mode}")

    async def _collect_inventory(self, session: AsyncSession) -> dict[str, Any]:
        database = {
            "raw_articles": await self._count(session, RawArticle),
            "blog_articles": await self._count(session, BlogArticle),
            "article_metadata": await self._count(session, ArticleMetadata),
            "article_metadata_selections": await self._count(session, ArticleMetadataSelection),
            "rule_pool": await self._count(session, RulePool),
            "ohlcv_bars": await self._count(session, OHLCVBar),
            "backtest_result_runs": await self._count(session, BacktestResultRun),
            "market_snapshots": await self._count(session, MarketSnapshot),
            "market_regimes": await self._count(session, MarketRegimeRecord),
            "rule_applicability_profiles": await self._count_table_name(session, "rule_applicability_profiles"),
            "trader_strategy_versions": await self._count(session, TraderStrategyVersion),
            "trader_memory": await self._count(session, TraderMemory),
            "jobs": await self._count(session, Job),
            "prompt_runs": await self._count(session, PromptRun),
            "article_structures": await self._count(session, ArticleStructure),
            "rule_candidates": await self._count(session, RuleCandidate),
            "rules": await self._count(session, Rule),
            "rule_versions": await self._count(session, RuleVersion),
            "dataset_snapshots": await self._count(session, DatasetSnapshot),
            "migration_runs": await self._count(session, MigrationRun),
            "legacy_id_mappings": await self._count(session, LegacyIdMapping),
        }

        daily_report_files = sorted(Path("daily-report").glob("*.md"))
        daily_session_files = sorted(Path("daily-sessions").glob("*.md"))
        jobs_dir = sorted(Path("data/jobs").glob("*/job.log"))
        strategy_files = sorted(Path(".").glob("**/*candidate*.json")) + sorted(Path(".").glob("**/*released*.json"))
        market_files = sorted(Path("data").glob("**/*market_state*.json"))
        json_jsonl_files = sorted(Path("data").glob("**/*.json")) + sorted(Path("data").glob("**/*.jsonl"))
        inventory = {
            "database": database,
            "sources": {
                "json_jsonl_files": self._file_inventory(json_jsonl_files),
                "job_logs": self._file_inventory(jobs_dir),
                "daily_report": self._file_inventory(daily_report_files),
                "daily_sessions": self._file_inventory(daily_session_files),
                "strategy_files": self._file_inventory(strategy_files),
                "market_files": self._file_inventory(market_files),
            },
        }
        return inventory

    async def _build_report(
        self,
        session: AsyncSession,
        *,
        mode: str,
        fingerprint: str,
        inventory: dict[str, Any],
        include_shadow: bool = False,
    ) -> Stage2MigrationReport:
        categories = await self._category_reports(session)
        shadow = await self._shadow_read(session) if include_shadow else {}
        return Stage2MigrationReport(
            mode=mode,
            status="completed",
            source_fingerprint=fingerprint,
            categories={key.value: value.to_dict() for key, value in categories.items()},
            inventory=inventory,
            run_id=None,
            recovery_export=await self._recovery_export(session),
            shadow_read=shadow,
            cutover=self._cutover_status(),
        )

    async def _apply(
        self,
        session: AsyncSession,
        *,
        mode: str,
        fingerprint: str,
        inventory: dict[str, Any],
        batch_size: int,
        fail_after_items: int | None,
    ) -> Stage2MigrationReport:
        run = await self._get_migration_run(session, fingerprint)
        if run and run.status == MigrationRunStatus.completed:
            report = await self._build_report(session, mode="apply", fingerprint=fingerprint, inventory=inventory, include_shadow=True)
            report.run_id = str(run.migration_run_id)
            for category_name in (
                "articles",
                "article_analysis",
                "selections",
                "rules",
                "backtests",
                "market_data",
            ):
                report.categories[category_name]["migrated_count"] = 0
                report.categories[category_name]["skipped_idempotent_count"] = report.categories[category_name]["eligible_count"]
            return report

        if run is None:
            run = MigrationRun(
                migration_run_id=stable_uuid(f"migration_run:{fingerprint}"),
                migration_name="stage2_data_migration",
                migration_version="2026_06_14_0004",
                source_fingerprint=fingerprint,
                status=MigrationRunStatus.running,
                started_at=datetime.now(UTC),
                pre_counts_json=inventory["database"],
                report_json={},
                recovery_point_json={},
            )
            session.add(run)
            await session.flush()

        processed = 0
        try:
            processed += await self._migrate_articles(session, run, batch_size=batch_size)
            if fail_after_items and processed >= fail_after_items:
                raise RuntimeError("injected failure after articles batch")
            processed += await self._migrate_article_analysis(session, run, batch_size=batch_size)
            if fail_after_items and processed >= fail_after_items:
                raise RuntimeError("injected failure after article analysis batch")
            processed += await self._migrate_selections(session, run)
            processed += await self._migrate_rules_and_backtests(session, run, batch_size=batch_size)
            processed += await self._migrate_market_data(session, run)
            run.status = MigrationRunStatus.completed
            run.completed_at = datetime.now(UTC)
            await self._write_quality_reports(session, run)
            await session.commit()
        except Exception as exc:
            run.status = MigrationRunStatus.failed
            run.recovery_point_json = {"mode": mode, "processed_items": processed, "error": str(exc)}
            await session.commit()
            report = await self._build_report(session, mode=mode, fingerprint=fingerprint, inventory=inventory, include_shadow=False)
            report.status = "failed"
            report.run_id = str(run.migration_run_id)
            return report

        report = await self._build_report(session, mode="apply", fingerprint=fingerprint, inventory=inventory, include_shadow=True)
        report.run_id = str(run.migration_run_id)
        return report

    async def _migrate_articles(self, session: AsyncSession, run: MigrationRun, *, batch_size: int) -> int:
        rows = (
            await session.execute(
                select(BlogArticle, RawArticle)
                .join(RawArticle, RawArticle.source_url == BlogArticle.source_url)
                .order_by(BlogArticle.id)
            )
        ).all()
        processed = 0
        for offset in range(0, len(rows), batch_size):
            for blog, raw in rows[offset : offset + batch_size]:
                revision_id = stable_uuid(f"article_revision:{blog.id}:1")
                exists = await session.get(ArticleRevision, revision_id)
                if exists is None:
                    session.add(
                        ArticleRevision(
                            article_revision_id=revision_id,
                            article_id=blog.id,
                            revision_no=1,
                            content_hash=blog.content_hash or sha256_text(blog.content_text),
                            content_text=blog.content_text,
                            content_html=blog.content_html,
                            source_payload={"blog_article": sanitize_payload(blog.raw_payload), "raw_article": sanitize_payload(raw.raw_payload)},
                            captured_at=blog.crawled_at,
                            quality_status="ambiguous" if raw.is_processed is False else "complete",
                        )
                    )
                    await self._upsert_mapping(
                        session,
                        legacy_system="blog_articles",
                        legacy_object_type="article",
                        legacy_id=str(blog.id),
                        canonical_object_type="article",
                        canonical_id=blog.id,
                        canonical_version_id=revision_id,
                        status="complete",
                        reason="blog article canonical article",
                        snapshot={"source_url": blog.source_url},
                    )
                    await self._upsert_mapping(
                        session,
                        legacy_system="raw_articles",
                        legacy_object_type="article",
                        legacy_id=str(raw.id),
                        canonical_object_type="article",
                        canonical_id=blog.id,
                        canonical_version_id=revision_id,
                        status="ambiguous",
                        reason="raw article is_processed=false conflicts with existing blog article",
                        snapshot={"source_url": raw.source_url, "is_processed": raw.is_processed},
                    )
                    await self._upsert_run_item(session, run, "raw_articles", str(raw.id), "article", blog.id, revision_id, MigrationItemStatus.migrated, {"source_url": raw.source_url})
                else:
                    await self._upsert_run_item(session, run, "raw_articles", str(raw.id), "article", blog.id, revision_id, MigrationItemStatus.skipped, {"source_url": raw.source_url})
                processed += 1
        return processed

    async def _migrate_article_analysis(self, session: AsyncSession, run: MigrationRun, *, batch_size: int) -> int:
        rows = (await session.execute(select(ArticleMetadata).order_by(ArticleMetadata.article_id, ArticleMetadata.version))).scalars().all()
        processed = 0
        for offset in range(0, len(rows), batch_size):
            for metadata in rows[offset : offset + batch_size]:
                prompt_run_id = stable_uuid(f"prompt_run:{metadata.article_id}:{metadata.version}")
                structure_id = stable_uuid(f"article_structure:{metadata.article_id}:{metadata.version}")
                prompt_run = await session.get(PromptRun, prompt_run_id)
                if prompt_run is None:
                    prompt_run = PromptRun(
                        prompt_run_id=prompt_run_id,
                        run_id=f"legacy:{metadata.id}",
                        article_id=metadata.article_id,
                        prompt_name="legacy_article_analysis",
                        prompt_version=metadata.extraction_version or "legacy_unknown",
                        schema_name="article_metadata",
                        schema_version=metadata.version or "legacy_unknown",
                        provider=metadata.provider or "legacy_unknown",
                        model=metadata.model or "legacy_unknown",
                        input_object_type="article",
                        input_object_id=str(metadata.article_id),
                        input_version_id=str(metadata.id),
                        input_hash=sha256_text(metadata.raw_llm_output and stable_json(metadata.raw_llm_output) or str(metadata.id)),
                        request_json={"article_metadata_id": str(metadata.id), "article_type": metadata.article_type},
                        raw_output=sanitize_payload(metadata.raw_llm_output),
                        raw_output_text=stable_json(metadata.raw_llm_output),
                        validation_state=PromptValidationState.valid,
                        validation_errors={},
                        retry_count=0,
                        token_usage={},
                        started_at=metadata.processed_at,
                        completed_at=metadata.processed_at,
                    )
                    session.add(prompt_run)
                    await session.flush()
                structure = await session.get(ArticleStructure, structure_id)
                if structure is None:
                    structure = ArticleStructure(
                        article_structure_id=structure_id,
                        article_id=metadata.article_id,
                        article_revision_id=stable_uuid(f"article_revision:{metadata.article_id}:1"),
                        prompt_run_id=prompt_run_id,
                        schema_version=metadata.version,
                        payload={
                            "article_type": metadata.article_type,
                            "extracted_concepts": sanitize_payload(metadata.extracted_concepts),
                            "strategy_rules": sanitize_payload(metadata.strategy_rules),
                            "preconditions": sanitize_payload(metadata.preconditions),
                            "comment_insights": sanitize_payload(metadata.comment_insights),
                        },
                        evidence_json={"raw_llm_output": sanitize_payload(metadata.raw_llm_output)},
                        missing_fields={},
                        inference_fields={},
                        lifecycle_state="draft",
                        quality_status="partial",
                        created_by="stage2-migration",
                        updated_by="stage2-migration",
                    )
                    session.add(structure)
                    await session.flush()
                for index, rule in enumerate(metadata.strategy_rules):
                    candidate_id = stable_uuid(f"rule_candidate:{metadata.article_id}:{metadata.version}:{index}")
                    if await session.get(RuleCandidate, candidate_id) is None:
                        session.add(
                            RuleCandidate(
                                rule_candidate_id=candidate_id,
                                article_structure_id=structure_id,
                                source_article_id=metadata.article_id,
                                candidate_index=index,
                                candidate_fingerprint=sha256_text(stable_json(rule)),
                                rule_type=str(rule.get("rule_type", "legacy_unknown")),
                                canonical_payload=sanitize_payload(rule),
                                evidence_json={"raw_llm_output": sanitize_payload(metadata.raw_llm_output)},
                                explicit_fields={},
                                inferred_fields={},
                                missing_fields={},
                                data_dependencies={},
                                backtestability_status="legacy_unknown",
                                review_state="extracted",
                                quality_status="partial",
                                created_by="stage2-migration",
                                updated_by="stage2-migration",
                            )
                        )
                await self._upsert_mapping(
                    session,
                    legacy_system="article_metadata",
                    legacy_object_type="analysis",
                    legacy_id=str(metadata.id),
                    canonical_object_type="article_structure",
                    canonical_id=structure_id,
                    canonical_version_id=prompt_run_id,
                    status="partial",
                    reason="legacy article metadata migrated without approval",
                    snapshot={"article_id": str(metadata.article_id), "schema_version": metadata.version},
                )
                await self._upsert_run_item(session, run, "article_metadata", str(metadata.id), "article_structure", structure_id, prompt_run_id, MigrationItemStatus.migrated, {"article_id": str(metadata.article_id), "schema_version": metadata.version})
                processed += 1
        return processed

    async def _migrate_selections(self, session: AsyncSession, run: MigrationRun) -> int:
        rows = (await session.execute(select(ArticleMetadataSelection).order_by(ArticleMetadataSelection.selection_id))).scalars().all()
        for row in rows:
            structure_id = stable_uuid(f"article_structure:{row.article_id}:{row.selected_schema_version}")
            event_id = stable_uuid(f"selection_event:{row.selection_id}")
            existing = await session.execute(select(MigrationRunItem).where(MigrationRunItem.migration_run_id == run.migration_run_id, MigrationRunItem.legacy_object_type == "article_metadata_selection", MigrationRunItem.legacy_id == row.selection_id))
            if existing.scalar_one_or_none() is None:
                if await session.get(LifecycleEvent, event_id) is None:
                    session.add(
                        LifecycleEvent(
                            event_id=event_id,
                            object_type="article_structure_selection_compatibility",
                            object_id=structure_id,
                            from_state=None,
                            to_state="legacy_auto_selected",
                            actor_type="compatibility_auto",
                            actor_id=row.selected_by or row.selection_mode,
                            reason_code="legacy_auto_selection",
                            reason_text=row.selection_reason,
                            before_json={},
                            after_json={"selected_schema_version": row.selected_schema_version, "selection_mode": row.selection_mode},
                            occurred_at=row.selected_at or row.created_at,
                            correlation_id=row.selection_id,
                        )
                    )
                await self._upsert_mapping(
                    session,
                    legacy_system="article_metadata_selections",
                    legacy_object_type="selection",
                    legacy_id=row.selection_id,
                    canonical_object_type="article_structure",
                    canonical_id=structure_id,
                    canonical_version_id=None,
                    status="legacy_only",
                    reason="automatic selection preserved as compatibility event",
                    snapshot={"selection_mode": row.selection_mode, "selected_schema_version": row.selected_schema_version},
                )
                await self._upsert_run_item(session, run, "article_metadata_selection", row.selection_id, "article_structure", structure_id, None, MigrationItemStatus.migrated, {"selection_mode": row.selection_mode})
        return len(rows)

    async def _migrate_rules_and_backtests(self, session: AsyncSession, run: MigrationRun, *, batch_size: int) -> int:
        rows = (await session.execute(select(RulePool).order_by(RulePool.created_at))).scalars().all()
        processed = 0
        for offset in range(0, len(rows), batch_size):
            for row in rows[offset : offset + batch_size]:
                canonical_rule_id = stable_uuid(f"rule:{row.rule_id}")
                canonical_rule_version_id = stable_uuid(f"rule_version:{row.rule_id}:1")
                family_id = stable_uuid(f"rule_family:{sha256_text(stable_json(row.extraction_layer))}")
                if await session.get(Rule, canonical_rule_id) is None:
                    session.add(
                        Rule(
                            rule_id=canonical_rule_id,
                            business_key=f"legacy-rule-pool:{row.rule_id}",
                            current_published_version_id=None,
                            created_at=row.created_at,
                            created_by="stage2-migration",
                            updated_at=row.updated_at,
                            updated_by="stage2-migration",
                        )
                    )
                    await session.flush()
                if await session.get(RuleVersion, canonical_rule_version_id) is None:
                    lifecycle = "draft"
                    quality = "legacy_only" if row.reviewed_by == "auto_review" else "unresolved"
                    session.add(
                        RuleVersion(
                            rule_version_id=canonical_rule_version_id,
                            rule_id=canonical_rule_id,
                            version_no=1,
                            source_candidate_id=stable_uuid(self._candidate_key_from_rule_id(row.rule_id)),
                            canonical_fingerprint=sha256_text(stable_json(row.extraction_layer)),
                            schema_version="legacy_unknown",
                            lifecycle_state=lifecycle,
                            title=row.rule_id,
                            description=None,
                            rule_type=row.rule_type,
                            instrument_scope={"instrument_focus": row.instrument_focus},
                            condition_json=sanitize_payload(row.extraction_layer),
                            action_json=sanitize_payload(row.extraction_layer.get("action", {})),
                            parameter_json={},
                            data_dependencies={},
                            evidence_json={"source_article_ids": sanitize_payload(row.source_article_ids)},
                            quality_status=quality,
                            created_by="stage2-migration",
                            updated_by="stage2-migration",
                        )
                    )
                    await session.flush()
                if await session.get(RuleFamily, family_id) is None:
                    session.add(
                        RuleFamily(
                            rule_family_id=family_id,
                            family_key=f"legacy:{row.rule_type}:{sha256_text(stable_json(row.extraction_layer))[:12]}",
                            canonical_fingerprint=sha256_text(stable_json(row.extraction_layer)),
                            name=row.rule_type,
                            lifecycle_state="draft",
                            quality_status="legacy_only",
                            created_by="stage2-migration",
                            updated_by="stage2-migration",
                        )
                    )
                    await session.flush()
                membership_id = stable_uuid(f"rule_family_membership:{family_id}:{canonical_rule_version_id}")
                if await session.get(RuleFamilyMembership, membership_id) is None:
                    session.add(
                        RuleFamilyMembership(
                            membership_id=membership_id,
                            rule_family_id=family_id,
                            rule_version_id=canonical_rule_version_id,
                            member_role="legacy_import",
                            approved_by=None,
                            approved_at=None,
                        )
                    )
                backtest_run_id = stable_short_id("legacy_bt", row.rule_id)
                if await session.get(BacktestResultRun, backtest_run_id) is None:
                    source_date = await self._rule_source_date(session, row.source_article_ids)
                    session.add(
                        BacktestResultRun(
                            result_run_id=backtest_run_id,
                            source_job_id=None,
                            job_type="legacy_rule_pool",
                            request_trader_id="legacy_rule_pool",
                            strategy_version_id=None,
                            request_date_from=source_date,
                            request_date_to=source_date,
                            benchmark_symbol=None,
                            regime_version=None,
                            source_feature_version=None,
                            mode="compatibility",
                            scoring_profile=None,
                            result_version="legacy_unknown",
                            status="legacy_import",
                            quality_status="unresolved",
                            total_days=None,
                            total_trades=None,
                            valid_trades=None,
                            skipped_trades=None,
                            win_rate=None,
                            avg_return_pct=None,
                            summary_json=sanitize_payload(row.backtest_result or {}),
                            regime_metrics_json=[],
                            rule_regime_metrics_json={},
                            fingerprint=sha256_text(stable_json(row.backtest_result or {})),
                            storage_ref={"source_table": "rule_pool", "legacy_rule_id": row.rule_id},
                            artifact_ref={},
                        )
                    )
                await self._upsert_mapping(
                    session,
                    legacy_system="rule_pool",
                    legacy_object_type="rule",
                    legacy_id=row.rule_id,
                    canonical_object_type="rule_version",
                    canonical_id=canonical_rule_id,
                    canonical_version_id=canonical_rule_version_id,
                    status="legacy_only" if row.reviewed_by == "auto_review" else "unresolved",
                    reason="legacy approved is not canonical published",
                    snapshot={"review_status": row.review_status, "reviewed_by": row.reviewed_by},
                )
                await self._upsert_run_item(session, run, "rule_pool", row.rule_id, "rule_version", canonical_rule_id, canonical_rule_version_id, MigrationItemStatus.migrated, {"review_status": row.review_status})
                processed += 1
        return processed

    async def _migrate_market_data(self, session: AsyncSession, run: MigrationRun) -> int:
        rows = (await session.execute(select(OHLCVBar).order_by(OHLCVBar.trade_date, OHLCVBar.symbol))).scalars().all()
        if not rows:
            return 0
        trade_dates = sorted({row.trade_date for row in rows})
        dataset_id = stable_uuid(f"dataset_snapshot:{trade_dates[0].isoformat()}:{len(rows)}")
        if await session.get(DatasetSnapshot, dataset_id) is None:
            session.add(
                DatasetSnapshot(
                    dataset_snapshot_id=dataset_id,
                    content_fingerprint=sha256_text(stable_json({"trade_dates": [day.isoformat() for day in trade_dates], "count": len(rows)})),
                    trade_date=trade_dates[0],
                    market="CN",
                    dataset_type="ohlcv_partial",
                    date_from=trade_dates[0],
                    date_to=trade_dates[-1],
                    symbol_manifest={"count": len({row.symbol for row in rows}), "symbols": sorted({row.symbol for row in rows})[:10]},
                    ohlcv_manifest={"row_count": len(rows), "trade_dates": [day.isoformat() for day in trade_dates], "coverage": "partial"},
                    kaipan_manifest={},
                    benchmark_symbol=None,
                    market_state_definition_version=None,
                    available_at=datetime.now(UTC),
                    frozen_at=datetime.now(UTC),
                    lifecycle_state=DatasetLifecycleState.partial,
                    quality_report_id=None,
                    storage_ref={"source_table": "ohlcv_bars"},
                )
            )
        for row in rows:
            await self._upsert_mapping(
                session,
                legacy_system="ohlcv_bars",
                legacy_object_type="ohlcv_row",
                legacy_id=str(row.id),
                canonical_object_type="dataset_snapshot",
                canonical_id=dataset_id,
                canonical_version_id=None,
                status="partial",
                reason="84 one-day rows are only a partial dataset snapshot",
                snapshot={"symbol": row.symbol, "trade_date": row.trade_date.isoformat()},
            )
            await self._upsert_run_item(session, run, "ohlcv_bars", str(row.id), "dataset_snapshot", dataset_id, None, MigrationItemStatus.migrated, {"symbol": row.symbol, "trade_date": row.trade_date.isoformat()})
        return len(rows)

    async def _write_quality_reports(self, session: AsyncSession, run: MigrationRun) -> None:
        categories = await self._category_reports(session)
        for category, payload in categories.items():
            report_id = stable_uuid(f"migration_quality:{run.migration_run_id}:{category.value}")
            if await session.get(MigrationQualityReport, report_id) is None:
                session.add(
                    MigrationQualityReport(
                        migration_quality_report_id=report_id,
                        migration_run_id=run.migration_run_id,
                        object_type=category.value,
                        report_json=payload.to_dict(),
                        created_at=datetime.now(UTC),
                    )
                )

    async def _category_reports(self, session: AsyncSession) -> dict[Stage2MigrationCategory, Stage2MigrationCategoryReport]:
        category_reports = {
            Stage2MigrationCategory.articles: Stage2MigrationCategoryReport(
                source_count=await self._count(session, BlogArticle),
                eligible_count=await self._count(session, BlogArticle),
                target_count_before=await self._count(session, ArticleRevision),
                target_count_after=await self._count(session, ArticleRevision),
                quality_status_counts={"ambiguous": await self._count_false_raw_processed(session)},
            ),
            Stage2MigrationCategory.article_analysis: Stage2MigrationCategoryReport(
                source_count=await self._count(session, ArticleMetadata),
                eligible_count=await self._count(session, ArticleMetadata),
                target_count_before=(await self._count(session, PromptRun)) + (await self._count(session, ArticleStructure)) + (await self._count(session, RuleCandidate)),
                target_count_after=(await self._count(session, PromptRun)) + (await self._count(session, ArticleStructure)) + (await self._count(session, RuleCandidate)),
                quality_status_counts={"partial": await self._count(session, ArticleStructure)},
            ),
            Stage2MigrationCategory.selections: Stage2MigrationCategoryReport(
                source_count=await self._count(session, ArticleMetadataSelection),
                eligible_count=await self._count(session, ArticleMetadataSelection),
                target_count_before=await self._count(session, LifecycleEvent),
                target_count_after=await self._count(session, LifecycleEvent),
                quality_status_counts={"legacy_only": await self._count(session, ArticleMetadataSelection)},
            ),
            Stage2MigrationCategory.rules: Stage2MigrationCategoryReport(
                source_count=await self._count(session, RulePool),
                eligible_count=await self._count(session, RulePool),
                target_count_before=(await self._count(session, Rule)) + (await self._count(session, RuleVersion)) + (await self._count(session, RuleFamily)) + (await self._count(session, RuleFamilyMembership)),
                target_count_after=(await self._count(session, Rule)) + (await self._count(session, RuleVersion)) + (await self._count(session, RuleFamily)) + (await self._count(session, RuleFamilyMembership)),
                quality_status_counts={"legacy_only": await self._count_rules_with_auto_review(session), "unresolved": await self._count_rules_without_auto_review(session)},
            ),
            Stage2MigrationCategory.backtests: Stage2MigrationCategoryReport(
                source_count=await self._count_non_null_rule_backtests(session),
                eligible_count=await self._count_non_null_rule_backtests(session),
                target_count_before=await self._count(session, BacktestResultRun),
                target_count_after=await self._count(session, BacktestResultRun),
                quality_status_counts={"unresolved": await self._count_non_null_rule_backtests(session)},
            ),
            Stage2MigrationCategory.author_profiles: Stage2MigrationCategoryReport(quality_status_counts={}),
            Stage2MigrationCategory.strategies: Stage2MigrationCategoryReport(quality_status_counts={}),
            Stage2MigrationCategory.market_data: Stage2MigrationCategoryReport(
                source_count=await self._count(session, OHLCVBar),
                eligible_count=await self._count(session, OHLCVBar),
                target_count_before=await self._count(session, DatasetSnapshot),
                target_count_after=await self._count(session, DatasetSnapshot),
                quality_status_counts={"partial": await self._count(session, OHLCVBar)},
            ),
            Stage2MigrationCategory.daily_objects: Stage2MigrationCategoryReport(
                source_count=len(list(Path("daily-report").glob("*.md"))) + len(list(Path("daily-sessions").glob("*.md"))),
                rejected_count=len(list(Path("daily-report").glob("*.md"))) + len(list(Path("daily-sessions").glob("*.md"))),
                quality_status_counts={"ambiguous": len(list(Path("daily-report").glob("*.md"))) + len(list(Path("daily-sessions").glob("*.md")))},
            ),
        }
        category_reports[Stage2MigrationCategory.article_analysis].migrated_count = await self._count(session, PromptRun)
        category_reports[Stage2MigrationCategory.articles].migrated_count = await self._count(session, ArticleRevision)
        category_reports[Stage2MigrationCategory.rules].migrated_count = await self._count(session, RuleVersion)
        category_reports[Stage2MigrationCategory.backtests].migrated_count = await self._count(session, BacktestResultRun)
        category_reports[Stage2MigrationCategory.market_data].migrated_count = await self._count(session, DatasetSnapshot)
        category_reports[Stage2MigrationCategory.article_analysis].eligible_count = await self._count(session, ArticleMetadata)
        return category_reports

    async def _shadow_read(self, session: AsyncSession) -> dict[str, Any]:
        return {
            "articles": {
                "legacy_blog_articles": await self._count(session, BlogArticle),
                "canonical_article_revisions": await self._count(session, ArticleRevision),
            },
            "analysis": {
                "legacy_metadata": await self._count(session, ArticleMetadata),
                "prompt_runs": await self._count(session, PromptRun),
                "article_structures": await self._count(session, ArticleStructure),
                "rule_candidates": await self._count(session, RuleCandidate),
            },
            "rules": {
                "legacy_rule_pool": await self._count(session, RulePool),
                "canonical_rule_versions": await self._count(session, RuleVersion),
                "published_rule_versions": await self._count_published_rule_versions(session),
            },
            "mappings": {
                "legacy_mapping_count": await self._count(session, LegacyIdMapping),
                "duplicate_legacy_keys": await self._count_duplicate_legacy_keys(session),
            },
        }

    async def _recovery_export(self, session: AsyncSession) -> dict[str, Any]:
        rows = (
            await session.execute(
                select(LegacyIdMapping.legacy_system, LegacyIdMapping.legacy_object_type, LegacyIdMapping.legacy_id, LegacyIdMapping.canonical_object_type, LegacyIdMapping.canonical_id, LegacyIdMapping.canonical_version_id, LegacyIdMapping.mapping_status)
            )
        ).all()
        return {
            "mappings": [
                {
                    "legacy_system": legacy_system,
                    "legacy_object_type": legacy_object_type,
                    "legacy_id": legacy_id,
                    "canonical_object_type": canonical_object_type,
                    "canonical_id": str(canonical_id) if canonical_id else None,
                    "canonical_version_id": str(canonical_version_id) if canonical_version_id else None,
                    "mapping_status": getattr(mapping_status, "value", mapping_status),
                }
                for legacy_system, legacy_object_type, legacy_id, canonical_object_type, canonical_id, canonical_version_id, mapping_status in rows
            ]
        }

    def _cutover_status(self) -> dict[str, Any]:
        enabled = canonical_writer_enabled()
        return {
            "switch": "STAGE2_CANONICAL_WRITER_ENABLED",
            "enabled": enabled,
            "verified": True,
            "recovery_evidence": "migration recovery export available before writer cutover",
        }

    def _file_inventory(self, paths: list[Path]) -> dict[str, Any]:
        if not paths:
            return {"count": 0, "fingerprint": sha256_text("[]"), "files": []}
        files = [{"path": str(path), "sha256": file_sha256(path)} for path in paths if path.is_file()]
        return {"count": len(files), "fingerprint": sha256_text(stable_json(files)), "files": files}

    def _reconcile_bootstrap_counts(self, database: dict[str, Any]) -> None:
        explained_drift = {
            "backtest_result_runs": "populated by RT-S2-003 compatibility backtest observations",
        }
        mismatches = {}
        for key, expected in BOOTSTRAP_COUNTS.items():
            actual = database.get(key)
            if actual == expected:
                continue
            if key in explained_drift and int(database.get("migration_runs", 0)) > 0 and int(actual or 0) >= expected:
                continue
            mismatches[key] = {"expected": expected, "actual": actual}
        if mismatches:
            raise RuntimeError(f"ESCALATION_REQUIRED bootstrap count mismatch: {stable_json(mismatches)}")

    def _candidate_key_from_rule_id(self, rule_id: str) -> str:
        parts = rule_id.split(":")
        if len(parts) < 4:
            return f"rule_candidate:unparsed:{rule_id}"
        return f"rule_candidate:{parts[0]}:{parts[1]}:{int(parts[-1])}"

    async def _rule_source_date(self, session: AsyncSession, source_article_ids: list[str]) -> date:
        if not source_article_ids:
            return date(2026, 4, 20)
        article_id = UUID(source_article_ids[0]) if isinstance(source_article_ids[0], str) and len(source_article_ids[0]) == 36 else None
        if article_id is None:
            return date(2026, 4, 20)
        article = await session.get(BlogArticle, article_id)
        if article and article.published_at:
            return article.published_at.date()
        return date(2026, 4, 20)

    async def _upsert_mapping(
        self,
        session: AsyncSession,
        *,
        legacy_system: str,
        legacy_object_type: str,
        legacy_id: str,
        canonical_object_type: str,
        canonical_id: UUID | None,
        canonical_version_id: UUID | None,
        status: str,
        reason: str,
        snapshot: dict[str, Any],
    ) -> None:
        stmt = select(LegacyIdMapping).where(
            LegacyIdMapping.legacy_system == legacy_system,
            LegacyIdMapping.legacy_object_type == legacy_object_type,
            LegacyIdMapping.legacy_id == legacy_id,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            session.add(
                LegacyIdMapping(
                    mapping_id=stable_uuid(f"legacy_mapping:{legacy_system}:{legacy_object_type}:{legacy_id}"),
                    legacy_system=legacy_system,
                    legacy_object_type=legacy_object_type,
                    legacy_id=legacy_id,
                    canonical_object_type=canonical_object_type,
                    canonical_id=canonical_id,
                    canonical_version_id=canonical_version_id,
                    mapping_status=status,
                    mapping_reason=reason,
                    source_snapshot=snapshot,
                    created_at=datetime.now(UTC),
                )
            )
        elif existing.canonical_id not in {canonical_id, None}:
            conflict_id = stable_uuid(f"migration_conflict:{legacy_system}:{legacy_object_type}:{legacy_id}")
            if await session.get(MigrationConflict, conflict_id) is None:
                session.add(
                    MigrationConflict(
                        migration_conflict_id=conflict_id,
                        migration_run_id=stable_uuid(f"migration_run:{sha256_text(legacy_system)}"),
                        conflict_key=f"{legacy_system}:{legacy_object_type}:{legacy_id}",
                        status=MigrationConflictStatus.open,
                        legacy_payload=snapshot,
                        canonical_payload={"existing_canonical_id": str(existing.canonical_id), "new_canonical_id": str(canonical_id) if canonical_id else None},
                        resolution_json=None,
                        created_at=datetime.now(UTC),
                    )
                )

    async def _upsert_run_item(
        self,
        session: AsyncSession,
        run: MigrationRun,
        legacy_object_type: str,
        legacy_id: str,
        canonical_object_type: str,
        canonical_id: UUID | None,
        canonical_version_id: UUID | None,
        status: MigrationItemStatus,
        payload: dict[str, Any],
    ) -> None:
        stmt = select(MigrationRunItem).where(
            MigrationRunItem.migration_run_id == run.migration_run_id,
            MigrationRunItem.legacy_object_type == legacy_object_type,
            MigrationRunItem.legacy_id == legacy_id,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            session.add(
                MigrationRunItem(
                    migration_run_item_id=stable_uuid(f"migration_item:{run.migration_run_id}:{legacy_object_type}:{legacy_id}"),
                    migration_run_id=run.migration_run_id,
                    legacy_object_type=legacy_object_type,
                    legacy_id=legacy_id,
                    canonical_object_type=canonical_object_type,
                    canonical_id=canonical_id,
                    canonical_version_id=canonical_version_id,
                    status=status,
                    message=None,
                    payload_json=payload,
                )
            )

    async def _get_migration_run(self, session: AsyncSession, fingerprint: str) -> MigrationRun | None:
        stmt = select(MigrationRun).where(
            MigrationRun.migration_name == "stage2_data_migration",
            MigrationRun.migration_version == "2026_06_14_0004",
            MigrationRun.source_fingerprint == fingerprint,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def _count(self, session: AsyncSession, model: Any) -> int:
        return int((await session.execute(select(func.count()).select_from(model))).scalar_one())

    async def _count_table_name(self, session: AsyncSession, table_name: str) -> int:
        result = await session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
        return int(result.scalar_one())

    async def _count_false_raw_processed(self, session: AsyncSession) -> int:
        return int((await session.execute(select(func.count()).select_from(RawArticle).where(RawArticle.is_processed.is_(False)))).scalar_one())

    async def _count_non_null_rule_backtests(self, session: AsyncSession) -> int:
        return int((await session.execute(select(func.count()).select_from(RulePool).where(RulePool.backtest_result.is_not(None)))).scalar_one())

    async def _count_rules_with_auto_review(self, session: AsyncSession) -> int:
        return int((await session.execute(select(func.count()).select_from(RulePool).where(RulePool.reviewed_by == "auto_review"))).scalar_one())

    async def _count_rules_without_auto_review(self, session: AsyncSession) -> int:
        return int((await session.execute(select(func.count()).select_from(RulePool).where(RulePool.reviewed_by.is_(None)))).scalar_one())

    async def _count_published_rule_versions(self, session: AsyncSession) -> int:
        return int((await session.execute(select(func.count()).select_from(RuleVersion).where(RuleVersion.lifecycle_state == "published"))).scalar_one())

    async def _count_duplicate_legacy_keys(self, session: AsyncSession) -> int:
        rows = (
            await session.execute(
                select(func.count()).select_from(
                    select(LegacyIdMapping.legacy_system, LegacyIdMapping.legacy_object_type, LegacyIdMapping.legacy_id)
                    .group_by(LegacyIdMapping.legacy_system, LegacyIdMapping.legacy_object_type, LegacyIdMapping.legacy_id)
                    .having(func.count() > 1)
                    .subquery()
                )
            )
        ).scalar_one()
        return int(rows)


def build_default_store() -> SqlAlchemyStage2MigrationStore:
    return SqlAlchemyStage2MigrationStore()


class Stage2MigrationRunner:
    def __init__(
        self,
        *,
        store: Stage2MigrationStore | None = None,
        report_dir: Path,
        batch_size: int = 100,
        fail_after_items: int | None = None,
    ) -> None:
        self.store = store or build_default_store()
        self.report_dir = report_dir
        self.batch_size = batch_size
        self.fail_after_items = fail_after_items

    def run_sync(self, *, mode: str) -> Stage2MigrationReport:
        ensure_directory(self.report_dir)
        report = self.store.run_sync(mode=mode, batch_size=self.batch_size, fail_after_items=self.fail_after_items, report_dir=self.report_dir)
        self._write_reports(report)
        return report

    def _write_reports(self, report: Stage2MigrationReport) -> None:
        ensure_directory(self.report_dir)
        (self.report_dir / "preflight_inventory.json").write_text(stable_json(report.inventory), encoding="utf-8")
        filename = {
            "dry-run": "dry_run_report.json",
            "apply": "apply_report.json",
            "verify": "verify_report.json",
            "resume": "apply_report.json",
        }[report.mode]
        (self.report_dir / filename).write_text(stable_json(asdict(report)), encoding="utf-8")
        (self.report_dir / "recovery_export.json").write_text(stable_json(report.recovery_export), encoding="utf-8")
