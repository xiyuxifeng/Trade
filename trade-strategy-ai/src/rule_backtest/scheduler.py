"""NTL-S11-010: 规则回测调度器

职责：
- 每周日 00:00 自动执行全量规则回测
- 与 pipeline 调度器解耦，独立运行
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.common.logger import get_logger

logger = get_logger("rule_backtest.scheduler")


@dataclass(slots=True)
class RuleBacktestScheduler:
    """规则回测调度器封装。

    提供 start/stop 接口用于管理调度器生命周期。
    """
    scheduler: BackgroundScheduler

    def start(self) -> None:
        """启动调度器"""
        self.scheduler.start()
        logger.info("规则回测调度器已启动")

    def stop(self) -> None:
        """停止调度器"""
        self.scheduler.shutdown(wait=False)
        logger.info("规则回测调度器已停止")


def build_rule_backtest_scheduler(
    *,
    start_date: date = date(2023, 1, 1),
    end_date: date = date(2026, 4, 30),
) -> RuleBacktestScheduler:
    """构建规则回测调度器

    每周日凌晨 00:00 执行全量规则回测。

    Args:
        start_date: 回测开始日期，默认 2023-01-01
        end_date: 回测结束日期，默认 2026-04-30

    Returns:
        RuleBacktestScheduler 实例
    """
    sched = BackgroundScheduler()

    def _job() -> None:
        """规则回测定时任务"""
        logger.info("规则回测任务触发，开始执行全量规则回测")

        async def _run() -> None:
            from src.backtest.engine import BacktestEngine
            from src.db.session import session_scope

            async with session_scope() as session:
                engine = BacktestEngine()
                result = await engine.run_rules_backtest(
                    session=session,
                    start_date=start_date,
                    end_date=end_date,
                )
                logger.info(
                    "规则回测完成: total_trades=%d, win_rate=%.2f, avg_return=%.2f",
                    result.summary.total_trades if result.summary else 0,
                    result.summary.win_rate if result.summary and result.summary.win_rate else 0,
                    result.summary.avg_return_pct if result.summary and result.summary.avg_return_pct else 0,
                )

        asyncio.run(_run())

    # 每周日凌晨 00:00 执行
    sched.add_job(
        _job,
        CronTrigger(day_of_week="sun", hour=0, minute=0),
        id="rule_backtest_weekly",
        replace_existing=True,
        misfire_grace_time=3600,  # 允许最多 1 小时延迟
    )

    logger.info(
        "规则回测调度器创建完成: 触发时间=每周日 00:00, 回测区间=%s 至 %s",
        start_date,
        end_date,
    )

    return RuleBacktestScheduler(scheduler=sched)