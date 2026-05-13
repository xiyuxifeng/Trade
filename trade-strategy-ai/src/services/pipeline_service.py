from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from src.agents.data_agent.skills.extract_article_metadata import extract_and_store_metadata
from src.agents.manager_agent.agent import ManagerAgent
from src.common.config import apply_database_config_to_env, load_app_config
from src.persona.cluster_builder import build_clusters_from_db
from src.pipeline.dag import run_pipeline
from src.services.base import BaseService, ServiceResult
from src.trader_profile.service import build_trader_profiles, default_profiles_path, write_trader_profiles_file
from cli.crawl import run_crawl_command


def _project_base_dir(config_path: Path) -> Path:
    """根据配置文件推导项目根目录。"""
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


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
    return value


class PipelineService(BaseService):
    """数据管道、抽取与 e2e 回归的共享服务。"""

    service_name = "pipeline"

    def __init__(
        self,
        *,
        crawl_runner: Callable[..., list[str]] = run_crawl_command,
        pipeline_runner: Callable[..., Any] = run_pipeline,
        extract_metadata_runner: Callable[..., Any] = extract_and_store_metadata,
        build_clusters_runner: Callable[..., Any] = build_clusters_from_db,
        build_trader_profiles_runner: Callable[..., Any] = build_trader_profiles,
        write_trader_profiles_runner: Callable[..., Path] = write_trader_profiles_file,
        manager_factory: Callable[..., ManagerAgent] = ManagerAgent,
    ) -> None:
        self._crawl_runner = crawl_runner
        self._pipeline_runner = pipeline_runner
        self._extract_metadata_runner = extract_metadata_runner
        self._build_clusters_runner = build_clusters_runner
        self._build_trader_profiles_runner = build_trader_profiles_runner
        self._write_trader_profiles_runner = write_trader_profiles_runner
        self._manager_factory = manager_factory

    def crawl(self, *, config_path: str | Path, max_articles: int | None = None) -> ServiceResult:
        """执行文章抓取。"""
        loaded = load_app_config(config_path)
        lines = self._crawl_runner(config_path=loaded.config_path, max_articles=max_articles)
        return ServiceResult(
            status="ok",
            message="crawl completed",
            payload={
                "config_path": str(loaded.config_path),
                "line_count": len(lines),
                "lines": lines,
            },
        )

    async def run_pipeline(
        self,
        *,
        config_path: str | Path,
        max_articles: int | None = None,
        force: bool = False,
        skip_crawl: bool = False,
        from_step: str | None = None,
        use_db: bool = False,
        new_version: str | None = None,
    ) -> ServiceResult:
        """执行完整 pipeline。"""
        loaded = load_app_config(config_path)
        apply_database_config_to_env(loaded.config)
        base_dir = _project_base_dir(loaded.config_path)
        result = await self._pipeline_runner(
            config=loaded.config,
            base_dir=base_dir,
            max_articles=max_articles,
            force=force,
            skip_crawl=skip_crawl,
            from_step=from_step,
            use_db=use_db,
            process_version=new_version or "v1",
        )
        return ServiceResult(
            status="ok",
            message="pipeline completed",
            payload={
                "config_path": str(loaded.config_path),
                "base_dir": str(base_dir),
                "result": _to_plain(result),
            },
        )

    async def run_pipeline_step(
        self,
        *,
        step: str,
        config_path: str | Path,
        max_articles: int | None = None,
        force: bool = False,
        use_db: bool = False,
        new_version: str | None = None,
    ) -> ServiceResult:
        """执行 pipeline 的单步或从指定步骤开始的链路。"""
        return await self.run_pipeline(
            config_path=config_path,
            max_articles=max_articles,
            force=force,
            skip_crawl=False,
            from_step=step,
            use_db=use_db,
            new_version=new_version,
        )

    async def build_clusters(
        self,
        *,
        config_path: str | Path,
        dest: str | Path,
        max_articles: int | None = None,
    ) -> ServiceResult:
        """从数据库构建 persona clusters。"""
        loaded = load_app_config(config_path)
        apply_database_config_to_env(loaded.config)
        base_dir = _project_base_dir(loaded.config_path)
        full_dest = Path(dest)
        if not full_dest.is_absolute():
            full_dest = base_dir / full_dest
        full_dest.parent.mkdir(parents=True, exist_ok=True)
        written, stats = await self._build_clusters_runner(
            config=loaded.config,
            dest=full_dest,
            max_articles=max_articles,
        )
        return ServiceResult(
            status="ok",
            message="clusters completed",
            payload={
                "config_path": str(loaded.config_path),
                "base_dir": str(base_dir),
                "dest": str(written),
                "stats": _to_plain(stats),
            },
        )

    async def build_trader_profiles(
        self,
        *,
        config_path: str | Path,
        clusters_path: str | Path | None = None,
        max_articles_per_trader: int = 50,
    ) -> ServiceResult:
        """构建 trader profile 文件。"""
        loaded = load_app_config(config_path)
        apply_database_config_to_env(loaded.config)
        base_dir = _project_base_dir(loaded.config_path)
        profiles_file = await self._build_trader_profiles_runner(
            config=loaded.config,
            base_dir=base_dir,
            clusters_path=clusters_path,
            max_articles_per_trader=max_articles_per_trader,
        )
        profiles_path = default_profiles_path(base_dir=base_dir, config=loaded.config)
        written = self._write_trader_profiles_runner(path=profiles_path, data=profiles_file)
        return ServiceResult(
            status="ok",
            message="profiles completed",
            payload={
                "config_path": str(loaded.config_path),
                "base_dir": str(base_dir),
                "profiles_path": str(written),
                "profiles": _to_plain(profiles_file),
            },
        )

    async def e2e_regression(
        self,
        *,
        config_path: str | Path,
        max_articles: int | None = 10,
        extract_limit: int = 10,
        clusters_dest: str | Path = "data/processed/persona/clusters.real.json",
    ) -> ServiceResult:
        """串起主链路回归：pipeline -> extract -> clusters -> profiles -> pre/post market。"""
        loaded = load_app_config(config_path)
        apply_database_config_to_env(loaded.config)
        base_dir = _project_base_dir(loaded.config_path)

        pipeline_result = await self._pipeline_runner(
            config=loaded.config,
            base_dir=base_dir,
            max_articles=max_articles,
            force=True,
            skip_crawl=False,
            from_step=None,
            use_db=False,
            process_version="v1",
        )
        extract_stats = await self._extract_metadata_runner(
            config=loaded.config,
            base_dir=base_dir,
            total_limit=extract_limit,
        )
        full_clusters = Path(clusters_dest)
        if not full_clusters.is_absolute():
            full_clusters = base_dir / full_clusters
        full_clusters.parent.mkdir(parents=True, exist_ok=True)
        clusters_path, clusters_stats = await self._build_clusters_runner(
            config=loaded.config,
            dest=full_clusters,
            max_articles=max_articles,
        )
        profiles_file = await self._build_trader_profiles_runner(
            config=loaded.config,
            base_dir=base_dir,
            clusters_path=clusters_path,
            max_articles_per_trader=max(1, int(extract_limit)),
        )
        profiles_path = default_profiles_path(base_dir=base_dir, config=loaded.config)
        written_profiles = self._write_trader_profiles_runner(path=profiles_path, data=profiles_file)

        cfg2 = loaded.config.model_copy(deep=True)
        cfg2.persona.enable = True
        try:
            cfg2.persona.clusters_path = str(full_clusters.relative_to(base_dir))
        except ValueError:
            cfg2.persona.clusters_path = str(full_clusters)
        mgr = self._manager_factory(config=cfg2, base_dir=base_dir)
        report = await mgr.run_pre_market(as_of_date=date.today(), force=True)
        report_html = mgr.export_daily_report_html(report=report)
        evaluation = await mgr.run_after_close(as_of_date=date.today(), force=True)
        evaluation_html = mgr.export_evaluation_html(result=evaluation)

        return ServiceResult(
            status="ok",
            message="e2e regression completed",
            payload={
                "config_path": str(loaded.config_path),
                "base_dir": str(base_dir),
                "pipeline": _to_plain(pipeline_result),
                "extract": _to_plain(extract_stats),
                "clusters_path": str(clusters_path),
                "clusters_stats": _to_plain(clusters_stats),
                "profiles_path": str(written_profiles),
                "daily_report": _to_plain(report),
                "daily_report_html": str(report_html),
                "evaluation": _to_plain(evaluation),
                "evaluation_html": str(evaluation_html),
            },
        )
