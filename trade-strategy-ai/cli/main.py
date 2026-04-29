from __future__ import annotations

import asyncio
import json
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
from src.pipeline.tasks.clean_task import run_clean_task, run_clean_from_db_task
from src.pipeline.tasks.validate_task import run_validate_task
from src.pipeline.tasks.process_tasks import run_process_tasks
from src.pipeline.tasks.export_task import run_export_task
from src.pipeline.tasks.crawl_task import run_crawl_task
from src.pipeline.tasks.stock_info_task import run_stock_info_update
from src.agents.data_agent.skills.store_db import store_articles_jsonl_to_db
from src.agents.data_agent.skills.extract_article_metadata import extract_and_store_metadata
from src.agents.data_agent.skills.import_trade_logs import (
	import_trade_logs_from_csv,
	import_trade_logs_from_excel,
	import_trade_logs_from_html,
	import_trade_logs_from_pdf,
	store_trade_logs,
)
from src.persona.cluster_builder import build_clusters_from_db
from src.persona.market_state import DailySeriesSource, classify_market_state, load_daily_close_series
from src.persona.sample import build_sample_clusters_file
from src.persona.storage import write_persona_clusters_file
from src.market_data.service import MarketDataCache, MarketDataSyncService
from src.backup.service import backup_project_state, restore_project_state
from src.trader_profile.service import build_trader_profiles, default_profiles_path, write_trader_profiles_file
from scripts.init_db import init_db
from scripts.seed_data import seed_project_data


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
	# market_data_cache_dir 用于存放 AkShare 同步后的标准化日线缓存
	market_data_cache_dir: data/processed/market_data

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

# API 服务配置
api:
	host: "0.0.0.0"
	port: 8000
	timeout_seconds: 300  # 5分钟，0 表示不限制
	auth:
		enabled: true
		api_keys:
			[]

# Kaipan 开盘啦私有接口配置
kaipan:
	# 数据存储根目录
	data_dir: data/kaipan
	# Schema 文件目录
	schema_dir: src/providers/kaipan_schema
	# 可选鉴权参数（建议通过环境变量注入）
	token: null
	user_id: null
	# 默认请求头，模拟 Android 客户端
	default_headers:
		Content-Type: application/x-www-form-urlencoded; charset=UTF-8
		User-Agent: Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)
		Connection: Keep-Alive
		Accept-Encoding: gzip
	# 抓取时间表（可配置）
	fetch_schedule:
		pre_market: "9:25"    # 盘前
		post_close: "17:30"   # 盘后
	# 交易日历来源
	trading_calendar:
		source: akshare
	# 简单反爬与重试策略
	min_request_interval_seconds: 3.0
	max_retries: 3
	retry_backoff_seconds: [1.0, 2.0, 4.0]
	retry_status_codes: [403, 429, 500, 502, 503, 504]
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


@app.command("import-trade-logs")
def import_trade_logs(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	csv_path: Path = typer.Option(..., help="交易记录 CSV/XLSX/HTML/PDF 路径"),
	source: str = typer.Option("csv_import", help="交易来源标识"),
	trader_account_map: str | None = typer.Option(None, help="JSON 格式的 trader_id -> account_id 映射"),
	dry_run: bool = typer.Option(False, help="仅解析和校验，不写入数据库"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)

	account_map = json.loads(trader_account_map) if trader_account_map else None
	if account_map is not None and not isinstance(account_map, dict):
		raise typer.BadParameter("trader_account_map must be a JSON object")

	suffix = csv_path.suffix.lower()
	if suffix in {".xlsx", ".xlsm", ".xls"}:
		records, stats = import_trade_logs_from_excel(
			xlsx_path=csv_path,
			source=source,
			trader_account_map=account_map,
		)
	elif suffix in {".html", ".htm"}:
		records, stats = import_trade_logs_from_html(
			html_path=csv_path,
			source=source,
			trader_account_map=account_map,
		)
	elif suffix == ".pdf":
		records, stats = import_trade_logs_from_pdf(
			pdf_path=csv_path,
			source=source,
			trader_account_map=account_map,
		)
	else:
		records, stats = import_trade_logs_from_csv(
			csv_path=csv_path,
			source=source,
			trader_account_map=account_map,
		)
	typer.echo(
		f"Parsed trade logs: rows={stats.rows_seen} imported={len(records)} "
		f"invalid={stats.invalid} duplicates={stats.duplicates}"
	)

	for issue in stats.issues:
		typer.echo(f"{issue.severity.value.upper()}: {issue.code}: {issue.message}")

	if not dry_run:
		imported = asyncio.run(store_trade_logs(records))
		typer.echo(f"Stored trade logs: {imported}")


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
	from_step: str | None = typer.Option(None, help="从指定步骤开始执行（crawl/clean/validate/store/process/export）"),
	use_db: bool = typer.Option(False, help="Crawl 阶段直接写入数据库（raw_articles 表），替代 articles.jsonl 文件"),
	new_version: str | None = typer.Option(None, help="Process 步骤的版本号（如 v2, v3），与 --from-step process 配合使用"),
	log_level: str = typer.Option("INFO", help="日志级别"),
) -> None:
	"""一键跑通 crawl → clean → validate → store。

	使用 --from-step 可以从指定步骤开始，跳过前面的步骤。例如：

	- --from-step clean：从 clean 开始，跳过 crawl
	- --from-step validate：从 validate 开始，跳过 crawl 和 clean
	- --from-step store：从 store 开始，跳过 crawl/clean/validate
	- --from-step process：从 process 开始，跳过前面的步骤

	使用 --new-version 指定 process 步骤的版本号（如 v2, v3）：
	- 需要配合 --from-step process 使用
	- 例如：pipeline-run --from-step process --use-db --new-version v2 --force

	使用 --use-db 可以让 Crawl 阶段直接写入数据库：
	- 替代 articles.jsonl 文件存储
	- 增量抓取状态存储在 crawl_state 表
	"""
	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	process_version = new_version or "v1"

	async def _run_and_cleanup():
		result = await run_pipeline(
			config=loaded.config,
			base_dir=base_dir,
			max_articles=max_articles,
			force=force,
			skip_crawl=skip_crawl,
			from_step=from_step,
			use_db=use_db,
			process_version=process_version,
		)
		return result

	result = asyncio.run(_run_and_cleanup())

	typer.echo("Pipeline done")
	typer.echo(f"crawl={result.crawl.outputs}")
	typer.echo(
		f"store inserted={result.store.inserted_articles} updated={result.store.updated_articles} dup_skipped={result.store.skipped_duplicates}"
	)
	cleanup_stats = result.cleanup_stats
	typer.echo(
		f"cleanup cleaned={len(cleanup_stats.get('cleaned', []))} errors={len(cleanup_stats.get('errors', []))}"
	)
	if cleanup_stats.get("cleaned"):
		for f in cleanup_stats["cleaned"]:
			typer.echo(f"  deleted: {f}")


@app.command("pipeline-step")
def pipeline_step(
	step: str = typer.Argument(..., help="步骤名称: crawl, clean, validate, store, stock_info_update, process, export, cleanup"),
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	max_articles: int | None = typer.Option(None, help="限制处理的文章数量（crawl/clean/validate/store 步骤生效）"),
	force: bool = typer.Option(False, help="强制重新执行（覆盖已有产物）"),
	use_db: bool = typer.Option(False, help="Crawl/Clean 阶段使用数据库模式（crawl: 写入 raw_articles 表；clean: 从 raw_articles 表读取并清洗）"),
	new_version: str | None = typer.Option(None, help="使用新版本号重新提取（如 v2, v3），为 process 步骤专用"),
	log_level: str = typer.Option("INFO", help="日志级别"),
) -> None:
	"""单独执行 Pipeline 中的某个步骤。

	每一步都会自动查找前置步骤产生的中间文件，无需手动指定路径。
	如果前置文件不存在，会给出友好提示。

	示例：
	  python -m cli.main pipeline-step clean --force
	  python -m cli.main pipeline-step store
	  python -m cli.main pipeline-step process --force
	  python -m cli.main pipeline-step crawl --use-db
	  python -m cli.main pipeline-step clean --use-db
	  python -m cli.main pipeline-step crawl --max-articles 50
	"""
	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	STEP_ORDER = ["crawl", "clean", "validate", "store", "stock_info_update", "process", "export", "cleanup"]

	if step not in STEP_ORDER:
		typer.echo(f"无效步骤: {step}")
		typer.echo(f"可选步骤: {', '.join(STEP_ORDER)}")
		raise typer.Exit(code=1)

	# 导入 audit service（store 步骤需要）
	from src.audit.service import AuditService

	def discover_crawl_jsonl_paths_func():
		"""查找 crawl 产生的 articles.jsonl 文件"""
		paths = []
		for src in loaded.config.crawl.sources:
			if not src.enabled:
				continue
			p = base_dir / "data" / "processed" / "crawl" / src.source / src.author_id / "articles.jsonl"
			paths.append(p)
		return paths

	def find_cleaned_paths():
		"""查找 clean 产生的 .cleaned.jsonl 文件"""
		out_dir = base_dir / "data" / "processed" / "pipeline" / "clean"
		if not out_dir.exists():
			return []
		return list(out_dir.glob("*.cleaned.jsonl"))

	def find_validated_paths():
		"""查找 validate 产生的 .validated.jsonl 文件"""
		out_dir = base_dir / "data" / "processed" / "pipeline" / "validate"
		if not out_dir.exists():
			return []
		return list(out_dir.glob("*.validated.jsonl"))

	async def run_step():
		if step == "crawl":
			result = run_crawl_task(config=loaded.config, base_dir=base_dir, max_articles=max_articles, use_db=use_db)
			typer.echo(f"crawl done: {len(result.outputs)} articles (max_articles={max_articles}, use_db={use_db})")
			return result

		elif step == "clean":
			if use_db:
				# 数据库模式：从 raw_articles 表读取并清洗
				existing = find_cleaned_paths()
				if existing and not force:
					typer.echo(f"找到 {len(existing)} 个已清洗文件（跳过处理），使用 --force 强制覆盖")
				result = await run_clean_from_db_task(
					base_dir=base_dir,
					force=force,
					remove_duplicates=False,
					max_articles=max_articles,
				)
				typer.echo(f"clean done: {len(result.cleaned_paths)} files (max_articles={max_articles})")
				return result
			else:
				# 文件模式：从 articles.jsonl 读取并清洗
				crawl_paths = discover_crawl_jsonl_paths_func()
				if not crawl_paths:
					raise RuntimeError(
						"未找到 articles.jsonl 文件。"
						" 请先运行 'pipeline-step crawl' 或 'pipeline-run --from-step clean --skip-crawl'"
					)
				existing = find_cleaned_paths()
				if existing and not force:
					typer.echo(f"找到 {len(existing)} 个已清洗文件（跳过处理），使用 --force 强制覆盖")
				result = run_clean_task(base_dir=base_dir, input_paths=crawl_paths, force=force, max_articles=max_articles)
				typer.echo(f"clean done: {len(result.cleaned_paths)} files (max_articles={max_articles})")
				return result

		elif step == "validate":
			cleaned_paths = find_cleaned_paths()
			if not cleaned_paths:
				raise RuntimeError(
					"未找到 .cleaned.jsonl 文件。"
					" 请先运行 'pipeline-step clean' 或 'pipeline-run --from-step validate'"
				)
			result = run_validate_task(base_dir=base_dir, input_paths=cleaned_paths, force=force, max_articles=max_articles)
			typer.echo(f"validate done: {len(result.validated_paths)} files (max_articles={max_articles})")
			return result

		elif step == "store":
			validated_paths = find_validated_paths()
			if not validated_paths:
				raise RuntimeError(
					"未找到 .validated.jsonl 文件。"
					" 请先运行 'pipeline-step validate' 或 'pipeline-run --from-step store'"
				)
			audit = AuditService()
			result = await store_articles_jsonl_to_db(base_dir=base_dir, jsonl_paths=validated_paths, limit=max_articles)
			typer.echo(
				f"store done: inserted={result.inserted_articles} updated={result.updated_articles} "
				f"dup_skipped={result.skipped_duplicates} tasks_generated={result.generated_tasks} (limit={max_articles})"
			)
			return result

		elif step == "stock_info_update":
			result = await run_stock_info_update(base_dir=base_dir, force=force)
			typer.echo(
				f"stock_info_update done: updated={result.updated} total={result.total} "
				f"inserted={result.inserted} updated_count={result.updated_count} skipped={result.skipped}"
			)
			return result

		elif step == "process":
			pending_path = base_dir / "data" / "processed" / "pipeline" / "pending_tasks.jsonl"
			version = new_version or "v1"
			result = await run_process_tasks(config=loaded.config, force=force, version=version, pending_path=pending_path)
			typer.echo(
				f"process done: processed={result.processed} skipped_dedup={result.skipped_dedup} "
				f"retried={result.retried} failed={result.failed} dead={result.dead}"
			)
			return result

		elif step == "export":
			result = await run_export_task()
			typer.echo(f"export done: duckdb_path={result.duckdb_path}")
			return result

		elif step == "cleanup":
			# cleanup 直接调用 handler，不走 DAG runner（cleanup 不在 data_pipeline 图中）
			from src.pipeline.dag import _build_data_pipeline_handlers
			from src.audit.service import AuditService

			audit = AuditService()
			handlers = _build_data_pipeline_handlers(
				config=loaded.config,
				base_dir=base_dir,
				max_articles=None,
				force=False,
				skip_crawl=False,
				audit=audit,
				from_step="cleanup",
				use_db=False,
			)
			context: dict[str, Any] = {
				"config": loaded.config,
				"base_dir": base_dir,
				"max_articles": None,
				"force": False,
				"skip_crawl": False,
				"from_step": None,
				"use_db": False,
				"audit_service": audit,
			}
			cleanup_result = handlers["cleanup"](context)
			typer.echo(f"cleanup done: cleaned={len(cleanup_result.get('cleaned', []))} errors={len(cleanup_result.get('errors', []))}")
			if cleanup_result.get('cleaned'):
				typer.echo(f"  deleted: {', '.join(cleanup_result['cleaned'])}")
			return cleanup_result

	# 执行步骤
	result = asyncio.run(run_step())
	typer.echo(f"步骤 {step} 执行完成")


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

	stats = asyncio.run(extract_and_store_metadata(config=loaded.config, base_dir=base_dir, total_limit=limit))
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
	await extract_and_store_metadata(config=loaded_cfg.config, base_dir=base_dir, total_limit=extract_limit)

	# 4) build clusters
	full_clusters = clusters_dest if clusters_dest.is_absolute() else (base_dir / clusters_dest)
	ensure_dir(full_clusters.parent)
	await build_clusters_from_db(config=loaded_cfg.config, dest=full_clusters)

	# 4.5) build trader profiles (from metadata + clusters)
	profiles_file = await build_trader_profiles(
		config=loaded_cfg.config,
		base_dir=base_dir,
		clusters_path=full_clusters,
		max_articles_per_trader=max(1, int(extract_limit)),
	)
	profiles_path = default_profiles_path(base_dir=base_dir, config=loaded_cfg.config)
	write_trader_profiles_file(path=profiles_path, data=profiles_file)

	# 5) run pre-market with persona enabled
	cfg2 = loaded_cfg.config.model_copy(deep=True)
	cfg2.persona.enable = True
	cfg2.persona.clusters_path = str(full_clusters.relative_to(base_dir))

	mgr = ManagerAgent(config=cfg2, base_dir=base_dir)
	report = await mgr.run_pre_market(as_of_date=date.today(), force=True)
	html_path = mgr.export_daily_report_html(report=report)
	result = await mgr.run_after_close(as_of_date=date.today(), force=True)
	eval_html_path = mgr.export_evaluation_html(result=result)
	typer.echo(f"E2E OK. DailyReport ideas={len(report.ideas)} evaluation={len(result.evaluations)}")
	typer.echo(f"HTML: {html_path}")
	typer.echo(f"Evaluation HTML: {eval_html_path}")


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
	# 将模板中的制表符归一化为空格，避免生成无效 YAML。
	dest.write_text(_DEFAULT_CONFIG_YAML.replace("\t", "  "), encoding="utf-8")
	typer.echo(f"Wrote config: {dest}")


@app.command("seed-data")
def seed_data(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	"""Import crawl JSONL and trade logs into the local database."""

	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	stats = asyncio.run(seed_project_data(config=loaded.config, base_dir=base_dir))
	typer.echo(f"Seeded articles: {stats.articles_inserted} inserted, {stats.articles_updated} updated")
	typer.echo(f"Seeded trade logs: {stats.trade_logs_imported}")
	typer.echo(f"Article JSONL paths: {len(stats.article_jsonl_paths)}")
	typer.echo(f"Trade log paths: {len(stats.trade_log_paths)}")


@app.command("init-project")
def init_project(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	"""Run migrations and seed local data in one step."""

	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	init_db(project_root=base_dir)
	stats = asyncio.run(seed_project_data(config=loaded.config, base_dir=base_dir))
	typer.echo("Project initialization complete")
	typer.echo(f"Seeded articles: {stats.articles_inserted} inserted, {stats.articles_updated} updated")
	typer.echo(f"Seeded trade logs: {stats.trade_logs_imported}")


@app.command("backup-data")
def backup_data(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	dest: Path | None = typer.Option(None, help="备份目录；未提供则自动生成"),
	include_processed: bool = typer.Option(True, help="是否包含 data/processed"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	"""Back up database tables and processed artifacts into one folder."""

	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	result = asyncio.run(
		backup_project_state(
			base_dir=base_dir,
			backup_dir=dest,
			include_processed=include_processed,
		)
	)
	typer.echo(f"Backup written: {result.backup_dir}")
	typer.echo(f"Tables: {', '.join(result.tables)}")
	typer.echo(f"Processed copied: {result.processed_copied}")


@app.command("restore-data")
def restore_data(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	source: Path = typer.Option(..., help="备份目录路径"),
	include_processed: bool = typer.Option(True, help="是否恢复 data/processed"),
	force: bool = typer.Option(False, help="确认执行破坏性恢复"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	"""Restore database tables and processed artifacts from one backup folder."""

	configure_logging(log_level)
	loaded = load_app_config(config)
	apply_database_config_to_env(loaded.config)
	base_dir = _project_base_dir(loaded.config_path)

	result = asyncio.run(
		restore_project_state(
			base_dir=base_dir,
			backup_dir=source,
			include_processed=include_processed,
			force=force,
		)
	)
	typer.echo(f"Restore completed from: {result.backup_dir}")
	typer.echo(f"Tables: {', '.join(result.tables)}")
	typer.echo(f"Processed restored: {result.processed_restored}")


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


@app.command("list-signals")
def list_signals(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	symbol: str | None = typer.Option(None, help="按标的代码过滤"),
	since: str | None = typer.Option(None, help="过滤起始日期 YYYY-MM-DD"),
	limit: int = typer.Option(100, help="返回数量限制"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	"""列出已存储的信号版本（P4-025）。

	用于查询盘前生成的交易信号及其上下文。
	"""
	configure_logging(log_level)
	loaded = load_app_config(config)
	base_dir = _project_base_dir(loaded.config_path)

	mgr = ManagerAgent(config=loaded.config, base_dir=base_dir)

	# 解析日期
	since_date = None
	if since:
		from datetime import datetime as dt

		since_date = dt.fromisoformat(since).date()

	versions = mgr.signal_versioning.list_versions(
		symbol=symbol,
		since=since_date,
		limit=limit,
	)

	if not versions:
		typer.echo("No signals found.")
		return

	typer.echo(f"Found {len(versions)} signal(s):")
	for v in versions:
		s = v.signal
		typer.echo(
			f"  {s.signal_id} | {s.symbol} | side={s.side.value} | "
			f"confidence={s.confidence:.2f} | {s.metadata.get('trader_id', 'N/A')}"
		)


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
		cache_dir = base_dir / cfg.data.market_data_cache_dir
		cached_csv = MarketDataCache(cache_dir).path_for_symbol(cfg.persona.market_state_benchmark_symbol)
		if cached_csv.exists():
			src = DailySeriesSource(symbol=cfg.persona.market_state_benchmark_symbol, csv_path=cached_csv)
			df = load_daily_close_series(src)
			ms = classify_market_state(as_of_date=as_of_date, daily_df=df, symbol=src.symbol)
		else:
			typer.echo("persona.market_state_benchmark_csv is not set; pass --from-akshare or sync cache first")
			raise typer.Exit(code=2)

	assert ms is not None

	full_dest = dest if dest.is_absolute() else (base_dir / dest)
	full_dest.parent.mkdir(parents=True, exist_ok=True)
	full_dest.write_text(ms.model_dump_json(indent=2), encoding="utf-8")
	typer.echo(f"Wrote MarketState: {full_dest}")
	typer.echo(f"regime={ms.regime} vol={ms.volatility}")


@app.command("market-data-sync")
def market_data_sync(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	symbol: list[str] = typer.Option([], "--symbol", help="需要同步的标的，可重复传入"),
	index_symbol: list[str] = typer.Option([], "--index-symbol", help="需要同步的指数，可重复传入"),
	industry_board: list[str] = typer.Option([], "--industry-board", help="需要同步的行业板块，可重复传入"),
	concept_board: list[str] = typer.Option([], "--concept-board", help="需要同步的概念板块，可重复传入"),
	start_date: str | None = typer.Option(None, help="起始日期 YYYY-MM-DD"),
	end_date: str | None = typer.Option(None, help="结束日期 YYYY-MM-DD"),
	adjust: str = typer.Option("", help="复权方式（AkShare 参数）"),
	cache_dir: Path | None = typer.Option(None, help="缓存目录，默认读取 config.data.market_data_cache_dir"),
	log_level: str = typer.Option("INFO", help="日志级别"),
) -> None:
	"""同步市场数据到本地缓存，并为后续 DataAgent/MarketState 复用。"""

	configure_logging(log_level)
	loaded = load_app_config(config)
	cfg = loaded.config
	base_dir = _project_base_dir(loaded.config_path)

	symbols = [item.strip() for item in symbol if item.strip()]
	if not symbols:
		if cfg.persona.market_state_benchmark_symbol:
			symbols = [cfg.persona.market_state_benchmark_symbol]
		else:
			symbols = [s for s in cfg.data.mock_prices.keys() if s.strip()]
	if not symbols:
		symbols = []

	resolved_cache_dir = cache_dir if cache_dir is not None else Path(cfg.data.market_data_cache_dir)
	if not resolved_cache_dir.is_absolute():
		resolved_cache_dir = base_dir / resolved_cache_dir

	service = MarketDataSyncService(cache_dir=resolved_cache_dir)

	results = []
	if symbols:
		results.extend(
			service.sync_symbols(
				symbols=symbols,
				start_date=_parse_date(start_date) if start_date else None,
				end_date=_parse_date(end_date) if end_date else None,
				adjust=adjust,
			)
		)
	for item in index_symbol:
		results.append(
			service.sync_index(
				item,
				start_date=_parse_date(start_date) if start_date else None,
				end_date=_parse_date(end_date) if end_date else None,
			)
		)
	for item in industry_board:
		results.append(
			service.sync_industry_board(
				item,
				start_date=_parse_date(start_date) if start_date else None,
				end_date=_parse_date(end_date) if end_date else None,
			)
		)
	for item in concept_board:
		results.append(
			service.sync_concept_board(
				item,
				start_date=_parse_date(start_date) if start_date else None,
				end_date=_parse_date(end_date) if end_date else None,
			)
		)

	if not results:
		typer.echo("No symbols provided and no default benchmark or mock_prices configured")
		raise typer.Exit(code=2)

	for result in results:
		typer.echo(
			f"{result.symbol}: rows={result.rows_written} latest_close={result.latest_close} cache={result.cache_path}"
		)


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


@app.command("migrate-crawl-state")
def migrate_crawl_state(
	config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
	log_level: str = typer.Option("INFO", help="日志级别"),
):
	"""将 state.json 中的增量抓取状态迁移到 crawl_state 表。

	从 data/processed/crawl/{source}/{author_id}/state.json 读取状态，
	写入数据库的 crawl_state 表。
	"""
	configure_logging(log_level)
	loaded = load_app_config(config)
	base_dir = _project_base_dir(loaded.config_path)

	from datetime import datetime
	from src.db.session import session_scope
	from src.models.crawl_state import CrawlState
	from src.common.utils import read_json
	from sqlalchemy import select

	migrated = 0
	skipped = 0

	for source_cfg in loaded.config.crawl.sources:
		if not source_cfg.enabled:
			continue

		state_dir = base_dir / "data" / "processed" / "crawl" / source_cfg.source / source_cfg.author_id
		state_path = state_dir / "state.json"

		if not state_path.exists():
			typer.echo(f"跳过 {source_cfg.source}/{source_cfg.author_id}: state.json 不存在")
			skipped += 1
			continue

		state_data = read_json(state_path)
		seen_urls = state_data.get("seen_urls", [])
		seen_hashes = state_data.get("seen_hashes", [])
		last_url = state_data.get("last_seen_article_url")
		last_published = state_data.get("last_seen_published_at")

		import asyncio
		async def _upsert():
			nonlocal migrated
			async with session_scope() as session:
				result = await session.execute(
					select(CrawlState).where(
						CrawlState.source == source_cfg.source,
						CrawlState.author_id == source_cfg.author_id
					)
				)
				existing = result.scalar_one_or_none()

				if existing is None:
					state = CrawlState(
						source=source_cfg.source,
						author_id=source_cfg.author_id,
						seen_urls=seen_urls,
						seen_hashes=seen_hashes,
						last_seen_article_url=last_url,
						last_seen_published_at=datetime.fromisoformat(last_published) if last_published else None,
						last_success_article_count=state_data.get("last_success_article_count", 0),
					)
					session.add(state)
				else:
					# 如果数据库中已有数据且更完整，保留数据库版本
					if len(existing.seen_urls or []) >= len(seen_urls):
						typer.echo(f"保留数据库状态 {source_cfg.source}/{source_cfg.author_id}: DB有{len(existing.seen_urls)}条 >= JSON有{len(seen_urls)}条")
						return
					existing.seen_urls = seen_urls
					existing.seen_hashes = seen_hashes
					existing.last_seen_article_url = last_url
					existing.last_seen_published_at = datetime.fromisoformat(last_published) if last_published else None
					existing.last_success_article_count = state_data.get("last_success_article_count", 0)

				typer.echo(f"迁移 {source_cfg.source}/{source_cfg.author_id}: {len(seen_urls)} URLs, {len(seen_hashes)} hashes")
				migrated += 1

		asyncio.run(_upsert())

	typer.echo(f"迁移完成: {migrated} 个源已迁移, {skipped} 个跳过")


# 注册 backtest 子命令（NTL-S6-008）
from cli.backtest import app as backtest_app
app.add_typer(backtest_app, name="backtest")

# 注册 optimize 子命令（S7-001/S7-002）
from cli.optimize import app as optimize_app
app.add_typer(optimize_app, name="optimize")

# 注册 ohlcv 子命令（S7-000）
from cli.ohlcv import app as ohlcv_app
app.add_typer(ohlcv_app, name="ohlcv")


def main() -> None:
	configure_logging()
	app()


if __name__ == "__main__":
	main()
