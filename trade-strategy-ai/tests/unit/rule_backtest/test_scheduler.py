"""NTL-S11-010: 规则回测调度器测试"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.rule_backtest.scheduler import (
    RuleBacktestScheduler,
    build_rule_backtest_scheduler,
)


class TestRuleBacktestScheduler:
    """RuleBacktestScheduler 单元测试"""

    def test_build_rule_backtest_scheduler_returns_scheduler(self):
        """测试 build_rule_backtest_scheduler 返回正确的调度器类型"""
        scheduler = build_rule_backtest_scheduler(
            start_date=date(2023, 1, 1),
            end_date=date(2026, 4, 30),
        )
        assert isinstance(scheduler, RuleBacktestScheduler)
        assert scheduler.scheduler is not None

    def test_build_rule_backtest_scheduler_default_dates(self):
        """测试默认回测日期区间"""
        scheduler = build_rule_backtest_scheduler()
        assert isinstance(scheduler, RuleBacktestScheduler)

    def test_scheduler_has_job(self):
        """测试调度器包含预定的定时任务"""
        scheduler = build_rule_backtest_scheduler()
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "rule_backtest_weekly"

    def test_scheduler_trigger_is_cron_sunday(self):
        """测试触发时间是每周日 00:00 的 CronTrigger"""
        scheduler = build_rule_backtest_scheduler()
        jobs = scheduler.scheduler.get_jobs()
        job = jobs[0]
        # 验证 job ID 正确
        assert job.id == "rule_backtest_weekly"
        # 验证 trigger 包含 day_of_week 字段
        trigger_fields = {f.name: f for f in job.trigger.fields}
        day_of_week_field = trigger_fields.get("day_of_week")
        assert day_of_week_field is not None
        # 验证 day_of_week 包含 "sun" 表达式
        assert any("sun" in str(expr) for expr in day_of_week_field.expressions)

    def test_start_stop_methods_exist(self):
        """测试调度器具有 start/stop 方法"""
        scheduler = build_rule_backtest_scheduler()
        assert hasattr(scheduler, "start")
        assert hasattr(scheduler, "stop")
        assert callable(scheduler.start)
        assert callable(scheduler.stop)

    def test_start_does_not_raise(self):
        """测试 start 方法可以正常调用"""
        scheduler = build_rule_backtest_scheduler()
        scheduler.start()
        scheduler.stop()

    def test_stop_on_unstarted_scheduler_raises(self):
        """测试停止未启动的调度器会抛出异常"""
        scheduler = build_rule_backtest_scheduler()
        # 未启动的调度器调用 stop 会抛出 SchedulerNotRunningError
        with pytest.raises(Exception):
            scheduler.stop()

    @patch("src.rule_backtest.scheduler.asyncio.run")
    @patch("src.backtest.engine.BacktestEngine")
    @patch("src.db.session.session_scope")
    async def test_job_calls_asyncio_run(
        self,
        mock_session_scope,
        mock_engine_class,
        mock_asyncio_run,
    ):
        """测试定时任务使用 asyncio.run 执行"""
        # 模拟 session_scope context manager
        mock_session = AsyncMock()
        mock_session_scope.return_value.__aenter__.return_value = mock_session
        mock_session_scope.return_value.__aexit__.return_value = None

        # 模拟引擎
        mock_engine = MagicMock()
        mock_engine.run_rules_backtest = AsyncMock(return_value=MagicMock(
            summary=MagicMock(
                total_trades=100,
                win_rate=0.6,
                avg_return_pct=0.02,
            )
        ))
        mock_engine_class.return_value = mock_engine

        # 获取定时任务
        scheduler = build_rule_backtest_scheduler()
        jobs = scheduler.scheduler.get_jobs()
        job = jobs[0]

        # 执行任务
        job.func()

        # 验证 asyncio.run 被调用
        mock_asyncio_run.assert_called_once()


class TestSchedulerJobTrigger:
    """调度任务触发时间测试"""

    def test_job_id_is_unique(self):
        """测试任务 ID 唯一性"""
        scheduler1 = build_rule_backtest_scheduler()
        scheduler2 = build_rule_backtest_scheduler()

        job1 = scheduler1.scheduler.get_jobs()[0]
        job2 = scheduler2.scheduler.get_jobs()[0]

        # 不同调度器实例的任务 ID 应该相同（replace_existing=True）
        assert job1.id == job2.id == "rule_backtest_weekly"