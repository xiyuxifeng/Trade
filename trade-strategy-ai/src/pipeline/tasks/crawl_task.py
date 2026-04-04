from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.agents.data_agent.skills.crawl_blog import run_crawl
from src.common.config import AppConfig


@dataclass(slots=True)
class CrawlResult:
	outputs: list[str]


def run_crawl_task(*, config: AppConfig, base_dir: Path, max_articles: int | None = None) -> CrawlResult:
	outputs = run_crawl(config, base_dir=base_dir, max_articles=max_articles)
	return CrawlResult(outputs=outputs)
