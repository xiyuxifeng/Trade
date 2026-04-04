from __future__ import annotations

from pathlib import Path

import typer

from src.agents.data_agent.skills.crawl_blog import run_crawl
from src.common.config import load_app_config
from src.common.logger import configure_logging


app = typer.Typer(add_completion=False)


def _project_base_dir(config_path: Path) -> Path:
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


def run_crawl_command(*, config_path: Path, max_articles: int | None = None) -> list[str]:
    loaded = load_app_config(config_path)
    return run_crawl(
        loaded.config,
        base_dir=_project_base_dir(loaded.config_path),
        max_articles=max_articles,
    )


@app.command("crawl")
def crawl(
    config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
    max_articles: int | None = typer.Option(None, help="每个作者最多抓取文章数"),
    log_level: str = typer.Option("INFO", help="日志级别"),
) -> None:
    configure_logging(log_level)
    for line in run_crawl_command(config_path=config, max_articles=max_articles):
        typer.echo(line)
