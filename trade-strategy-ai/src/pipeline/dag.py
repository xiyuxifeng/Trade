from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Callable
from pathlib import Path

from src.audit.service import AuditService, default_dataset_version
from src.agents.data_agent.skills.store_db import StoreStats, store_articles_jsonl_to_db
from src.common.config import AppConfig
from src.common.utils import ensure_dir
from src.pipeline.graph import PipelineGraphRegistry
from src.pipeline.health import PipelineHealthSnapshot
from src.pipeline.runner import PipelineRunner
from src.pipeline.tasks.clean_task import CleanResult, run_clean_task, run_clean_from_db_task
from src.pipeline.tasks.crawl_task import CrawlResult, run_crawl_task
from src.pipeline.tasks.export_task import ExportResult, ExportStats, run_export_task, DUCKDB_PATH
from src.pipeline.tasks.stock_info_task import StockInfoUpdateResult, run_stock_info_update
from src.pipeline.tasks.validate_task import ValidateResult, run_validate_task
from src.pipeline.tasks.process_tasks import ProcessTasksStats, run_process_tasks


@dataclass(slots=True)
class PipelineRunResult:
	crawl: CrawlResult
	clean: CleanResult
	validate: ValidateResult
	store: StoreStats
	stock_info_update: StockInfoUpdateResult
	export: ExportResult
	process: ProcessTasksStats
	cleanup_stats: dict[str, Any] = None

	def __post_init__(self):
		if self.cleanup_stats is None:
			object.__setattr__(self, 'cleanup_stats', {"cleaned": [], "errors": []})


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
	retry_failed: bool,
	audit: AuditService,
	from_step: str | None = None,
	until_step: str | None = None,
	use_db: bool = False,
	process_version: str = "v1",
	progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
	"""Create node handlers for the built-in data pipeline graph.

	Args:
		from_step: 从指定步骤开始执行，之前的步骤会被跳过。可选值: crawl, clean, validate, store, stock_info_update, process, export, cleanup
		until_step: 从指定步骤结束执行，之后的步骤会被跳过。可选值同上。
		use_db: 是否使用数据库模式存储原始数据（Crawl → raw_articles 表）
	"""
	# 步骤优先级
	STEP_ORDER = ["crawl", "clean", "validate", "store", "stock_info_update", "process", "export", "cleanup"]

	def _should_skip(step_name: str) -> bool:
		"""判断是否应该跳过某个步骤。"""
		current_index = STEP_ORDER.index(step_name)
		if from_step is not None:
			if from_step not in STEP_ORDER:
				raise ValueError(f"Invalid from_step: {from_step}. Must be one of {STEP_ORDER}")
			from_index = STEP_ORDER.index(from_step)
			if current_index < from_index:
				return True
		if until_step is not None:
			if until_step not in STEP_ORDER:
				raise ValueError(f"Invalid until_step: {until_step}. Must be one of {STEP_ORDER}")
			until_index = STEP_ORDER.index(until_step)
			if current_index > until_index:
				return True
		return False

	active_steps = [step for step in STEP_ORDER if not _should_skip(step)]
	active_total = len(active_steps)
	active_index_by_step = {step: index + 1 for index, step in enumerate(active_steps)}

	def _emit_progress(step_name: str, *, status: str = "running", current: int | None = None, total: int | None = None, error: str | None = None, current_step: str | None = None, current_dataset: str | None = None, current_trade_date: str | None = None) -> None:
		if progress_callback is None:
			return
		step_total = total if total is not None else active_total
		step_current = current if current is not None else active_index_by_step.get(step_name, 0)
		percent = round((step_current / step_total) * 100, 2) if step_total else 0.0
		progress_callback(
			{
				"job_type": "pipeline-run",
				"stage": step_name,
				"current": step_current,
				"total": step_total,
				"percent": percent,
				"remaining": max(step_total - step_current, 0),
				"current_step": current_step or step_name,
				"current_trade_date": current_trade_date,
				"current_dataset": current_dataset,
				"status": status,
				"error": error,
			}
		)

	def _crawl(context: dict[str, Any]) -> CrawlResult:
		if _should_skip("crawl"):
			result = CrawlResult(outputs=[])
		elif skip_crawl:
			_emit_progress("crawl", status="success")
			result = CrawlResult(outputs=[])
		else:
			_emit_progress("crawl", status="running")
			result = run_crawl_task(config=config, base_dir=base_dir, max_articles=max_articles, use_db=use_db)
			_emit_progress("crawl", status="success")
		context["crawl_result"] = result
		return result

	async def _clean(context: dict[str, Any]) -> CleanResult:
		if _should_skip("clean"):
			# 跳过 clean 时，需要伪造一个 CleanResult 以便后续步骤可以继续
			from src.common.utils import ensure_dir
			out_dir = ensure_dir(base_dir / "data" / "processed" / "pipeline" / "clean")
			cleaned = []
			if use_db:
				# use_db 模式下，clean --use-db 生成的是 all.articles.cleaned.jsonl
				all_cleaned = out_dir / "all.articles.cleaned.jsonl"
				if all_cleaned.exists():
					cleaned.append(all_cleaned)
			else:
				# 文件模式：从 articles.jsonl 路径推断 cleaned 文件路径
				crawl_paths = discover_crawl_jsonl_paths(base_dir=base_dir, config=config)
				for p in crawl_paths:
					cleaned_path = out_dir / (p.parent.name + ".articles.cleaned.jsonl")
					if cleaned_path.exists():
						cleaned.append(cleaned_path)
			context["clean_result"] = CleanResult(cleaned_paths=cleaned, stats_path=out_dir / "clean_stats.json")
			return context["clean_result"]
		_emit_progress("clean", status="running")
		if use_db:
			# 数据库模式：从 raw_articles 表读取并清洗
			result = await run_clean_from_db_task(
				base_dir=base_dir,
				force=force,
				remove_duplicates=False,
				max_articles=max_articles,
			)
		else:
			# 文件模式：从 articles.jsonl 读取并清洗
			crawl_paths = discover_crawl_jsonl_paths(base_dir=base_dir, config=config)
			result = run_clean_task(base_dir=base_dir, input_paths=crawl_paths, force=force, max_articles=max_articles)
		context["clean_result"] = result
		_emit_progress("clean", status="success")
		return result

	def _validate(context: dict[str, Any]) -> ValidateResult:
		if _should_skip("validate"):
			clean_result = context.get("clean_result")
			if clean_result:
				context["validate_result"] = ValidateResult(validated_paths=clean_result.cleaned_paths, report_path=clean_result.stats_path.parent / "validation_report.json")
				return context["validate_result"]
			raise ValueError("Cannot skip validate: clean_result not available")
		_emit_progress("validate", status="running")
		clean_result = context["clean_result"]
		result = run_validate_task(base_dir=base_dir, input_paths=clean_result.cleaned_paths, force=force)
		context["validate_result"] = result
		_emit_progress("validate", status="success")
		return result

	async def _store(context: dict[str, Any]) -> StoreStats:
		if _should_skip("store"):
			context["store_stats"] = StoreStats()
			return context["store_stats"]
		_emit_progress("store", status="running")
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
		_emit_progress("store", status="success")
		return result

	async def _stock_info_update(context: dict[str, Any]) -> StockInfoUpdateResult:
		if _should_skip("stock_info_update"):
			# 返回空的 result，后续步骤可继续
			from src.pipeline.tasks.stock_info_task import StockInfoUpdateResult
			return StockInfoUpdateResult(updated=False)
		_emit_progress("stock_info_update", status="running")
		result = await run_stock_info_update(base_dir=base_dir, force=force)
		context["stock_info_result"] = result
		_emit_progress("stock_info_update", status="success")
		return result

	async def _process(context: dict[str, Any]) -> ProcessTasksStats:
		if _should_skip("process"):
			context["process_stats"] = ProcessTasksStats()
			return context["process_stats"]
		result = await run_process_tasks(
			config=config,
			force=force,
			retry_failed=retry_failed,
			version=process_version,
			progress_callback=progress_callback,
			overall_current=active_index_by_step["process"],
			overall_total=active_total,
		)
		context["process_stats"] = result
		if getattr(result, "fatal_error", None) or int(getattr(result, "failed", 0) or 0) > 0:
			failed_count = int(getattr(result, "failed", 0) or 0)
			fatal_error = getattr(result, "fatal_error", None)
			raise RuntimeError(fatal_error or f"process completed with failures: failed={failed_count}")
		return result

	async def _export(context: dict[str, Any]) -> ExportResult:
		if _should_skip("export"):
			context["export_result"] = ExportResult(stats=ExportStats(), duckdb_path=DUCKDB_PATH)
			return context["export_result"]
		_emit_progress("export", status="running")
		result = await run_export_task()
		context["export_result"] = result
		_emit_progress("export", status="success")
		return result

	def _cleanup(context: dict[str, Any]) -> dict[str, Any]:
		"""清理中间文件，释放存储空间。"""
		if _should_skip("cleanup"):
			context["cleanup_result"] = {"cleaned": [], "errors": []}
			return context["cleanup_result"]
		_emit_progress("cleanup", status="running")

		cleaned: list[str] = []
		errors: list[str] = []

		# 1. 清理 articles.jsonl（crawl 产物）
		if not use_db:
			crawl_paths = discover_crawl_jsonl_paths(base_dir=base_dir, config=config)
			for p in crawl_paths:
				if p.exists():
					try:
						p.unlink()
						cleaned.append(str(p))
					except OSError as exc:
						errors.append(f"Failed to delete {p}: {exc}")

		# 2. 清理 .cleaned.jsonl（clean 产物）
		clean_dir = base_dir / "data" / "processed" / "pipeline" / "clean"
		if clean_dir.exists():
			for p in clean_dir.glob("*.articles.cleaned.jsonl"):
				try:
					p.unlink()
					cleaned.append(str(p))
				except OSError as exc:
					errors.append(f"Failed to delete {p}: {exc}")

		# 3. 清理 .validated.jsonl（validate 产物）
		validate_dir = base_dir / "data" / "processed" / "pipeline" / "validate"
		if validate_dir.exists():
			for p in validate_dir.glob("*.validated.jsonl"):
				try:
					p.unlink()
					cleaned.append(str(p))
				except OSError as exc:
					errors.append(f"Failed to delete {p}: {exc}")

		# 4. 清理 pending_tasks.jsonl（process 消费后残留）
		pending_path = base_dir / "data" / "processed" / "pipeline" / "pending_tasks.jsonl"
		if pending_path.exists():
			try:
				pending_path.unlink()
				cleaned.append(str(pending_path))
			except OSError as exc:
				errors.append(f"Failed to delete {pending_path}: {exc}")

		# 5. 清理 failed_tasks.jsonl（如果存在）
		failed_path = base_dir / "data" / "processed" / "pipeline" / "failed_tasks.jsonl"
		if failed_path.exists():
			try:
				failed_path.unlink()
				cleaned.append(str(failed_path))
			except OSError as exc:
				errors.append(f"Failed to delete {failed_path}: {exc}")

		# 6. 清理 llm_checkpoint.jsonl（如果存在）
		checkpoint_path = base_dir / "data" / "processed" / "pipeline" / "llm_checkpoint.jsonl"
		if checkpoint_path.exists():
			try:
				checkpoint_path.unlink()
				cleaned.append(str(checkpoint_path))
			except OSError as exc:
				errors.append(f"Failed to delete {checkpoint_path}: {exc}")

		result = {"cleaned": cleaned, "errors": errors}
		context["cleanup_result"] = result
		_emit_progress("cleanup", status="success")
		return result

	return {
		"crawl": _crawl,
		"clean": _clean,
		"validate": _validate,
		"store": _store,
		"stock_info_update": _stock_info_update,
		"process": _process,
		"export": _export,
		"cleanup": _cleanup,
	}


async def _run_data_pipeline_graph(
	*,
	config: AppConfig,
	base_dir: Path,
	max_articles: int | None = None,
	force: bool = False,
	skip_crawl: bool = False,
	from_step: str | None = None,
	until_step: str | None = None,
	use_db: bool = False,
	retry_failed: bool = False,
	process_version: str = "v1",
	progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[PipelineHealthSnapshot, dict[str, Any]]:
	"""Run the built-in data pipeline graph and return the snapshot plus context.

	Args:
		from_step: 从指定步骤开始执行，之前的步骤会被跳过。可选值: crawl, clean, validate, store, stock_info_update, process, export, cleanup
		use_db: 是否使用数据库模式存储原始数据（Crawl → raw_articles 表）
		process_version: 抽取版本号，如 "v1", "v2" 等
	"""

	default_pipeline_state_dir(base_dir=base_dir)
	audit = AuditService()
	context: dict[str, Any] = {
		"config": config,
		"base_dir": base_dir,
		"max_articles": max_articles,
		"force": force,
		"skip_crawl": skip_crawl,
		"from_step": from_step,
		"use_db": use_db,
		"retry_failed": retry_failed,
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
			retry_failed=retry_failed,
			audit=audit,
			from_step=from_step,
			until_step=until_step,
			use_db=use_db,
			process_version=process_version,
			progress_callback=progress_callback,
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
	from_step: str | None = None,
	until_step: str | None = None,
	use_db: bool = False,
	retry_failed: bool = False,
	process_version: str = "v1",
	progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> PipelineRunResult:
	_, context = await _run_data_pipeline_graph(
		config=config,
		base_dir=base_dir,
		max_articles=max_articles,
		force=force,
		skip_crawl=skip_crawl,
		from_step=from_step,
		until_step=until_step,
		use_db=use_db,
		retry_failed=retry_failed,
		process_version=process_version,
		progress_callback=progress_callback,
	)
	if context["health_snapshot"].failed_nodes:
		raise RuntimeError("; ".join(context["health_snapshot"].error_summaries) or "pipeline graph failed")
	crawl_result = context.get("crawl_result", CrawlResult(outputs=[]))
	clean_result = context["clean_result"]
	validate_result = context["validate_result"]
	store_stats = context["store_stats"]
	stock_info_result = context.get("stock_info_result", StockInfoUpdateResult(updated=False))
	process_stats = context["process_stats"]
	export_result = context["export_result"]

	return PipelineRunResult(
		crawl=crawl_result,
		clean=clean_result,
		validate=validate_result,
		store=store_stats,
		stock_info_update=stock_info_result,
		export=export_result,
		process=process_stats,
		cleanup_stats=context.get("cleanup_result", {"cleaned": [], "errors": []}),
	)


async def run_pipeline_via_registry(
	*,
	config: AppConfig,
	base_dir: Path,
	max_articles: int | None = None,
	force: bool = False,
	skip_crawl: bool = False,
	from_step: str | None = None,
	use_db: bool = False,
	retry_failed: bool = False,
) -> PipelineHealthSnapshot:
	"""Run the built-in data pipeline graph and return its health snapshot."""

	snapshot, _ = await _run_data_pipeline_graph(
		config=config,
		base_dir=base_dir,
		max_articles=max_articles,
		force=force,
		skip_crawl=skip_crawl,
		from_step=from_step,
		use_db=use_db,
		retry_failed=retry_failed,
	)
	return snapshot
