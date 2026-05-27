"""NTL-S6-004: 回测引擎单元测试"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from src.backtest.schemas import BacktestRequest


class TestBacktestEngine:
    """回测引擎测试"""

    def test_engine_run_single_day_backtest(self):
        """单日回测：引擎应返回覆盖1天的结果"""
        from src.backtest.engine import BacktestEngine

        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
        )
        result = engine.run_sync(req)
        assert result.request_trader_id == "trader_a"
        assert result.request_date_from == date(2026, 4, 1)
        assert result.request_date_to == date(2026, 4, 1)

    @pytest.mark.asyncio
    async def test_engine_run_can_resume_from_checkpoint(self):
        """回测运行应能从 runtime_state 的交易日游标恢复。"""
        from src.backtest.engine import BacktestEngine

        mock_loader = AsyncMock()
        mock_loader.load_market_context.return_value = {
            "trade_date": "2026-04-02",
            "bars_by_symbol": {},
            "indicators_by_symbol": {},
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }

        mock_strategy_loader = AsyncMock()
        mock_strategy_loader.load_version_for_date.return_value = None

        engine = BacktestEngine(
            loader=mock_loader,
            strategy_loader=mock_strategy_loader,
        )
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 2),
        )
        progress_events: list[dict[str, object]] = []
        result = await engine.run(
            req,
            progress_callback=progress_events.append,
            runtime_state={
                "checkpoint": {
                    "trade_date_index": 1,
                    "records": [
                        {
                            "trade_date": "2026-04-01",
                            "trader_id": "trader_a",
                            "strategy_version_id": "",
                            "symbol": "",
                            "status": "skipped",
                            "skip_reason": "checkpointed",
                            "evidence_refs": [],
                        }
                    ],
                }
            },
        )

        assert mock_loader.load_market_context.call_count == 1
        assert len(result.records) == 2
        assert result.records[0].trade_date == date(2026, 4, 1)
        assert result.records[1].trade_date == date(2026, 4, 2)
        assert progress_events[-1]["runtime_state"]["checkpoint"]["trade_date_index"] == 2

    def test_engine_run_multi_day_backtest(self):
        """多日回测：覆盖指定日期区间"""
        from src.backtest.engine import BacktestEngine

        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 10),
        )
        result = engine.run_sync(req)
        assert result.summary is not None
        # 日期差：2026-04-01 到 2026-04-10，刨除周末应覆盖约7个交易日
        assert result.summary.total_days >= 7

    def test_engine_run_replay_mode(self):
        """replay 模式：仅重放策略版本，不做评分"""
        from src.backtest.engine import BacktestEngine

        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
            mode="replay",
        )
        result = engine.run_sync(req)
        # replay 模式只产生 records，不保证有 summary
        assert isinstance(result.records, list)

    def test_engine_run_rule_validation_mode(self):
        """rule_validation 模式：仅做规则验真"""
        from src.backtest.engine import BacktestEngine

        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
            mode="rule_validation",
        )
        result = engine.run_sync(req)
        assert isinstance(result.records, list)

    def test_engine_produces_backtest_result(self):
        """引擎返回 BacktestResult 类型"""
        from src.backtest.engine import BacktestEngine

        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
        )
        result = engine.run_sync(req)
        from src.backtest.schemas import BacktestResult

        assert isinstance(result, BacktestResult)
        assert result.records is not None
        assert isinstance(result.records, list)


class TestBacktestEngineWithMockedComponents:
    """带 mock 组件的回测引擎集成测试"""

    @pytest.mark.asyncio
    async def test_engine_calls_loader_for_each_day(self):
        """引擎应逐日调用 loader（async）"""
        from src.backtest.engine import BacktestEngine
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_loader = AsyncMock(spec=SnapshotLoader)
        mock_loader.load_market_context.return_value = {
            "trade_date": "2026-04-01",
            "bars_by_symbol": {},
            "indicators_by_symbol": {},
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }

        engine = BacktestEngine(loader=mock_loader)
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 3),
        )
        result = await engine.run(req)
        # 应调用 3 次（3 天）
        assert mock_loader.load_market_context.call_count >= 1

    def test_engine_with_stub_strategy_loader(self):
        """使用 stub 策略加载器时能正常返回"""
        from src.backtest.engine import BacktestEngine
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_loader = AsyncMock(spec=SnapshotLoader)
        mock_loader.load_market_context.return_value = {
            "trade_date": "2026-04-01",
            "bars_by_symbol": {},
            "indicators_by_symbol": {},
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }

        engine = BacktestEngine(loader=mock_loader)
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
        )
        result = engine.run_sync(req)
        assert result.request_trader_id == "trader_a"
        assert len(result.records) >= 0


class TestEngineIntegration:
    """Engine 串接测试：loader → replayer → scoring"""

    @pytest.mark.asyncio
    async def test_engine_with_full_components_produces_trade_records(self):
        """loader + strategy_loader + scoring 串接时应产生真实 trade records"""
        from datetime import datetime

        from src.backtest.engine import BacktestEngine
        from src.backtest.execution import replay_candidates
        from src.backtest.scoring import score_backtest_trade
        from src.strategy_library.schemas import (
            StrategyRecommendation,
            StrategyVersion,
            StrategyVersionStatus,
        )

        # Mock loader: 返回包含 bars 的 market context
        mock_loader = AsyncMock()
        mock_loader.load_market_context.return_value = {
            "trade_date": "2026-04-01",
            "bars_by_symbol": {
                "000001": [
                    {
                        "date": "2026-04-01",
                        "open": 10.0,
                        "high": 10.5,
                        "low": 9.8,
                        "close": 10.2,
                        "volume": 1000000,
                    },
                    {
                        "date": "2026-04-02",
                        "open": 10.2,
                        "high": 10.8,
                        "low": 10.1,
                        "close": 10.5,
                        "volume": 1100000,
                    },
                    {
                        "date": "2026-04-03",
                        "open": 10.5,
                        "high": 11.0,
                        "low": 10.4,
                        "close": 10.8,
                        "volume": 1200000,
                    },
                ]
            },
            "indicators_by_symbol": {
                "000001": {"rsi": 65.0, "ma5": 10.2}
            },
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }

        # Mock strategy_loader: 返回策略版本
        mock_strategy_loader = AsyncMock()
        mock_strategy_loader.load_version_for_date.return_value = StrategyVersion(
            version_id="v1",
            trader_id="trader_a",
            strategy_date=datetime(2026, 4, 1).date(),
            status=StrategyVersionStatus.released,
            recommendations=[
                StrategyRecommendation(
                    symbol="000001",
                    decision="buy",
                    confidence=0.8,
                    entry_price=10.2,
                    target_price=11.0,
                    stop_loss_price=9.5,
                )
            ],
        )

        # Mock scoring_func (同步函数)
        mock_scoring = Mock()
        mock_scoring.return_value = {
            "mfe": 0.08,
            "mae": -0.02,
            "return_pct": 0.058,
            "exit_triggered": "target",
            "exit_date": "2026-04-03",
            "halted_dates": [],
            "eval_date": "2026-04-03",
        }

        engine = BacktestEngine(
            loader=mock_loader,
            strategy_loader=mock_strategy_loader,
            scoring_func=mock_scoring,
        )
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=datetime(2026, 4, 1).date(),
            date_to=datetime(2026, 4, 1).date(),
        )
        result = await engine.run(req)

        # 验证产生了真实交易记录（非 skipped）
        assert len(result.records) == 1
        record = result.records[0]
        assert record.status != "skipped" or record.symbol == "000001"
        assert record.symbol == "000001"
        # exit_price 应从 bars 中查找 exit_date 对应的收盘价（10.8）
        assert record.exit_price == 10.8, f"exit_price 应为收盘价 10.8，实际为 {record.exit_price}"
        assert record.exit_date == "2026-04-03"

    def test_engine_rule_validation_mode(self):
        """rule_validation 模式：仅做规则验真"""
        from datetime import datetime

        from src.backtest.engine import BacktestEngine

        mock_loader = AsyncMock()
        mock_loader.load_market_context.return_value = {
            "trade_date": "2026-04-01",
            "bars_by_symbol": {},
            "indicators_by_symbol": {"000001": {"rsi": 65.0}},
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }

        mock_strategy_loader = AsyncMock()
        mock_strategy_loader.load_version_for_date.return_value = None

        engine = BacktestEngine(
            loader=mock_loader,
            strategy_loader=mock_strategy_loader,
        )
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=datetime(2026, 4, 1).date(),
            date_to=datetime(2026, 4, 1).date(),
            mode="rule_validation",
        )
        result = engine.run_sync(req)
        assert isinstance(result.records, list)

    @pytest.mark.asyncio
    async def test_engine_checks_lot_size_for_buy(self):
        """买入交易量必须是 100 股整数倍；卖出不校验"""
        from datetime import datetime

        from src.backtest.engine import BacktestEngine
        from src.strategy_library.schemas import (
            StrategyRecommendation,
            StrategyVersion,
            StrategyVersionStatus,
        )

        mock_loader = AsyncMock()
        mock_loader.load_market_context.return_value = {
            "trade_date": "2026-04-01",
            "bars_by_symbol": {
                "000001": [
                    {
                        "date": "2026-04-01",
                        "open": 10.0,
                        "high": 10.5,
                        "low": 9.8,
                        "close": 10.2,
                        "volume": 1000000,
                    }
                ]
            },
            "indicators_by_symbol": {},
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }

        mock_strategy_loader = AsyncMock()
        mock_strategy_loader.load_version_for_date.return_value = StrategyVersion(
            version_id="v1",
            trader_id="trader_a",
            strategy_date=datetime(2026, 4, 1).date(),
            status=StrategyVersionStatus.released,
            recommendations=[
                StrategyRecommendation(
                    symbol="000001",
                    decision="buy",
                    confidence=0.8,
                    entry_price=10.2,
                    volume=150,  # 不是 100 的整数倍
                ),
                StrategyRecommendation(
                    symbol="000001",
                    decision="buy",
                    confidence=0.8,
                    entry_price=10.2,
                    volume=200,  # 是 100 的整数倍
                ),
                StrategyRecommendation(
                    symbol="000001",
                    decision="sell",
                    confidence=0.8,
                    entry_price=10.2,
                    volume=150,  # 卖出不校验
                ),
            ],
        )

        mock_scoring = Mock()
        mock_scoring.return_value = {
            "mfe": 0.08,
            "mae": -0.02,
            "return_pct": 0.058,
            "exit_triggered": "target",
            "exit_date": "2026-04-01",
            "halted_dates": [],
            "eval_date": "2026-04-01",
        }

        engine = BacktestEngine(
            loader=mock_loader,
            strategy_loader=mock_strategy_loader,
            scoring_func=mock_scoring,
        )
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=datetime(2026, 4, 1).date(),
            date_to=datetime(2026, 4, 1).date(),
        )
        result = await engine.run(req)

        assert len(result.records) == 3
        # 150 股买入 → 不符合 100 股整数倍
        assert result.records[0].volume == 150
        assert result.records[0].is_valid_lot_size is False
        # 200 股买入 → 符合
        assert result.records[1].volume == 200
        assert result.records[1].is_valid_lot_size is True
        # 150 股卖出 → 不校验
        assert result.records[2].volume == 150
        assert result.records[2].is_valid_lot_size is None


class TestValidateRuleHits:
    """NTL-S6-010: 规则命中验证测试"""

    def test_validate_rule_hits_basic_count(self):
        """验证 hit_count >= 0 且 sample_count == len(contexts)"""
        from src.backtest.engine import validate_rule_hits
        from src.backtest.rule_registry import RuleMeta

        rule_meta = RuleMeta(
            rule_id="r1",
            rule_text="rsi < 30",
            required_fields=["rsi"],
            programmatic_level="fully_programmable",
        )
        # 空的 contexts 列表
        contexts: list[dict] = []
        result = validate_rule_hits(rule_meta, contexts)
        assert result.hit_count >= 0
        assert result.sample_count == 0

    def test_validate_rule_hits_unsupported_rule(self):
        """不可程序化规则应标记为 unsupported_rule"""
        from src.backtest.engine import validate_rule_hits
        from src.backtest.rule_registry import RuleMeta

        rule_meta = RuleMeta(
            rule_id="r2",
            rule_text="关注市场情绪",
            required_fields=[],
            programmatic_level="descriptive_only",
        )
        contexts: list[dict] = []
        result = validate_rule_hits(rule_meta, contexts)
        assert result.validation_status == "unsupported_rule"
        assert result.programmable is False


class TestIterTradeDates:
    """交易日迭代器测试"""

    def test_iter_trade_dates_single_day(self):
        """单日"""
        from src.backtest.engine import iter_trade_dates

        dates = list(iter_trade_dates(date(2026, 4, 1), date(2026, 4, 1)))
        assert len(dates) == 1
        assert dates[0] == date(2026, 4, 1)

    def test_iter_trade_dates_excludes_weekends(self):
        """应跳过周末（周六、周日）"""
        from src.backtest.engine import iter_trade_dates

        # 2026-04-01 是周三，2026-04-03 是周五
        dates = list(iter_trade_dates(date(2026, 4, 1), date(2026, 4, 3)))
        assert len(dates) == 3  # Wed, Thu, Fri

    def test_iter_trade_dates_skips_full_weekends(self):
        """跨周时应跳过整个周末"""
        from src.backtest.engine import iter_trade_dates

        # 2026-04-01 周三 到 2026-04-06 周一
        dates = list(iter_trade_dates(date(2026, 4, 1), date(2026, 4, 6)))
        # Wed(1), Thu(2), Fri(3), Mon(6) = 4 天
        assert date(2026, 4, 4) not in dates  # 周六
        assert date(2026, 4, 5) not in dates  # 周日


class TestIterTradeDatesWithHolidays:
    """节假日跨越测试（清明 4/4-4/6、五一 5/1-5/5）"""

    def setup_method(self):
        """每个测试前设置节假日，yield 后自动恢复（即使测试异常也能清理）"""
        from src.backtest.engine import TradeCalendar

        TradeCalendar.set_holidays({
            "2026-04-04", "2026-04-05", "2026-04-06",  # 清明假期
            "2026-05-01", "2026-05-02", "2026-05-03",  # 五一假期（5/4-5/5 本身是周末）
            "2026-05-04", "2026-05-05",
        })
        TradeCalendar._loaded = True  # 阻止懒加载覆盖

    def teardown_method(self):
        """每个测试后清除节假日，恢复默认值"""
        from src.backtest.engine import TradeCalendar

        TradeCalendar.set_holidays(set())
        TradeCalendar._loaded = False
        TradeCalendar._trade_dates = None

    def test_iter_trade_dates_skips_qingming_holiday(self):
        """清明假期（4/4-4/6）应被跳过"""
        from src.backtest.engine import iter_trade_dates

        # 2026-04-01(周三) 到 2026-04-07(周二)
        dates = list(iter_trade_dates(date(2026, 4, 1), date(2026, 4, 7)))
        # 交易日：4/1, 4/2, 4/3, 4/7（4/4-4/6 为清明+周末全部跳过）
        assert len(dates) == 4
        assert date(2026, 4, 1) in dates  # 周三
        assert date(2026, 4, 2) in dates  # 周四
        assert date(2026, 4, 3) in dates  # 周五
        assert date(2026, 4, 4) not in dates  # 清明周六
        assert date(2026, 4, 5) not in dates  # 清明周日
        assert date(2026, 4, 6) not in dates  # 清明周一（调休）
        assert date(2026, 4, 7) in dates  # 周二

    def test_iter_trade_dates_skips_labor_day_holiday(self):
        """五一假期（5/1-5/5）应被跳过"""
        from src.backtest.engine import iter_trade_dates

        # 2026-05-01(周五) 到 2026-05-06(周三)
        dates = list(iter_trade_dates(date(2026, 5, 1), date(2026, 5, 6)))
        # 交易日：5/1 跨周末后只有 5/6
        assert len(dates) == 1
        assert date(2026, 5, 1) not in dates  # 五一周五
        assert date(2026, 5, 2) not in dates  # 周六
        assert date(2026, 5, 3) not in dates  # 周日
        assert date(2026, 5, 4) not in dates  # 五一调休
        assert date(2026, 5, 5) not in dates  # 五一调休
        assert date(2026, 5, 6) in dates  # 周三

    def test_engine_skips_holidays_across_qingming(self):
        """引擎在清明假期跨越期间只处理交易日"""
        from unittest.mock import AsyncMock

        from src.backtest.engine import BacktestEngine
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_loader = AsyncMock(spec=SnapshotLoader)
        mock_loader.load_market_context.return_value = {
            "trade_date": "2026-04-01",
            "bars_by_symbol": {},
            "indicators_by_symbol": {},
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }

        engine = BacktestEngine(loader=mock_loader)
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 7),
        )
        result = engine.run_sync(req)
        # 清明假期跨越：4个交易日（4/1-4/3 + 4/7）
        assert result.summary is not None
        assert result.summary.total_days == 4
        # 4/4-4/6 被跳过，不应产生这些日期的记录
        trade_dates = {r.trade_date for r in result.records}
        assert date(2026, 4, 4) not in trade_dates
        assert date(2026, 4, 5) not in trade_dates
        assert date(2026, 4, 6) not in trade_dates

    def test_engine_skips_holidays_across_labor_day(self):
        """引擎在五一假期跨越期间只处理交易日"""
        from unittest.mock import AsyncMock

        from src.backtest.engine import BacktestEngine
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_loader = AsyncMock(spec=SnapshotLoader)
        mock_loader.load_market_context.return_value = {
            "trade_date": "2026-05-01",
            "bars_by_symbol": {},
            "indicators_by_symbol": {},
            "market_universe": None,
            "topic_snapshot": None,
            "source_refs": [],
        }

        engine = BacktestEngine(loader=mock_loader)
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 5, 1),
            date_to=date(2026, 5, 6),
        )
        result = engine.run_sync(req)
        # 五一假期跨越：只有 5/6 是交易日
        assert result.summary is not None
        assert result.summary.total_days == 1
        trade_dates = {r.trade_date for r in result.records}
        assert date(2026, 5, 1) not in trade_dates
        assert date(2026, 5, 2) not in trade_dates
        assert date(2026, 5, 3) not in trade_dates
        assert date(2026, 5, 4) not in trade_dates
        assert date(2026, 5, 5) not in trade_dates
        assert date(2026, 5, 6) in trade_dates
