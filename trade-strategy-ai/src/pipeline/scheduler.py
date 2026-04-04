from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.common.config import AppConfig
from src.common.logger import get_logger
from src.pipeline.dag import run_pipeline


logger = get_logger("pipeline.scheduler")


@dataclass(slots=True)
class PipelineScheduler:
	scheduler: BackgroundScheduler

	def start(self) -> None:
		self.scheduler.start()

	def stop(self) -> None:
		self.scheduler.shutdown(wait=False)


def _parse_hhmm(value: str | None) -> tuple[int, int] | None:
	if not value:
		return None
	try:
		hour_s, min_s = value.split(":", 1)
		return int(hour_s), int(min_s)
	except Exception:  # noqa: BLE001
		return None


def build_pipeline_scheduler(*, config: AppConfig, base_dir: Path) -> PipelineScheduler:
	sched = BackgroundScheduler()

	if not config.schedule.enable:
		return PipelineScheduler(scheduler=sched)

	hhmm = _parse_hhmm(config.schedule.pre_market_time)
	if hhmm is None:
		# 默认：每天 08:00 跑一次数据 pipeline（可按需调整）
		hhmm = (8, 0)

	hour, minute = hhmm

	def _job() -> None:
		logger.info("pipeline job triggered", when=datetime.utcnow().isoformat())
		asyncio.run(run_pipeline(config=config, base_dir=base_dir, skip_crawl=False, force=False))

	sched.add_job(_job, CronTrigger(hour=hour, minute=minute), id="pipeline_run", replace_existing=True)
	return PipelineScheduler(scheduler=sched)
