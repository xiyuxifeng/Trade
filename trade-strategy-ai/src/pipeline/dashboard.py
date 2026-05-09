from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.common.config import AppConfig, load_app_config
from src.common.paths import resolve_project_path
from src.db.session import get_session_factory as async_session_factory
from src.alerting.models import AlertLevel
from src.pipeline.dashboard_models import DashboardReport
from src.pipeline.dashboard_service import DashboardService
from src.pipeline.dashboard_renderers import CLIRenderer, HTMLRenderer
from src.services.dashboard_service import DashboardService as DashboardCommandService


def load_config() -> AppConfig:
    loaded = load_app_config("config/app.yaml")
    return loaded.config


async def build_report(settings: AppConfig) -> DashboardReport:
    report_dir = resolve_project_path("data/processed/pipeline/anomaly")
    dashboard_cfg = getattr(settings, "dashboard", None) or {}

    freshness_threshold = dashboard_cfg.get("freshness_threshold_hours", 24.0)
    anomaly_threshold = dashboard_cfg.get("anomaly_rate_threshold", 5.0)
    max_details = dashboard_cfg.get("max_anomaly_details", 20)

    async with async_session_factory()() as session:
        service = DashboardService(
            session=session,
            report_dir=report_dir,
            freshness_threshold_hours=freshness_threshold,
            anomaly_rate_threshold=anomaly_threshold,
            max_anomaly_details=max_details,
        )
        return await service.build_report()


@click.command()
@click.option("--mode", type=click.Choice(["cli", "html", "both"]), default="cli", help="输出模式")
@click.option("--output", type=click.Path(path_type=Path), default=None, help="HTML 输出路径")
@click.option("--config", type=click.Path(path_type=Path), default=None, help="配置文件路径")
def main(mode: str, output: Path | None, config: Path | None):
    """数据监控 Dashboard CLI"""
    config_path = config or Path("config/app.yaml")
    result = asyncio.run(DashboardCommandService().build_report(config_path=config_path, mode=mode, output=output))

    if mode in ("html", "both") and result.payload.get("html_path"):
        click.echo(f"HTML 报告已生成: {result.payload['html_path']}")

    if result.payload.get("exit_code", 0):
        sys.exit(result.payload["exit_code"])


if __name__ == "__main__":
    main()
