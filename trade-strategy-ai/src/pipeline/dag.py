from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.agents.data_agent.skills.store_db import StoreStats, store_articles_jsonl_to_db
from src.common.config import AppConfig
from src.common.utils import ensure_dir
from src.pipeline.tasks.clean_task import CleanResult, run_clean_task
from src.pipeline.tasks.crawl_task import CrawlResult, run_crawl_task
from src.pipeline.tasks.validate_task import ValidateResult, run_validate_task


@dataclass(slots=True)
class PipelineRunResult:
	crawl: CrawlResult
	clean: CleanResult
	validate: ValidateResult
	store: StoreStats


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


async def run_pipeline(
	*,
	config: AppConfig,
	base_dir: Path,
	max_articles: int | None = None,
	force: bool = False,
	skip_crawl: bool = False,
) -> PipelineRunResult:
	default_pipeline_state_dir(base_dir=base_dir)

	crawl_result = CrawlResult(outputs=[])
	if not skip_crawl:
		crawl_result = run_crawl_task(config=config, base_dir=base_dir, max_articles=max_articles)

	crawl_paths = discover_crawl_jsonl_paths(base_dir=base_dir, config=config)
	clean_result = run_clean_task(base_dir=base_dir, input_paths=crawl_paths, force=force)
	validate_result = run_validate_task(base_dir=base_dir, input_paths=clean_result.cleaned_paths, force=force)
	store_stats = await store_articles_jsonl_to_db(base_dir=base_dir, jsonl_paths=validate_result.validated_paths)

	return PipelineRunResult(
		crawl=crawl_result,
		clean=clean_result,
		validate=validate_result,
		store=store_stats,
	)
