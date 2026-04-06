from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any
from pathlib import Path

from src.audit.service import AuditService, default_dataset_version
from src.agents.data_agent.skills.store_db import StoreStats, store_articles_jsonl_to_db
from src.common.config import AppConfig
from src.common.utils import ensure_dir
from src.pipeline.graph import PipelineGraphRegistry
from src.pipeline.health import PipelineHealthSnapshot
from src.pipeline.runner import PipelineRunner
from src.pipeline.tasks.clean_task import CleanResult, run_clean_task
from src.pipeline.tasks.crawl_task import CrawlResult, run_crawl_task
from src.pipeline.tasks.export_task import ExportResult, run_export_task
from src.pipeline.tasks.validate_task import ValidateResult, run_validate_task
from src.pipeline.tasks.process_tasks import ProcessTasksStats, run_process_tasks


@dataclass(slots=True)
class PipelineRunResult:
	crawl: CrawlResult
	clean: CleanResult
	validate: ValidateResult
	store: StoreStats
	export: ExportResult
	process: ProcessTasksStats


def discover_crawl_jsonl_paths(*, base_dir: Path, config: AppConfig) -> list[Path]:
	paths: list[Path] = []
	for src in config.crawl.sources:
		if not src.enabled:
			continue
		p = base_dir / "data" / "processed" / "crawl" / src.source / src.author_id / "articles.jsonl"
		paths.append(p)
	return paths


def default_pipeline_state_dir(*, base_dir: Path) -> Path:
	return ensure_dir(base_dir / "data" / "processed" / "pipeline")


def _store_stats_payload(store_stats: StoreStats) -> dict[str, object]:
	"""Normalize store stats into a plain payload for audit records."""

	if is_dataclass(store_stats):
		return asdict(store_stats)
	if hasattr(store_stats, "__dict__"):
		return dict(vars(store_stats))
	return {"value": store_stats}


def _build_data_pipeline_handlers(
	*,
	config: AppConfig,
	base_dir: Path,
	max_articles: int | None,
	force: bool,
	skip_crawl: bool,
	audit: AuditService,
) -> dict[str, Any]:
	"""Create node handlers for the built-in data pipeline graph."""

	def _crawl(context: dict[str, Any]) -> CrawlResult:
		if skip_crawl:
			result = CrawlResult(outputs=[])
		else:
			result = run_crawl_task(config=config, base_dir=base_dir, max_articles=max_articles)
		context["crawl_result"] = result
		return result

	def _clean(context: dict[str, Any]) -> CleanResult:
		crawl_paths = discover_crawl_jsonl_paths(base_dir=base_dir, config=config)
		result = run_clean_task(base_dir=base_dir, input_paths=crawl_paths, force=force)
		context["clean_result"] = result
		return result

	def _validate(context: dict[str, Any]) -> ValidateResult:
		clean_result = context["clean_result"]
		result = run_validate_task(base_dir=base_dir, input_paths=clean_result.cleaned_paths, force=force)
		context["validate_result"] = result
		return result

	async def _store(context: dict[str, Any]) -> StoreStats:
		validate_result = context["validate_result"]
		result = await store_articles_jsonl_to_db(base_dir=base_dir, jsonl_paths=validate_result.validated_paths)
		context["store_stats"] = result
		await audit.record(
			event_type="article_ingested_batch",
			actor="pipeline.run_pipeline",
			entity_type="database",
			entity_id=None,
			dataset_version=default_dataset_version(prefix="pipeline"),
			payload=_store_stats_payload(result),
			source="pipeline",
		)
		return result

	async def _process(context: dict[str, Any]) -> ProcessTasksStats:
		result = await run_process_tasks(config=config)
		context["process_stats"] = result
		return result

	async def _export(context: dict[str, Any]) -> ExportResult:
		result = await run_export_task()
		context["export_result"] = result
		return result

	return {
		"crawl": _crawl,
		"clean": _clean,
		"validate": _validate,
		"store": _store,
		"process": _process,
		"export": _export,
	}


async def _run_data_pipeline_graph(
	*,
	config: AppConfig,
	base_dir: Path,
	max_articles: int | None = None,
	force: bool = False,
	skip_crawl: bool = False,
) -> tuple[PipelineHealthSnapshot, dict[str, Any]]:
	"""Run the built-in data pipeline graph and return the snapshot plus context."""

	default_pipeline_state_dir(base_dir=base_dir)
	audit = AuditService()
	context: dict[str, Any] = {
		"config": config,
		"base_dir": base_dir,
		"max_articles": max_articles,
		"force": force,
		"skip_crawl": skip_crawl,
		"audit_service": audit,
	}
	registry = PipelineGraphRegistry.default()
	runner = PipelineRunner(
		handlers=_build_data_pipeline_handlers(
			config=config,
			base_dir=base_dir,
			max_articles=max_articles,
			force=force,
			skip_crawl=skip_crawl,
			audit=audit,
		),
		registry=registry,
	)
	snapshot = await runner.run("data_pipeline", context=context)
	context["health_snapshot"] = snapshot
	return snapshot, context


async def run_pipeline(
	*,
	config: AppConfig,
	base_dir: Path,
	max_articles: int | None = None,
	force: bool = False,
	skip_crawl: bool = False,
) -> PipelineRunResult:
	_, context = await _run_data_pipeline_graph(
		config=config,
		base_dir=base_dir,
		max_articles=max_articles,
		force=force,
		skip_crawl=skip_crawl,
	)
	if context["health_snapshot"].failed_nodes:
		raise RuntimeError("; ".join(context["health_snapshot"].error_summaries) or "pipeline graph failed")
	crawl_result = context.get("crawl_result", CrawlResult(outputs=[]))
	clean_result = context["clean_result"]
	validate_result = context["validate_result"]
	store_stats = context["store_stats"]
	process_stats = context["process_stats"]
	export_result = context["export_result"]

	return PipelineRunResult(
		crawl=crawl_result,
		clean=clean_result,
		validate=validate_result,
		store=store_stats,
		export=export_result,
		process=process_stats,
	)


async def run_pipeline_via_registry(
	*,
	config: AppConfig,
	base_dir: Path,
	max_articles: int | None = None,
	force: bool = False,
	skip_crawl: bool = False,
) -> PipelineHealthSnapshot:
	"""Run the built-in data pipeline graph and return its health snapshot."""

	snapshot, _ = await _run_data_pipeline_graph(
		config=config,
		base_dir=base_dir,
		max_articles=max_articles,
		force=force,
		skip_crawl=skip_crawl,
	)
	return snapshot
