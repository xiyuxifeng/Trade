from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.common.config import AppConfig, load_app_config
from src.db.session import get_session_factory as async_session_factory
from src.pipeline.dashboard_models import DashboardReport
from src.pipeline.dashboard_service import DashboardService
from src.pipeline.dashboard_renderers import CLIRenderer, HTMLRenderer


def load_config() -> AppConfig:
    loaded = load_app_config("config/app.yaml")
    return loaded.config


async def build_report(settings: AppConfig) -> DashboardReport:
    report_dir = Path("data/processed/pipeline/anomaly")
    dashboard_cfg = getattr(settings, "dashboard", None) or {}

    freshness_threshold = dashboard_cfg.get("freshness_threshold_hours", 24.0)
    anomaly_threshold = dashboard_cfg.get("anomaly_rate_threshold", 5.0)
    max_details = dashboard_cfg.get("max_anomaly_details", 20)

    async with async_session_factory() as session:
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
    settings = load_config()

    report: DashboardReport = asyncio.run(build_report(settings))

    if mode in ("cli", "both"):
        renderer = CLIRenderer()
        renderer.render(report)

    if mode in ("html", "both"):
        template_path = Path("src/reporting/templates/dashboard.html")
        if output is None:
            output = Path("data/processed/dashboard/dashboard.html")
        html_renderer = HTMLRenderer(template_path, output)
        result_path = html_renderer.render(report)
        click.echo(f"HTML 报告已生成: {result_path}")

    # 如果有关键告警，返回非零退出码
    critical_alerts = [a for a in report.alerts if "[CRITICAL]" in a]
    if critical_alerts:
        sys.exit(1)


if __name__ == "__main__":
    main()
