from __future__ import annotations

import signal
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from threading import Lock
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
	_NORMALIZE_DATASETS = KaipanNormalizer.DEFAULT_DATASETS
	_scheduler_lock = Lock()
	_scheduler: BackgroundScheduler | None = None
	_scheduler_pre_market: str | None = None
	_scheduler_post_close: str | None = None
	_scheduler_config_path: Path | None = None

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

	def _resolve_trade_dates(
		self,
		*,
		trade_date: str | date | None = None,
		start_date: str | date | None = None,
		end_date: str | date | None = None,
	) -> list[date]:
		"""把单日或区间参数统一展开为交易日列表。"""
		from src.backtest.engine import iter_trade_dates

		def _parse(value: str | date | None) -> date | None:
			if value is None:
				return None
			if isinstance(value, date):
				return value
			return date.fromisoformat(value)

		start = _parse(start_date)
		end = _parse(end_date)
		if start is None and end is None:
			effective = _parse(trade_date) or date.today()
			start = effective
			end = effective
		elif start is None:
			start = end or _parse(trade_date) or date.today()
		elif end is None:
			end = start

		if start > end:
			raise ValueError("start_date must be before or equal to end_date")

		trade_dates = iter_trade_dates(start, end)
		if not trade_dates:
			raise ValueError("no trade dates in range")
		return trade_dates

	def _progress_payload(
		self,
		*,
		job_type: str,
		stage: str,
		current: int,
		total: int,
		current_trade_date: str,
		current_slot: str | None = None,
		current_fetcher: str | None = None,
		current_dataset: str | None = None,
		status: str | None = None,
		error: str | None = None,
	) -> dict[str, Any]:
		"""构造统一的 Job progress payload。"""
		percent = round((current / total) * 100, 2) if total else 0.0
		payload: dict[str, Any] = {
			"job_type": job_type,
			"stage": stage,
			"current": current,
			"total": total,
			"percent": percent,
			"remaining": max(total - current, 0),
			"current_trade_date": current_trade_date,
			"current_slot": current_slot,
			"current_fetcher": current_fetcher,
			"current_dataset": current_dataset,
			"updated_at": datetime.now().isoformat(),
		}
		if current_fetcher is not None:
			payload["current_step"] = f"{stage}:{current_fetcher}"
		elif current_dataset is not None:
			payload["current_step"] = f"{stage}:{current_dataset}"
		else:
			payload["current_step"] = stage
		if status is not None:
			payload["status"] = status
		if error is not None:
			payload["error"] = error
		return payload

	def _emit_progress(self, progress_callback: Callable[[dict[str, Any]], None] | None, payload: dict[str, Any]) -> None:
		"""把进度事件发送给上层回调。"""
		if progress_callback is not None:
			progress_callback(payload)

	@classmethod
	def _scheduler_snapshot(cls) -> dict[str, Any]:
		"""读取当前 scheduler 的内存状态。"""
		with cls._scheduler_lock:
			scheduler = cls._scheduler
			started = bool(scheduler is not None and getattr(scheduler, "running", False))
			if not started and scheduler is not None:
				cls._scheduler = None
				cls._scheduler_pre_market = None
				cls._scheduler_post_close = None
				cls._scheduler_config_path = None
			return {
				"started": started,
				"pre_market": cls._scheduler_pre_market,
				"post_close": cls._scheduler_post_close,
				"config_path": str(cls._scheduler_config_path) if cls._scheduler_config_path is not None else None,
			}

	@classmethod
	def _clear_scheduler(cls) -> None:
		"""清空 scheduler 内存状态。"""
		with cls._scheduler_lock:
			scheduler = cls._scheduler
			if scheduler is not None:
				try:
					if getattr(scheduler, "running", False):
						scheduler.shutdown(wait=False)
				finally:
					pass
			cls._scheduler = None
			cls._scheduler_pre_market = None
			cls._scheduler_post_close = None
			cls._scheduler_config_path = None

	def fetch(
		self,
		*,
		config_path: str | Path,
		trade_date: str | date | None = None,
		start_date: str | date | None = None,
		end_date: str | date | None = None,
		slot: str = "all",
		runtime_state: dict[str, Any] | None = None,
		progress_callback: Callable[[dict[str, Any]], None] | None = None,
	) -> ServiceResult:
		"""抓取指定交易日或区间的数据并执行标准化。"""
		runtime = self._load_runtime(config_path)
		try:
			slots_to_fetch = self._expand_slots(slot)
			trade_dates = self._resolve_trade_dates(trade_date=trade_date, start_date=start_date, end_date=end_date)
		except ValueError as exc:
			return ServiceResult(status="error", message=str(exc), payload={"config_path": str(runtime["config_path"])})
		provider = self._create_provider(runtime)
		normalizer = self._create_normalizer(runtime)
		total_steps = sum(
			len(self._fetchers_for_slot(provider, current_slot)) + len(self._NORMALIZE_DATASETS)
			for _trade_day in trade_dates
			for current_slot in slots_to_fetch
		)
		current_step = 0
		runtime_state_payload = runtime_state if isinstance(runtime_state, dict) else {}
		checkpoint = runtime_state_payload.get("checkpoint") if isinstance(runtime_state_payload.get("checkpoint"), dict) else {}
		start_step = int(checkpoint.get("step_index") or 0)
		current_step = int(checkpoint.get("step_index") or 0)
		date_results: dict[str, dict[str, Any]] = dict(checkpoint.get("date_results") or {})

		for trade_day in trade_dates:
			trade_day_key = trade_day.isoformat()
			day_slot_results: dict[str, Any] = {}
			day_normalize_results: dict[str, Any] = {}
			date_results[trade_day_key] = {
				"slot_results": day_slot_results,
				"normalize_results": day_normalize_results,
			}

			for current_slot in slots_to_fetch:
				fetchers = self._fetchers_for_slot(provider, current_slot)
				day_slot_results[current_slot] = {
					"fetchers": [name for name, _ in fetchers],
					"success": [],
					"failed": [],
				}
				for name, fetcher in fetchers:
					step_index = current_step + 1
					current_step = step_index
					if step_index <= start_step:
						continue
					status = "success"
					error_message: str | None = None
					try:
						fetcher(trade_date=trade_day, slot=current_slot)
						day_slot_results[current_slot]["success"].append(name)
					except Exception as exc:  # noqa: BLE001
						status = "error"
						error_message = str(exc)
						day_slot_results[current_slot]["failed"].append({"dataset": name, "error": error_message})
					if progress_callback is not None:
						progress_callback(
							{
								"job_type": "kaipan-fetch",
								"stage": "fetch",
								"current": step_index,
								"total": total_steps,
								"percent": round((step_index / total_steps) * 100, 2) if total_steps else 0.0,
								"remaining": max(total_steps - step_index, 0),
								"current_step": f"fetch:{name}",
								"current_trade_date": trade_day_key,
								"current_slot": current_slot,
								"current_fetcher": name,
								"status": status,
								"error": error_message,
								"runtime_state": {
									"schema_version": 1,
									"checkpoint": {
										"step_index": step_index,
										"date_results": date_results,
									},
								},
							}
						)
				def _on_normalize_step(step_payload: dict[str, Any]) -> None:
					nonlocal current_step
					current_step += 1
					dataset_name = step_payload.get("dataset")
					if progress_callback is not None:
						progress_callback(
							{
								"job_type": "kaipan-fetch",
								"stage": "normalize",
								"current": current_step,
								"total": total_steps,
								"percent": round((current_step / total_steps) * 100, 2) if total_steps else 0.0,
								"remaining": max(total_steps - current_step, 0),
								"current_step": f"normalize:{dataset_name}" if dataset_name else "normalize",
								"current_trade_date": str(step_payload.get("trade_date") or trade_day_key),
								"current_slot": str(step_payload.get("slot") or current_slot),
								"current_dataset": str(dataset_name) if dataset_name else None,
								"status": str(step_payload.get("status") or "unknown"),
								"error": str(step_payload["error"]) if step_payload.get("error") else None,
								"runtime_state": {
									"schema_version": 1,
									"checkpoint": {
										"step_index": current_step,
										"date_results": date_results,
									},
								},
							}
						)

				normalize_results = normalizer.normalize_date(trade_day_key, slots=(current_slot,), progress_callback=_on_normalize_step)
				day_normalize_results[current_slot] = normalize_results.get(current_slot, {})

		return ServiceResult(
			status="ok",
			message="kaipan fetch completed",
			payload={
				"config_path": str(runtime["config_path"]),
				"base_dir": str(runtime["base_dir"]),
				"trade_date": trade_dates[0].isoformat() if len(trade_dates) == 1 else None,
				"start_date": trade_dates[0].isoformat(),
				"end_date": trade_dates[-1].isoformat(),
				"trade_dates": [trade_day.isoformat() for trade_day in trade_dates],
				"slots": slots_to_fetch,
				"date_results": _to_plain(date_results),
				"slot_results": _to_plain(date_results[trade_dates[0].isoformat()]["slot_results"]) if len(trade_dates) == 1 else None,
				"normalize_results": _to_plain(date_results[trade_dates[0].isoformat()]["normalize_results"]) if len(trade_dates) == 1 else None,
			},
		)

	def normalize(
		self,
		*,
		config_path: str | Path,
		trade_date: str | date | None = None,
		start_date: str | date | None = None,
		end_date: str | date | None = None,
		slot: str = "all",
		runtime_state: dict[str, Any] | None = None,
		progress_callback: Callable[[dict[str, Any]], None] | None = None,
	) -> ServiceResult:
		"""仅执行 normalize，可覆盖单日或区间。"""
		runtime = self._load_runtime(config_path)
		try:
			slots = tuple(self._expand_slots(slot))
			trade_dates = self._resolve_trade_dates(trade_date=trade_date, start_date=start_date, end_date=end_date)
		except ValueError as exc:
			return ServiceResult(status="error", message=str(exc), payload={"config_path": str(runtime["config_path"])})
		normalizer = self._create_normalizer(runtime)
		total_steps = len(self._NORMALIZE_DATASETS) * len(slots) * len(trade_dates)
		current_step = 0
		runtime_state_payload = runtime_state if isinstance(runtime_state, dict) else {}
		checkpoint = runtime_state_payload.get("checkpoint") if isinstance(runtime_state_payload.get("checkpoint"), dict) else {}
		start_step = int(checkpoint.get("step_index") or 0)
		current_step = int(checkpoint.get("step_index") or 0)
		date_results: dict[str, dict[str, Any]] = dict(checkpoint.get("date_results") or {})

		def _on_normalize_step(step_payload: dict[str, Any]) -> None:
			nonlocal current_step
			current_step += 1
			self._emit_progress(
				progress_callback,
				self._progress_payload(
					job_type="kaipan-normalize",
					stage="normalize",
					current=current_step,
					total=total_steps,
					current_trade_date=str(step_payload.get("trade_date") or ""),
					current_slot=str(step_payload.get("slot") or ""),
					current_dataset=str(step_payload.get("dataset")) if step_payload.get("dataset") else None,
					status=str(step_payload.get("status") or "unknown"),
					error=str(step_payload["error"]) if step_payload.get("error") else None,
				),
			)
			if progress_callback is not None:
				progress_callback(
					{
						"job_type": "kaipan-normalize",
						"stage": "normalize",
						"current": current_step,
						"total": total_steps,
						"percent": round((current_step / total_steps) * 100, 2) if total_steps else 0.0,
						"remaining": max(total_steps - current_step, 0),
						"current_step": f"normalize:{step_payload.get('dataset')}" if step_payload.get("dataset") else "normalize",
						"current_trade_date": str(step_payload.get("trade_date") or ""),
						"current_slot": str(step_payload.get("slot") or ""),
						"current_dataset": str(step_payload.get("dataset")) if step_payload.get("dataset") else None,
						"status": str(step_payload.get("status") or "unknown"),
						"error": str(step_payload["error"]) if step_payload.get("error") else None,
						"runtime_state": {
							"schema_version": 1,
							"checkpoint": {
								"step_index": current_step,
								"date_results": date_results,
							},
						},
					}
				)

		for trade_day in trade_dates:
			trade_day_key = trade_day.isoformat()
			date_results[trade_day_key] = normalizer.normalize_date(trade_day_key, slots=slots, progress_callback=_on_normalize_step)
		return ServiceResult(
			status="ok",
			message="kaipan normalize completed",
			payload={
				"config_path": str(runtime["config_path"]),
				"base_dir": str(runtime["base_dir"]),
				"trade_date": trade_dates[0].isoformat() if len(trade_dates) == 1 else None,
				"start_date": trade_dates[0].isoformat(),
				"end_date": trade_dates[-1].isoformat(),
				"trade_dates": [trade_day.isoformat() for trade_day in trade_dates],
				"slots": list(slots),
				"date_results": _to_plain(date_results),
				"results": _to_plain(date_results[trade_dates[0].isoformat()]) if len(trade_dates) == 1 else None,
			},
		)

	def status(self, *, config_path: str | Path) -> ServiceResult:
		"""查看最近一次抓取状态。"""
		runtime = self._load_runtime(config_path)
		raw_base = runtime["raw_dir"]
		scheduler_state = self._scheduler_snapshot()
		if not raw_base.exists():
			return ServiceResult(
				status="partial",
				message="no data yet",
				payload={
					"config_path": str(runtime["config_path"]),
					"base_dir": str(runtime["base_dir"]),
					"raw_base": str(raw_base),
					"latest_slot": None,
					"scheduler_started": scheduler_state["started"],
					"scheduler_pre_market": scheduler_state["pre_market"],
					"scheduler_post_close": scheduler_state["post_close"],
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
				"scheduler_started": scheduler_state["started"],
				"scheduler_pre_market": scheduler_state["pre_market"],
				"scheduler_post_close": scheduler_state["post_close"],
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
		scheduler_state = self._scheduler_snapshot()

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
					"scheduler_started": scheduler_state["started"],
				},
			)

		if scheduler_state["started"]:
			return ServiceResult(
				status="partial",
				message="kaipan scheduler already running",
				payload={
					"config_path": str(runtime["config_path"]),
					"base_dir": str(runtime["base_dir"]),
					"pre_market": scheduler_state["pre_market"] or pre_market,
					"post_close": scheduler_state["post_close"] or post_close,
					"started": True,
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
		cls = type(self)
		with cls._scheduler_lock:
			cls._scheduler = scheduler
			cls._scheduler_pre_market = pre_market
			cls._scheduler_post_close = post_close
			cls._scheduler_config_path = runtime["config_path"]

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
				"scheduler_started": True,
			},
		)

	def stop(self, *, config_path: str | Path) -> ServiceResult:
		"""停止当前 Kaipan 调度器。"""
		runtime = self._load_runtime(config_path)
		scheduler_state = self._scheduler_snapshot()
		if not scheduler_state["started"]:
			return ServiceResult(
				status="partial",
				message="kaipan scheduler is not running",
				payload={
					"config_path": str(runtime["config_path"]),
					"base_dir": str(runtime["base_dir"]),
					"started": False,
					"pre_market": scheduler_state["pre_market"],
					"post_close": scheduler_state["post_close"],
				},
			)
		self._clear_scheduler()
		return ServiceResult(
			status="ok",
			message="kaipan scheduler stopped",
			payload={
				"config_path": str(runtime["config_path"]),
				"base_dir": str(runtime["base_dir"]),
				"started": False,
				"pre_market": scheduler_state["pre_market"],
				"post_close": scheduler_state["post_close"],
			},
		)
