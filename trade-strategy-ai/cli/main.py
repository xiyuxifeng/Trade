from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path

import typer
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.agents.manager_agent.agent import ManagerAgent
from src.common.config import load_app_config
from src.common.logger import configure_logging


app = typer.Typer(add_completion=False)


_DEFAULT_CONFIG_YAML = """timezone: Asia/Shanghai
run_mode: interactive

schedule:
  enable: false
  pre_market_time: "08:30"
  after_close_time: "15:30"

evaluation:
  min_expected_return: 0.0
  loss_trigger: true

data:
  providers: ["mock"]
  mock_prices:
    000001.SZ: 10.0
    510300.SH: 3.5

storage:
  output_dir: data/processed/phase0

llm:
  provider: null
  model: null
  url: null
  api_key: null

traders:
  - trader_id: trader_a
    display_name: Trader A
    article_sources:
      urls: []
      rss: []
      site_type: null
      crawl_frequency_minutes: null
    trade_log_sources:
      csv_paths: []
    watchlist: ["000001.SZ", "510300.SH"]
    default_target_pct: 0.05
    default_stop_pct: 0.03
"""


def _parse_date(value: str | None) -> date:
	if not value:
		return date.today()
	return datetime.strptime(value, "%Y-%m-%d").date()  # noqa: DTZ007


def _project_base_dir(config_path: Path) -> Path:
	# Heuristic: if config is under ./config/, base dir is its parent.
	if config_path.parent.name == "config":
		return config_path.parent.parent
	return config_path.parent


@app.command("init-config")
def init_config(
	dest: Path = typer.Option(
		Path("config/app.yaml"),
		help="生成配置文件到该路径",
	),
	force: bool = typer.Option(False, help="覆盖已存在文件"),
):
	if dest.exists() and not force:
		typer.echo(f"Config already exists: {dest}")
		raise typer.Exit(code=1)

	dest.parent.mkdir(parents=True, exist_ok=True)
	dest.write_text(_DEFAULT_CONFIG_YAML, encoding="utf-8")
	typer.echo(f"Wrote config: {dest}")


@app.command("run-pre-market")
def run_pre_market(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	as_of: str | None = typer.Option(None, help="日期 YYYY-MM-DD，默认今天"),
	force: bool = typer.Option(False, help="强制重跑并覆盖输出"),
	export_html: bool = typer.Option(False, help="同时导出 HTML 日报"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	configure_logging(log_level)
	loaded = load_app_config(config)
	base_dir = _project_base_dir(loaded.config_path)

	mgr = ManagerAgent(config=loaded.config, base_dir=base_dir)
	as_of_date = _parse_date(as_of)

	report = asyncio.run(mgr.run_pre_market(as_of_date=as_of_date, force=force))
	typer.echo(f"Daily report written. ideas={len(report.ideas)}")
	if export_html:
		html_path = mgr.export_daily_report_html(report=report)
		typer.echo(f"Daily report HTML written: {html_path}")
	typer.echo(f"Output dir: {mgr.output_dir}")


@app.command("run-after-close")
def run_after_close(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	as_of: str | None = typer.Option(None, help="日期 YYYY-MM-DD，默认今天"),
	force: bool = typer.Option(False, help="强制重跑并覆盖输出"),
	export_html: bool = typer.Option(False, help="同时导出 HTML 考核报告"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	configure_logging(log_level)
	loaded = load_app_config(config)
	base_dir = _project_base_dir(loaded.config_path)

	mgr = ManagerAgent(config=loaded.config, base_dir=base_dir)
	as_of_date = _parse_date(as_of)

	result = asyncio.run(mgr.run_after_close(as_of_date=as_of_date, force=force))
	typer.echo(f"Evaluation written. items={len(result.evaluations)}")
	if export_html:
		html_path = mgr.export_evaluation_html(result=result)
		typer.echo(f"Evaluation HTML written: {html_path}")
	typer.echo(f"Output dir: {mgr.output_dir}")


@app.command("scheduler-start")
def scheduler_start(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	"""Start a simple scheduler based on config.schedule.*.

	Note: Phase 0 scheduler is optional; manual CLI runs are recommended first.
	"""

	configure_logging(log_level)
	loaded = load_app_config(config)
	base_dir = _project_base_dir(loaded.config_path)
	cfg = loaded.config

	if not cfg.schedule.enable:
		typer.echo("schedule.enable=false, scheduler will not start")
		raise typer.Exit(code=1)

	if not cfg.schedule.pre_market_time or not cfg.schedule.after_close_time:
		typer.echo("schedule.pre_market_time / schedule.after_close_time must be set")
		raise typer.Exit(code=2)

	mgr = ManagerAgent(config=cfg, base_dir=base_dir)

	scheduler = BlockingScheduler(timezone=cfg.timezone)

	pre_h, pre_m = cfg.schedule.pre_market_time.split(":")
	after_h, after_m = cfg.schedule.after_close_time.split(":")

	def _run_pre_market_job() -> None:
		asyncio.run(mgr.run_pre_market(as_of_date=date.today(), force=False))

	def _run_after_close_job() -> None:
		asyncio.run(mgr.run_after_close(as_of_date=date.today(), force=False))

	scheduler.add_job(
		_run_pre_market_job,
		CronTrigger(hour=int(pre_h), minute=int(pre_m)),
		name="pre_market",
		replace_existing=True,
	)
	scheduler.add_job(
		_run_after_close_job,
		CronTrigger(hour=int(after_h), minute=int(after_m)),
		name="after_close",
		replace_existing=True,
	)

	typer.echo(
		f"Scheduler started. pre_market={cfg.schedule.pre_market_time} after_close={cfg.schedule.after_close_time}"
	)
	typer.echo(f"Output dir: {mgr.output_dir}")
	scheduler.start()


def main() -> None:
	app()


if __name__ == "__main__":
	main()
