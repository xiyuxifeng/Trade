from __future__ import annotations

import signal
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.common.config import load_app_config
from src.providers.kaipan_normalizer import KaipanNormalizer
from src.providers.kaipan_provider import KaipanAuth, KaipanProvider
from src.services.base import BaseService, ServiceResult


def _project_base_dir(config_path: Path) -> Path:
	"""根据配置文件路径推导项目根目录。"""
	if config_path.parent.name == "config":
		return config_path.parent.parent
	return config_path.parent


def _to_plain(value: Any) -> Any:
	"""把 dataclass / 容器值转成可序列化结构。"""
	if hasattr(value, "model_dump"):
		return _to_plain(value.model_dump())
	if is_dataclass(value):
		return {k: _to_plain(v) for k, v in asdict(value).items()}
	if isinstance(value, dict):
		return {k: _to_plain(v) for k, v in value.items()}
	if isinstance(value, (list, tuple)):
		return [_to_plain(item) for item in value]
	if isinstance(value, Enum):
		return value.value
	if isinstance(value, (date, datetime)):
		return value.isoformat()
	if isinstance(value, Path):
		return str(value)
	return value


class KaipanService(BaseService):
	"""Kaipan 调度与标准化的共享服务。"""

	service_name = "kaipan"
	_ALLOWED_SLOTS = ("09-25", "17-30")

	def __init__(
		self,
		*,
		provider_factory: Callable[..., KaipanProvider] | None = None,
		normalizer_factory: Callable[..., KaipanNormalizer] | None = None,
	) -> None:
		self._provider_factory = provider_factory
		self._normalizer_factory = normalizer_factory

	def _load_runtime(self, config_path: str | Path) -> dict[str, Any]:
		"""加载 kaipan 运行时配置并计算工作目录。"""
		loaded = load_app_config(config_path)
		base_dir = _project_base_dir(loaded.config_path)
		cfg = loaded.config
		data_root = base_dir / cfg.kaipan.data_dir
		raw_dir = data_root / "raw"
		snapshots_dir = data_root / "snapshots"
		schema_dir = base_dir / cfg.kaipan.schema_dir
		return {
			"config_path": loaded.config_path,
			"base_dir": base_dir,
			"config": cfg,
			"data_root": data_root,
			"raw_dir": raw_dir,
			"snapshots_dir": snapshots_dir,
			"schema_dir": schema_dir,
		}

	def _create_provider(self, runtime: dict[str, Any]) -> KaipanProvider:
		"""创建 KaipanProvider。"""
		factory = self._provider_factory or KaipanProvider
		return factory(
			auth=KaipanAuth(),
			raw_dir=runtime["raw_dir"],
			normalized_dir=runtime["snapshots_dir"],
			snapshots_dir=runtime["snapshots_dir"],
			kaipan_config=runtime["config"].kaipan,
		)

	def _create_normalizer(self, runtime: dict[str, Any]) -> KaipanNormalizer:
		"""创建 KaipanNormalizer。"""
		factory = self._normalizer_factory or KaipanNormalizer
		return factory(schema_dir=runtime["schema_dir"], snapshots_dir=runtime["snapshots_dir"])

	def _expand_slots(self, slot: str) -> list[str]:
		"""将 slot 参数展开为实际处理的时间槽列表。"""
		if slot == "all":
			return list(self._ALLOWED_SLOTS)
		if slot not in self._ALLOWED_SLOTS:
			raise ValueError(f"invalid slot: {slot}, expected one of {', '.join((*self._ALLOWED_SLOTS, 'all'))}")
		return [slot]

	def _fetchers_for_slot(self, provider: KaipanProvider, slot: str) -> list[tuple[str, Callable[..., dict[str, Any]]]]:
		"""返回指定时间槽对应的抓取器列表。"""
		base_fetchers = [
			("market_sentiment", provider.fetch_market_sentiment),
			("market_index", provider.fetch_market_index),
			("board_strength", provider.fetch_board_strength),
			("industry_ranking", provider.fetch_industry_ranking),
			("concept_fengkou", provider.fetch_concept_fengkou),
			("theme_detail", provider.fetch_theme_detail),
			("stock_sector_v2", provider.fetch_stock_sector_v2),
			("strong_fengkou", provider.fetch_strong_fengkou),
			("interval_stats_stock", provider.fetch_interval_stats_stock),
			("limit_up_reason", provider.fetch_limit_up_reason),
			("limit_up_info", provider.fetch_limit_up_info),
		]
		if slot == "09-25":
			return base_fetchers[:8] + [
				("morning_bidding_list", provider.fetch_morning_bidding_list),
				("pre_market_bid", provider.fetch_pre_market_bid),
				("pre_market_stats", provider.fetch_pre_market_stats),
				("limit_up_info", provider.fetch_limit_up_info),
			]
		if slot == "17-30":
			return base_fetchers + [
				("lhb_list", provider.fetch_lhb_list),
				("market_stock_zd_num", provider.fetch_market_stock_zd_num),
				("zhang_ting_expression", provider.fetch_zhang_ting_expression),
				("daily_limit_index", provider.fetch_daily_limit_index),
				("weight_performance", provider.fetch_weight_performance),
				("strong_fengkou_best", provider.fetch_get_feng_k_list),
				("sharp_withdrawal", provider.fetch_sharp_withdrawal),
				("sector_ranking", provider.fetch_sector_ranking),
			]
		return []

	def fetch(
		self,
		*,
		config_path: str | Path,
		trade_date: str | date | None = None,
		slot: str = "all",
	) -> ServiceResult:
		"""抓取指定交易日的数据并执行标准化。"""
		runtime = self._load_runtime(config_path)
		td = date.today() if trade_date is None else date.fromisoformat(trade_date) if isinstance(trade_date, str) else trade_date
		try:
			slots_to_fetch = self._expand_slots(slot)
		except ValueError as exc:
			return ServiceResult(status="error", message=str(exc), payload={"config_path": str(runtime["config_path"])})
		provider = self._create_provider(runtime)
		normalizer = self._create_normalizer(runtime)

		slot_results: dict[str, dict[str, Any]] = {}
		for current_slot in slots_to_fetch:
			fetchers = self._fetchers_for_slot(provider, current_slot)
			slot_results[current_slot] = {
				"fetchers": [name for name, _ in fetchers],
				"success": [],
				"failed": [],
			}
			for name, fetcher in fetchers:
				try:
					fetcher(trade_date=td, slot=current_slot)
					slot_results[current_slot]["success"].append(name)
				except Exception as exc:  # noqa: BLE001
					slot_results[current_slot]["failed"].append({"dataset": name, "error": str(exc)})

		normalize_results = normalizer.normalize_date(td.isoformat(), slots=tuple(slots_to_fetch))
		return ServiceResult(
			status="ok",
			message="kaipan fetch completed",
			payload={
				"config_path": str(runtime["config_path"]),
				"base_dir": str(runtime["base_dir"]),
				"trade_date": td.isoformat(),
				"slots": slots_to_fetch,
				"slot_results": slot_results,
				"normalize_results": _to_plain(normalize_results),
			},
		)

	def normalize(
		self,
		*,
		config_path: str | Path,
		trade_date: str | date | None = None,
		slot: str = "all",
	) -> ServiceResult:
		"""仅执行 normalize。"""
		runtime = self._load_runtime(config_path)
		td = date.today() if trade_date is None else date.fromisoformat(trade_date) if isinstance(trade_date, str) else trade_date
		try:
			slots = tuple(self._expand_slots(slot))
		except ValueError as exc:
			return ServiceResult(status="error", message=str(exc), payload={"config_path": str(runtime["config_path"])})
		normalizer = self._create_normalizer(runtime)
		results = normalizer.normalize_date(td.isoformat(), slots=slots)
		return ServiceResult(
			status="ok",
			message="kaipan normalize completed",
			payload={
				"config_path": str(runtime["config_path"]),
				"base_dir": str(runtime["base_dir"]),
				"trade_date": td.isoformat(),
				"slots": list(slots),
				"results": _to_plain(results),
			},
		)

	def status(self, *, config_path: str | Path) -> ServiceResult:
		"""查看最近一次抓取状态。"""
		runtime = self._load_runtime(config_path)
		raw_base = runtime["raw_dir"]
		if not raw_base.exists():
			return ServiceResult(
				status="partial",
				message="no data yet",
				payload={
					"config_path": str(runtime["config_path"]),
					"base_dir": str(runtime["base_dir"]),
					"raw_base": str(raw_base),
					"latest_slot": None,
				},
			)

		latest: str | None = None
		latest_key: tuple[date, str] | None = None
		for p in raw_base.rglob("*.json"):
			slot_dir = p.parent.name
			try:
				date_part, slot_part = slot_dir.split("_", 1)
				trade_day = date.fromisoformat(date_part)
			except ValueError:
				continue
			current_key = (trade_day, slot_part)
			if latest_key is None or current_key > latest_key:
				latest_key = current_key
				latest = slot_dir

		return ServiceResult(
			status="ok" if latest else "partial",
			message=f"latest slot {latest}" if latest else "no data yet",
			payload={
				"config_path": str(runtime["config_path"]),
				"base_dir": str(runtime["base_dir"]),
				"raw_base": str(raw_base),
				"latest_slot": latest,
			},
		)

	def run(
		self,
		*,
		config_path: str | Path,
		start_scheduler: bool = False,
		block: bool = False,
	) -> ServiceResult:
		"""构建 Kaipan 调度计划或启动调度器。"""
		runtime = self._load_runtime(config_path)
		cfg = runtime["config"].kaipan
		pre_market = cfg.fetch_schedule.get("pre_market", "9:25")
		post_close = cfg.fetch_schedule.get("post_close", "17:30")

		if not start_scheduler:
			return ServiceResult(
				status="ok",
				message="kaipan scheduler plan prepared",
				payload={
					"config_path": str(runtime["config_path"]),
					"base_dir": str(runtime["base_dir"]),
					"pre_market": pre_market,
					"post_close": post_close,
					"data_root": str(runtime["data_root"]),
				},
			)

		def _run_fetch(slot: str) -> None:
			td = date.today()
			self.fetch(config_path=config_path, trade_date=td, slot=slot)

		scheduler = BackgroundScheduler()
		pre_hour, pre_min = map(int, pre_market.split(":"))
		post_hour, post_min = map(int, post_close.split(":"))
		scheduler.add_job(_run_fetch, CronTrigger(hour=pre_hour, minute=pre_min, second=0), args=["09-25"], id="pre_market", replace_existing=True)
		scheduler.add_job(_run_fetch, CronTrigger(hour=post_hour, minute=post_min, second=0), args=["17-30"], id="post_close", replace_existing=True)
		scheduler.start()

		if block:
			signal.signal(signal.SIGINT, lambda *_: scheduler.shutdown())
			signal.signal(signal.SIGTERM, lambda *_: scheduler.shutdown())
			scheduler._thread.join()

		return ServiceResult(
			status="ok",
			message="kaipan scheduler started",
			payload={
				"config_path": str(runtime["config_path"]),
				"base_dir": str(runtime["base_dir"]),
				"pre_market": pre_market,
				"post_close": post_close,
				"started": True,
			},
		)
