from __future__ import annotations

import asyncio
from datetime import date, datetime
import os
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from cli.crawl import run_crawl_command
from src.agents.manager_agent.agent import ManagerAgent
from config.settings import get_settings
from src.common.config import apply_database_config_to_env, load_app_config
from src.common.logger import configure_logging
from src.common.akshare_tool import AkshareDailyRequest, AkshareMarketDataTool
from src.common.utils import ensure_dir
from src.pipeline.dag import run_pipeline
from src.agents.data_agent.skills.extract_article_metadata import extract_and_store_metadata
from src.persona.cluster_builder import build_clusters_from_db
from src.persona.market_state import DailySeriesSource, classify_market_state, load_daily_close_series
from src.persona.sample import build_sample_clusters_file
from src.persona.storage import write_persona_clusters_file


app = typer.Typer(add_completion=False)


_DEFAULT_CONFIG_YAML = """## trade-strategy-ai 配置文件（YAML）
## - 配置加载支持环境变量展开：例如 "${TGB_COOKIE}"
## - 建议不要把 Cookie/API Key 明文写入仓库，优先用环境变量注入

# 数据库（推荐：本机安装 PostgreSQL；Docker 仅作为可选方案）
database:
	# SQLAlchemy Async URL（示例：postgresql+asyncpg://user:pass@localhost:5432/trade_strategy_ai）
	# 若不填写（null），则使用 .env / 环境变量中的 DATABASE_URL（或 Settings 默认值）。
	url: null
	echo: false
	pool_size: 10
	max_overflow: 20
	pool_timeout: 30
	pool_recycle: 1800

# 时区（影响调度时间解析）
timezone: Asia/Shanghai

# 运行模式：interactive（手动/本地验证） / service（长期运行服务，后续可扩展）
run_mode: interactive

schedule:
	# 是否启用定时调度（Phase 0 默认 false，仅手动跑）
	enable: false
	# 盘前时间（HH:MM，按 timezone 解释）
	pre_market_time: "08:30"
	# 盘后时间（HH:MM，按 timezone 解释）
	after_close_time: "15:30"

evaluation:
	# 收益率不达标阈值（如 0.01 表示 1%）
	min_expected_return: 0.0
	# 是否“亏损即触发复盘”
	loss_trigger: true

data:
	# 数据提供者列表：Phase 0 默认 mock；后续可扩展为 akshare/tushare 等
	providers: ["mock"]
	# mock_prices 用于演示闭环，后续可接入真实行情
	mock_prices:
		000001.SZ: 10.0
		510300.SH: 3.5

crawl:
	# 站点认证信息（按域名/站点名分组）
	auth: {}
	# 示例（淘股吧，建议通过环境变量注入 Cookie）：
	# auth:
	#   tgb.cn:
	#     mode: cookie
	#     cookie: "${TGB_COOKIE}"

	throttling:
		# 每次请求之间的随机间隔区间（秒）
		min_interval_seconds: 1.0
		max_interval_seconds: 2.0
		# 失败时退避序列（秒），按序重试
		backoff_seconds: [5, 15, 30]

	# 抓取来源列表（支持同站点多作者增量抓取）
	sources: []
	# 示例（建议把 trader_id 绑定到 traders[].trader_id，便于后续聚类/路由）：
	# sources:
	#   - source: tgb
	#     site: tgb.cn
	#     trader_id: trader_a
	#     author_id: "10461311"
	#     author_name: "某交易员"
	#     list_url: "https://www.tgb.cn/xxxxx"
	#     enabled: true

storage:
	# 输出目录（日报、persona_route 等产物默认写到这里）
	output_dir: data/processed/phase0

llm:
	# 大模型提供商（预留）：openai/anthropic/...
	provider: null
	# 模型名（随 provider 而定）
	model: null
	# 第三方大模型 API Base URL（可选）
	url: null
	# 大模型 API Key（建议通过环境变量注入）
	api_key: null

persona:
	# 是否启用 Persona Router
	enable: false
	# 路由目标：return_max（收益最大化）；后续可扩展 risk_min
	objective: "return_max"
	# clusters 文件路径（可用 persona-init-sample 生成样例）
	clusters_path: data/processed/persona/clusters.sample.json
	# 输出 Top-K（默认 2：Top-1 + Top-2 备选）
	top_k: 2
	# 可选：直接指定 MarketState JSON
	market_state_path: null
	# 基准指数/ETF：用于从日线推断 MarketState（regime/vol）
	market_state_benchmark_symbol: "510300.SH"
	# 基准日线 CSV；为空时可用 market-state-build --from-akshare 拉取
	market_state_benchmark_csv: null

traders:
	- trader_id: trader_a
		# 展示名（用于报告展示）
		display_name: Trader A
		article_sources:
			urls: []
			rss: []
			site_type: null
			crawl_frequency_minutes: null
		trade_log_sources:
			csv_paths: []
		# 关注列表
		watchlist: ["000001.SZ", "510300.SH"]
		# 默认止盈/止损
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


def _alembic_config(project_root: Path) -> Config:
	ini_path = project_root / "src" / "db" / "migrations" / "alembic.ini"
	if not ini_path.exists():
		raise FileNotFoundError(f"alembic.ini not found: {ini_path}")
	return Config(str(ini_path))


@app.command("crawl")
def crawl(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	max_articles: int | None = typer.Option(None, help="每个作者最多抓取文章数"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	configure_logging(log_level)
	for line in run_crawl_command(config_path=config, max_articles=max_articles):
		typer.echo(line)


@app.command("db-check")
def db_check(
	config: Path | None = typer.Option(None, help="从配置文件读取 database.url（并同步到 DATABASE_URL）"),
	database_url: str | None = typer.Option(None, help="覆盖 DATABASE_URL（默认读取环境变量/Settings）"),
) -> None:
	"""Async SQLAlchemy 连接可用性验证。"""
	if config is not None:
		loaded = load_app_config(config)
		apply_database_config_to_env(loaded.config)
	url = database_url or os.getenv("DATABASE_URL") or get_settings().database_url

	async def _run() -> None:
		engine = create_async_engine(url, echo=False)
		try:
			async with engine.connect() as conn:
				res = await conn.execute(text("SELECT 1"))
				typer.echo(f"DB OK: {res.scalar_one()}")
		finally:
			await engine.dispose()

	asyncio.run(_run())


@app.command("db-migrate")
def db_migrate(
	config: Path | None = typer.Option(None, help="从配置文件读取 database.url（并同步到 DATABASE_URL）"),
	project_root: Path = typer.Option(Path("."), help="trade-strategy-ai 项目根目录"),
	revision: str = typer.Option("head", help="目标版本（默认 head）"),
) -> None:
	"""执行 Alembic 迁移（upgrade）。"""
	if config is not None:
		loaded = load_app_config(config)
		apply_database_config_to_env(loaded.config)
	cfg = _alembic_config(project_root.resolve())
	command.upgrade(cfg, revision)
	typer.echo(f"Migrated to: {revision}")


@app.command("pipeline-run")
def pipeline_run(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	max_articles: int | None = typer.Option(None, help="每个作者最多抓取文章数"),
	force: bool = typer.Option(False, help="强制重跑 clean/validate 产物"),
	skip_crawl: bool = typer.Option(False, help="跳过 crawl（直接用已有 articles.jsonl）"),
	log_level: str = typer.Option("INFO", help="日志级别"),
) -> None:
	"""一键跑通 crawl → clean → validate → store。"""
	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	result = asyncio.run(
		run_pipeline(
			config=loaded.config,
			base_dir=base_dir,
			max_articles=max_articles,
			force=force,
			skip_crawl=skip_crawl,
		)
	)

	typer.echo("Pipeline done")
	typer.echo(f"crawl={result.crawl.outputs}")
	typer.echo(
		f"store inserted={result.store.inserted_articles} updated={result.store.updated_articles} dup_skipped={result.store.skipped_duplicates}"
	)


@app.command("extract-articles")
def extract_articles(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	limit: int = typer.Option(20, help="最多抽取多少篇（processed_at 为空的）"),
	log_level: str = typer.Option("INFO", help="日志级别"),
) -> None:
	"""LLM 抽取 v0：articles → ArticleMetadata.strategy_rules/preconditions。"""
	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	stats = asyncio.run(extract_and_store_metadata(config=loaded.config, base_dir=base_dir, limit=limit))
	typer.echo(
		f"Extract done scanned={stats.scanned} extracted={stats.extracted} skipped={stats.skipped} failed={stats.failed}"
	)


@app.command("clusters-build")
def clusters_build(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	dest: Path = typer.Option(Path("data/processed/persona/clusters.real.json"), help="输出 clusters 文件"),
	max_articles: int | None = typer.Option(None, help="最多使用多少篇已抽取文章"),
	log_level: str = typer.Option("INFO", help="日志级别"),
) -> None:
	"""从真实抽取数据（DB）生成 StyleClusters。"""
	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	full_dest = dest if dest.is_absolute() else (base_dir / dest)
	full_dest.parent.mkdir(parents=True, exist_ok=True)
	written, stats = asyncio.run(
		build_clusters_from_db(config=loaded.config, dest=full_dest, max_articles=max_articles)
	)
	typer.echo(f"Wrote clusters: {written}")
	typer.echo(f"scanned={stats.scanned_articles} used={stats.used_articles} clusters={stats.clusters_built}")


async def _e2e_regression_async(
	config: Path,
	max_articles: int | None,
	extract_limit: int,
	clusters_dest: Path,
	base_dir: Path,
	loaded_cfg,
) -> None:
	# 2) pipeline
	await run_pipeline(
		config=loaded_cfg.config,
		base_dir=base_dir,
		max_articles=max_articles,
		force=True,
		skip_crawl=False,
	)

	# 3) extract
	await extract_and_store_metadata(config=loaded_cfg.config, base_dir=base_dir, limit=extract_limit)

	# 4) build clusters
	full_clusters = clusters_dest if clusters_dest.is_absolute() else (base_dir / clusters_dest)
	ensure_dir(full_clusters.parent)
	await build_clusters_from_db(config=loaded_cfg.config, dest=full_clusters)

	# 5) run pre-market with persona enabled
	cfg2 = loaded_cfg.config.model_copy(deep=True)
	cfg2.persona.enable = True
	cfg2.persona.clusters_path = str(full_clusters.relative_to(base_dir))

	mgr = ManagerAgent(config=cfg2, base_dir=base_dir)
	report = await mgr.run_pre_market(as_of_date=date.today(), force=True)
	html_path = mgr.export_daily_report_html(report=report)
	typer.echo(f"E2E OK. DailyReport ideas={len(report.ideas)}")
	typer.echo(f"HTML: {html_path}")


@app.command("e2e-regression")
def e2e_regression(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	max_articles: int | None = typer.Option(10, help="每个作者最多抓取文章数"),
	extract_limit: int = typer.Option(10, help="抽取篇数上限"),
	clusters_dest: Path = typer.Option(Path("data/processed/persona/clusters.real.json"), help="clusters 输出路径"),
	log_level: str = typer.Option("INFO", help="日志级别"),
) -> None:
	"""端到端回归：crawl → store_db → extract → build_clusters → run-pre-market(+HTML)。"""
	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	# 1) migrate
	cfg = _alembic_config(base_dir)
	command.upgrade(cfg, "head")

	# 2-5) run all async steps in a single event loop
	asyncio.run(_e2e_regression_async(
		config=config,
		max_articles=max_articles,
		extract_limit=extract_limit,
		clusters_dest=clusters_dest,
		base_dir=base_dir,
		loaded_cfg=loaded,
	))


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


@app.command("persona-init-sample")
def persona_init_sample(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	dest: Path | None = typer.Option(
		None,
		help="输出 clusters 文件路径（默认使用 config.persona.clusters_path）",
	),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	"""生成一份可运行的样例 persona clusters 文件。

	在爬虫/抽取未完成前，用该样例文件即可跑通 persona router 的端到端闭环。
	"""

	configure_logging(log_level)
	loaded = load_app_config(config)
	cfg = loaded.config

	trader_ids = [t.trader_id for t in cfg.traders]
	clusters = build_sample_clusters_file(trader_ids=trader_ids)

	path = dest
	if path is None:
		if cfg.persona.clusters_path:
			path = Path(cfg.persona.clusters_path)
		else:
			path = Path("data/processed/persona/clusters.sample.json")

	written = write_persona_clusters_file(path=path, data=clusters)
	typer.echo(f"Wrote sample clusters: {written}")
	typer.echo("Next: set persona.enable=true and run run-pre-market")


@app.command("market-state-build")
def market_state_build(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	as_of: str | None = typer.Option(None, help="日期 YYYY-MM-DD，默认今天"),
	dest: Path = typer.Option(Path("data/processed/persona/market_state.json"), help="输出 MarketState JSON"),
	from_akshare: bool = typer.Option(False, help="当未配置 benchmark_csv 时，尝试从 AkShare 拉取日线数据"),
	cache_csv: bool = typer.Option(True, help="从 AkShare 拉取后是否缓存为 CSV（写入 benchmark_csv 或默认路径）"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	"""从指数/ETF 日线 CSV 构建 MarketState(regime/vol) 并输出 JSON。

	需要在 config.persona.market_state_benchmark_csv 指定 CSV 路径（列：date,close）。
	"""

	configure_logging(log_level)
	loaded = load_app_config(config)
	cfg = loaded.config
	as_of_date = _parse_date(as_of)

	if not cfg.persona.market_state_benchmark_symbol:
		typer.echo("persona.market_state_benchmark_symbol is not set")
		raise typer.Exit(code=3)

	base_dir = _project_base_dir(loaded.config_path)

	# Prefer CSV if configured
	ms = None
	if cfg.persona.market_state_benchmark_csv:
		csv_path = Path(cfg.persona.market_state_benchmark_csv)
		if not csv_path.is_absolute():
			csv_path = base_dir / csv_path
		src = DailySeriesSource(symbol=cfg.persona.market_state_benchmark_symbol, csv_path=csv_path)
		df = load_daily_close_series(src)
		ms = classify_market_state(as_of_date=as_of_date, daily_df=df, symbol=src.symbol)
	elif from_akshare:
		tool = AkshareMarketDataTool()
		etf_df = tool.fetch_etf_daily_em(
			AkshareDailyRequest(symbol=cfg.persona.market_state_benchmark_symbol)
		)
		if cache_csv:
			# If config has no csv path, write to default under processed/persona
			csv_path = (
				Path(cfg.persona.market_state_benchmark_csv)
				if cfg.persona.market_state_benchmark_csv
				else Path("data/processed/persona") / f"{cfg.persona.market_state_benchmark_symbol}_daily.csv"
			)
			if not csv_path.is_absolute():
				csv_path = base_dir / csv_path
			tool.write_daily_csv(df=etf_df, dest_path=csv_path)
		ms = classify_market_state(
			as_of_date=as_of_date,
			daily_df=etf_df,
			symbol=cfg.persona.market_state_benchmark_symbol,
		)
	else:
		typer.echo("persona.market_state_benchmark_csv is not set; pass --from-akshare or set benchmark_csv")
		raise typer.Exit(code=2)

	assert ms is not None

	full_dest = dest if dest.is_absolute() else (base_dir / dest)
	full_dest.parent.mkdir(parents=True, exist_ok=True)
	full_dest.write_text(ms.model_dump_json(indent=2), encoding="utf-8")
	typer.echo(f"Wrote MarketState: {full_dest}")
	typer.echo(f"regime={ms.regime} vol={ms.volatility}")


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
