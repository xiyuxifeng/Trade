from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.common.config import AppConfig
from src.common.logger import get_logger
from src.pipeline.dag import run_pipeline
from src.rule_backtest.scheduler import build_rule_backtest_scheduler, RuleBacktestScheduler


logger = get_logger("pipeline.scheduler")


@dataclass(slots=True)
class PipelineScheduler:
    scheduler: BackgroundScheduler
    rule_backtest_scheduler: RuleBacktestScheduler | None = None

    def start(self) -> None:
        self.scheduler.start()
        if self.rule_backtest_scheduler:
            self.rule_backtest_scheduler.start()

    def stop(self) -> None:
        self.scheduler.shutdown(wait=False)
        if self.rule_backtest_scheduler:
            self.rule_backtest_scheduler.stop()


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

	# 默认回测区间
	from datetime import date
	start_date = date(2023, 1, 1)
	end_date = date(2026, 4, 30)

	# 构建规则回测调度器
	rule_backtest_scheduler = build_rule_backtest_scheduler(
		start_date=start_date,
		end_date=end_date,
	)

	if not config.schedule.enable:
		return PipelineScheduler(scheduler=sched, rule_backtest_scheduler=rule_backtest_scheduler)

	hhmm = _parse_hhmm(config.schedule.pre_market_time)
	if hhmm is None:
		# 默认：每天 08:00 跑一次数据 pipeline（可按需调整）
		hhmm = (8, 0)

	hour, minute = hhmm

	def _job() -> None:
		logger.info("pipeline job triggered", when=datetime.now(UTC).isoformat())
		asyncio.run(run_pipeline(config=config, base_dir=base_dir, skip_crawl=False, force=False))

	sched.add_job(_job, CronTrigger(hour=hour, minute=minute), id="pipeline_run", replace_existing=True)
	return PipelineScheduler(scheduler=sched, rule_backtest_scheduler=rule_backtest_scheduler)
