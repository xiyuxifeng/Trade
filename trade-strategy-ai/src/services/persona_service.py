from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Callable

from src.common.akshare_tool import AkshareDailyRequest, AkshareMarketDataTool
from src.common.config import load_app_config
from src.market_data.service import MarketDataCache
from src.persona.market_state import DailySeriesSource, classify_market_state, load_daily_close_series
from src.persona.sample import build_sample_clusters_file
from src.persona.schemas import MarketState, PersonaClustersFile
from src.persona.storage import write_persona_clusters_file
from src.services.base import BaseService, ServiceResult


def _project_base_dir(config_path: Path) -> Path:
	"""根据配置文件路径推导项目根目录。"""
	if config_path.parent.name == "config":
		return config_path.parent.parent
	return config_path.parent


def _parse_date_like(value: str | date | None) -> date:
	"""解析日期或日期字符串。"""
	if value is None:
		return date.today()
	if isinstance(value, date):
		return value
	return datetime.strptime(value, "%Y-%m-%d").date()


class PersonaService(BaseService):
	"""Persona 与 MarketState 相关的共享服务。"""

	service_name = "persona"

	def __init__(
		self,
		*,
		akshare_tool_factory: Callable[[], AkshareMarketDataTool] | None = None,
	) -> None:
		self._akshare_tool_factory = akshare_tool_factory

	def _create_akshare_tool(self) -> AkshareMarketDataTool:
		"""创建 AkShare 工具实例。"""
		if self._akshare_tool_factory is not None:
			return self._akshare_tool_factory()
		return AkshareMarketDataTool()

	def build_sample_clusters(
		self,
		*,
		config_path: str | Path,
		dest: str | Path | None = None,
	) -> ServiceResult:
		"""生成可运行的样例 persona clusters 文件。"""
		loaded = load_app_config(config_path)
		base_dir = _project_base_dir(loaded.config_path)
		trader_ids = [t.trader_id for t in loaded.config.traders]
		clusters: PersonaClustersFile = build_sample_clusters_file(trader_ids=trader_ids)

		path = dest
		if path is None:
			if loaded.config.persona.clusters_path:
				path = Path(loaded.config.persona.clusters_path)
			else:
				path = Path("data/processed/persona/clusters.sample.json")
		full_path = Path(path)
		if not full_path.is_absolute():
			full_path = base_dir / full_path

		written = write_persona_clusters_file(path=full_path, data=clusters)
		return ServiceResult(
			status="ok",
			message="sample clusters written",
			payload={
				"config_path": str(loaded.config_path),
				"base_dir": str(base_dir),
				"clusters_path": str(written),
				"trader_count": len(trader_ids),
				"clusters_count": sum(len(items) for items in clusters.clusters_by_trader.values()),
			},
		)

	def build_market_state(
		self,
		*,
		config_path: str | Path,
		as_of: str | date | None = None,
		dest: str | Path = Path("data/processed/persona/market_state.json"),
		from_akshare: bool = False,
		cache_csv: bool = True,
	) -> ServiceResult:
		"""从 benchmark CSV / cache / AkShare 构建 MarketState。"""
		loaded = load_app_config(config_path)
		base_dir = _project_base_dir(loaded.config_path)
		cfg = loaded.config
		as_of_date = _parse_date_like(as_of)

		bench_symbol = getattr(cfg.persona, "market_state_benchmark_symbol", None)
		if not bench_symbol:
			return ServiceResult(
				status="error",
				message="persona.market_state_benchmark_symbol is not set",
				payload={"config_path": str(loaded.config_path), "base_dir": str(base_dir)},
			)

		market_state: MarketState | None = None
		source = ""
		if cfg.persona.market_state_benchmark_csv:
			csv_path = Path(cfg.persona.market_state_benchmark_csv)
			if not csv_path.is_absolute():
				csv_path = base_dir / csv_path
			try:
				src = DailySeriesSource(symbol=bench_symbol, csv_path=csv_path)
				df = load_daily_close_series(src)
				market_state = classify_market_state(as_of_date=as_of_date, daily_df=df, symbol=src.symbol)
				source = "csv"
			except Exception as exc:  # noqa: BLE001
				return ServiceResult(
					status="error",
					message=f"failed to build MarketState from benchmark CSV: {exc}",
					payload={"config_path": str(loaded.config_path), "base_dir": str(base_dir), "csv_path": str(csv_path)},
				)
		elif from_akshare:
			try:
				tool = self._create_akshare_tool()
				etf_df = tool.fetch_etf_daily_em(AkshareDailyRequest(symbol=bench_symbol))
				if cache_csv:
					csv_path = (
						Path(cfg.persona.market_state_benchmark_csv)
						if cfg.persona.market_state_benchmark_csv
						else Path("data/processed/persona") / f"{bench_symbol}_daily.csv"
					)
					if not csv_path.is_absolute():
						csv_path = base_dir / csv_path
					tool.write_daily_csv(df=etf_df, dest_path=csv_path)
				market_state = classify_market_state(as_of_date=as_of_date, daily_df=etf_df, symbol=bench_symbol)
				source = "akshare"
			except Exception as exc:  # noqa: BLE001
				return ServiceResult(
					status="error",
					message=f"failed to build MarketState from AkShare: {exc}",
					payload={"config_path": str(loaded.config_path), "base_dir": str(base_dir)},
				)
		else:
			cache_dir = base_dir / cfg.data.market_data_cache_dir
			cached_csv = MarketDataCache(cache_dir).path_for_symbol(bench_symbol)
			if cached_csv.exists():
				try:
					src = DailySeriesSource(symbol=bench_symbol, csv_path=cached_csv)
					df = load_daily_close_series(src)
					market_state = classify_market_state(as_of_date=as_of_date, daily_df=df, symbol=src.symbol)
					source = "cache"
				except Exception as exc:  # noqa: BLE001
					return ServiceResult(
						status="error",
						message=f"failed to build MarketState from cache: {exc}",
						payload={"config_path": str(loaded.config_path), "base_dir": str(base_dir), "cache_path": str(cached_csv)},
					)
			else:
				return ServiceResult(
					status="error",
					message="persona.market_state_benchmark_csv is not set; pass from_akshare or sync cache first",
					payload={"config_path": str(loaded.config_path), "base_dir": str(base_dir), "cache_path": str(cached_csv)},
				)

		assert market_state is not None
		full_dest = Path(dest)
		if not full_dest.is_absolute():
			full_dest = base_dir / full_dest
		full_dest.parent.mkdir(parents=True, exist_ok=True)
		full_dest.write_text(market_state.model_dump_json(indent=2), encoding="utf-8")
		return ServiceResult(
			status="ok",
			message="market state written",
			payload={
				"config_path": str(loaded.config_path),
				"base_dir": str(base_dir),
				"market_state_path": str(full_dest),
				"source": source,
				"market_state": market_state.model_dump(mode="json"),
			},
		)
