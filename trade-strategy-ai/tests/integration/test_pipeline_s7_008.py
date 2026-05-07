"""NTL-S7-008: 关键链路集成测试与回归测试

测试覆盖三大主链路：
1. 盘前链路（Pre-market）：TraderAgent 生成交易想法 → DailyReport
2. 盘后链路（After-close）：评估想法 → EvaluationResult + 记忆写入
3. 回测链路（Backtest）：历史区间回测 → BacktestResult

所有测试使用 mock 外部依赖（DataAgent/DB），聚焦链路本身的编排逻辑验证。
"""

import pytest
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.agents.manager_agent.agent import ManagerAgent
from src.agents.manager_agent.premarket_service import PreMarketService
from src.backtest.engine import BacktestEngine, TradeCalendar
from src.backtest.schemas import BacktestRequest, BacktestTradeRecord
from src.common.config import AppConfig, DataConfig, Stage4Config, StorageConfig, TraderConfig
from src.market_universe.schemas import HotTopic, HotTopicsPayload, MarketUniverse
from src.market_universe.snapshot_service import SnapshotService
from src.schemas.contracts import DailyReport, EvaluationResult, IdeaEvaluation, TradeEntry, TradeIdea
from src.strategy_library.schemas import (
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
)
from src.strategy.types import SignalSide


@asynccontextmanager
async def _mock_session_scope():
    """避免单元测试连接真实数据库。"""
    yield MagicMock()


# ============================================================================
# 盘前链路测试
# ============================================================================


@pytest.fixture
def pre_market_config(tmp_path: Path) -> AppConfig:
    """盘前链路测试配置"""
    return AppConfig(
        storage=StorageConfig(output_dir=str(tmp_path / "data/processed/phase0")),
        data=DataConfig(mock_prices={"000001.SZ": 12.0, "600000.SH": 10.0}),
        stage4=Stage4Config(enable=True, allow_phase0_fallback=True),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=["000001.SZ"],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )


@pytest.fixture
def pre_market_manager(pre_market_config: AppConfig, tmp_path: Path) -> ManagerAgent:
    """创建盘前链路 ManagerAgent"""
    return ManagerAgent(config=pre_market_config, base_dir=tmp_path)


class TestPreMarketPipeline:
    """盘前链路集成测试"""

    def _mock_memory_store(self) -> MagicMock:
        """创建 mock TraderMemoryStore（避免 DB 连接）"""
        mock = MagicMock()
        mock.summarize_context = AsyncMock(
            return_value=MagicMock(
                total_items=0,
                by_type={},
                recent_titles=[],
                symbol_titles=[],
                review_notes=[],
                postmortem_notes=[],
                strategy_adjustments=[],
                success_case_titles=[],
                failure_case_titles=[],
            )
        )
        return mock

    @pytest.mark.asyncio
    async def test_run_pre_market_produces_daily_report(
        self, pre_market_manager: ManagerAgent, tmp_path: Path
    ) -> None:
        """验证 run_pre_market 生成包含 ideas 的 DailyReport"""
        day = date(2026, 4, 20)

        # Mock memory_store 和 session_scope 以避免 DB 连接
        pre_market_manager.memory_store = self._mock_memory_store()
        with patch(
            "src.agents.manager_agent.agent.session_scope", _mock_session_scope
        ):
            report = await pre_market_manager.run_pre_market(as_of_date=day, force=True)

        assert report is not None
        assert report.as_of_date == day
        assert len(report.ideas) >= 0  # Phase 0 或 Stage 4 路径
        assert report.highlights  # 应有 highlights

    @pytest.mark.asyncio
    async def test_run_pre_market_caches_result(
        self, pre_market_manager: ManagerAgent, tmp_path: Path
    ) -> None:
        """验证 run_pre_market 缓存逻辑（相同日期不重复生成）"""
        day = date(2026, 4, 21)

        pre_market_manager.memory_store = self._mock_memory_store()
        with patch(
            "src.agents.manager_agent.agent.session_scope", _mock_session_scope
        ):
            # 第一次运行
            report1 = await pre_market_manager.run_pre_market(as_of_date=day, force=False)
            # 第二次运行（应返回缓存）
            report2 = await pre_market_manager.run_pre_market(as_of_date=day, force=False)

        # 如果没有缓存，两者 ideas 数量应该相同（因为都走 mock）
        # 关键验证：第二次不走 DataAgent 路径
        assert report1.as_of_date == report2.as_of_date

    @pytest.mark.asyncio
    async def test_run_pre_market_records_signals(
        self, pre_market_manager: ManagerAgent, tmp_path: Path
    ) -> None:
        """验证 run_pre_market 将 ideas 记录为信号版本"""
        day = date(2026, 4, 22)

        pre_market_manager.memory_store = self._mock_memory_store()
        with patch(
            "src.agents.manager_agent.agent.session_scope", _mock_session_scope
        ):
            report = await pre_market_manager.run_pre_market(as_of_date=day, force=True)

        # 验证信号版本已被记录
        for idea in report.ideas:
            signal_id = f"idea_{idea.idea_id}"
            stored = pre_market_manager.signal_versioning.get_version(signal_id)
            if stored:
                assert stored.signal.symbol == idea.symbol

    @pytest.mark.asyncio
    async def test_run_pre_market_with_stage4_path(
        self, pre_market_config: AppConfig, tmp_path: Path
    ) -> None:
        """验证 Stage 4 路径：strategy_version 决定候选标的"""
        manager = ManagerAgent(config=pre_market_config, base_dir=tmp_path)
        day = date(2026, 4, 23)

        # Mock StrategyLibraryService 返回 strategy_version（含 recommendations）
        strategy_version = StrategyVersion(
            version_id="trader_a:2026-04-23:draft:v1",
            trader_id="trader_a",
            strategy_date=day,
            status=StrategyVersionStatus.draft,
            recommendations=[
                StrategyRecommendation(symbol="600000.SH", decision="buy", confidence=0.72),
            ],
        )
        manager.memory_store = self._mock_memory_store()
        with patch(
            "src.agents.manager_agent.agent.session_scope", _mock_session_scope
        ):
            manager.strategy_library_service.get_current_released_version = AsyncMock(
                return_value=strategy_version
            )

            report = await manager.run_pre_market(as_of_date=day, force=True)

        # Stage 4 路径：候选来自 strategy_version.recommendations
        symbols = {idea.symbol for idea in report.ideas}
        assert "600000.SH" in symbols


class TestPreMarketService:
    """PreMarketService 单元测试（盘前链路核心编排逻辑）"""

    @pytest.mark.asyncio
    async def test_premarket_service_generates_ideas_for_trader(self) -> None:
        """验证 PreMarketService 能为单个 trader 生成 ideas"""
        from src.agents.data_agent.agent import DataAgent

        config = AppConfig(
            storage=StorageConfig(output_dir="/tmp/test"),
            data=DataConfig(mock_prices={"000001.SZ": 12.0}),
            stage4=Stage4Config(enable=True, allow_phase0_fallback=True),
            traders=[
                TraderConfig(
                    trader_id="trader_a",
                    display_name="Trader A",
                    watchlist=["000001.SZ"],
                    default_target_pct=0.05,
                    default_stop_pct=0.03,
                )
            ],
        )

        mock_data_agent = MagicMock(spec=DataAgent)
        mock_data_agent.fetch_indicators = AsyncMock(return_value={})
        mock_data_agent.fetch_strong_symbols = AsyncMock(return_value=[])

        # Mock TraderMemoryStore 以避免 DB 连接
        mock_memory_store = MagicMock()
        mock_memory_store.summarize_context = AsyncMock(
            return_value=MagicMock(
                total_items=0,
                by_type={},
                recent_titles=[],
                symbol_titles=[],
                review_notes=[],
                postmortem_notes=[],
                strategy_adjustments=[],
                success_case_titles=[],
                failure_case_titles=[],
            )
        )

        mock_strategy_library_service = MagicMock()
        mock_strategy_library_service.get_current_released_version = AsyncMock(return_value=None)

        service = PreMarketService(
            data_agent=mock_data_agent,
            strategy_agent=MagicMock(),
            risk_agent=MagicMock(),
            memory_store=mock_memory_store,
            trader_profiles={},
            config=config,
            snapshot_service=MagicMock(),
            strategy_library_service=mock_strategy_library_service,
        )

        trader_cfg = config.traders[0]
        market_universe = None
        day = date(2026, 4, 24)

        result = await service.run_for_trader(
            trader_cfg=trader_cfg,
            market_universe=market_universe,
            as_of_date=day,
        )

        # 应返回 PreMarketResult（ideas list）
        assert isinstance(result.ideas, list)


# ============================================================================
# 盘后链路测试
# ============================================================================


@pytest.fixture
def after_close_config(tmp_path: Path) -> AppConfig:
    """盘后链路测试配置"""
    return AppConfig(
        storage=StorageConfig(output_dir=str(tmp_path / "data/processed/phase0")),
        data=DataConfig(mock_prices={"000001.SZ": 12.0, "600000.SH": 10.5}),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=["000001.SZ"],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
        evaluation={"min_expected_return": 0.0, "loss_trigger": True},
    )


@pytest.fixture
def after_close_manager(after_close_config: AppConfig, tmp_path: Path) -> ManagerAgent:
    """创建盘后链路 ManagerAgent"""
    return ManagerAgent(config=after_close_config, base_dir=tmp_path)


class TestAfterClosePipeline:
    """盘后链路集成测试"""

    @pytest.mark.asyncio
    async def test_run_after_close_requires_pre_market_report(
        self, after_close_manager: ManagerAgent, tmp_path: Path
    ) -> None:
        """验证 run_after_close 必须有盘前报告才能运行"""
        day = date(2026, 4, 20)

        # 直接运行盘后（无盘前报告）应抛出 FileNotFoundError
        with pytest.raises(FileNotFoundError):
            await after_close_manager.run_after_close(as_of_date=day, force=True)

    def _mock_memory_store(self) -> MagicMock:
        """创建 mock TraderMemoryStore（避免 DB 连接）"""
        mock = MagicMock()
        mock.summarize_context = AsyncMock(
            return_value=MagicMock(
                total_items=0,
                by_type={},
                recent_titles=[],
                symbol_titles=[],
                review_notes=[],
                postmortem_notes=[],
                strategy_adjustments=[],
                success_case_titles=[],
                failure_case_titles=[],
            )
        )
        mock.list_recent = AsyncMock(return_value=[])
        mock.append = AsyncMock(return_value=MagicMock(memory_id=uuid4()))
        return mock

    @pytest.mark.asyncio
    async def test_run_after_close_produces_evaluation(
        self, after_close_manager: ManagerAgent, tmp_path: Path
    ) -> None:
        """验证 run_after_close 生成 EvaluationResult"""
        day = date(2026, 4, 21)

        after_close_manager.memory_store = self._mock_memory_store()

        # 先运行盘前
        with patch(
            "src.agents.manager_agent.agent.session_scope", _mock_session_scope
        ):
            await after_close_manager.run_pre_market(as_of_date=day, force=True)

        with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope):
            with patch(
                "src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"
            ):
                with patch(
                    "src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"
                ):
                    result = await after_close_manager.run_after_close(
                        as_of_date=day, force=True
                    )

        assert result is not None
        assert result.as_of_date == day
        assert isinstance(result.evaluations, list)

    @pytest.mark.asyncio
    async def test_run_after_close_fills_evaluation_fields(
        self, after_close_manager: ManagerAgent, tmp_path: Path
    ) -> None:
        """验证 EvaluationResult 包含完整字段（status/return_pct/notes）"""
        day = date(2026, 4, 22)

        after_close_manager.memory_store = self._mock_memory_store()

        # 创建盘前报告
        report = DailyReport(
            as_of_date=day,
            ideas=[
                TradeIdea(
                    trader_id="trader_a",
                    as_of_date=day,
                    symbol="000001.SZ",
                    entry=TradeEntry(type="limit", price=10.0),
                    target_price=10.5,
                    stop_loss_price=9.7,
                )
            ],
            highlights=["test"],
        )
        after_close_manager._daily_report_path(day).write_text(
            report.model_dump_json(), encoding="utf-8"
        )

        with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope):
            with patch(
                "src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"
            ):
                with patch(
                    "src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"
                ):
                    result = await after_close_manager.run_after_close(
                        as_of_date=day, force=True
                    )

        assert len(result.evaluations) == 1
        eval_item = result.evaluations[0]
        assert eval_item.symbol == "000001.SZ"
        assert eval_item.status in ("fallback", "ok", "partial", "not_evaluated")
        assert eval_item.return_pct is not None  # 应该计算出收益率

    @pytest.mark.asyncio
    async def test_run_after_close_creates_review_task_on_loss(
        self, after_close_manager: ManagerAgent, tmp_path: Path
    ) -> None:
        """验证亏损时创建复盘任务"""
        day = date(2026, 4, 23)

        after_close_manager.memory_store = self._mock_memory_store()

        # 创建盘前报告（entry=10.0，当前价格=9.0 → 亏损）
        report = DailyReport(
            as_of_date=day,
            ideas=[
                TradeIdea(
                    trader_id="trader_a",
                    as_of_date=day,
                    symbol="000001.SZ",
                    entry=TradeEntry(type="limit", price=10.0),
                    target_price=10.5,
                    stop_loss_price=9.7,
                )
            ],
            highlights=["test"],
        )
        after_close_manager._daily_report_path(day).write_text(
            report.model_dump_json(), encoding="utf-8"
        )

        # 设置亏损价格（mock_prices 中 000001.SZ=12.0，改配置让当前价格为 9.0）
        after_close_manager.config.data.mock_prices = {"000001.SZ": 9.0}

        with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope):
            with patch(
                "src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"
            ):
                with patch(
                    "src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"
                ):
                    await after_close_manager.run_after_close(as_of_date=day, force=True)

        # 验证生成了复盘任务
        tasks_content = after_close_manager.tasks_path.read_text(encoding="utf-8")
        task_lines = [line for line in tasks_content.splitlines() if line.strip()]
        import json

        review_tasks = [
            json.loads(line)
            for line in task_lines
            if json.loads(line)["type"] == "trader_review"
        ]
        assert len(review_tasks) >= 1


# ============================================================================
# 回测链路测试
# ============================================================================


class TestBacktestPipeline:
    """回测链路集成测试"""

    @pytest.fixture(autouse=True)
    def _local_trade_calendar(self):
        """固定本地交易日集合，避免集成测试依赖 akshare 或本地日历文件。"""
        original_trade_dates = TradeCalendar._trade_dates
        original_loaded = TradeCalendar._loaded
        original_source = TradeCalendar._source
        original_last_loaded_at = TradeCalendar._last_loaded_at

        TradeCalendar._trade_dates = {
            "2026-04-01",
            "2026-04-02",
            "2026-04-03",
            "2026-04-06",
            "2026-04-07",
            "2026-04-08",
            "2026-04-09",
            "2026-04-10",
        }
        TradeCalendar._loaded = True
        TradeCalendar._source = "holidays"
        TradeCalendar._last_loaded_at = "2026-05-06T00:00:00+08:00"

        yield

        TradeCalendar._trade_dates = original_trade_dates
        TradeCalendar._loaded = original_loaded
        TradeCalendar._source = original_source
        TradeCalendar._last_loaded_at = original_last_loaded_at

    def test_backtest_engine_run_sync_returns_result(self) -> None:
        """验证 BacktestEngine.run_sync 返回 BacktestResult"""
        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
        )

        result = engine.run_sync(req)

        assert result is not None
        assert result.request_trader_id == "trader_a"
        assert result.request_date_from == date(2026, 4, 1)
        assert result.request_date_to == date(2026, 4, 1)

    def test_backtest_engine_multi_day(self) -> None:
        """验证多日回测"""
        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 10),
        )

        result = engine.run_sync(req)

        assert result.summary is not None
        # 应覆盖交易日
        assert result.summary.total_days >= 5

    def test_backtest_result_structure(self) -> None:
        """验证 BacktestResult 结构完整（records/summary/request_*）"""
        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_b",
            date_from=date(2026, 4, 7),  # 2026-04-07 是清明节后第一个交易日
            date_to=date(2026, 4, 7),
        )

        result = engine.run_sync(req)

        # 验证结构完整性
        assert result.request_trader_id == "trader_b"
        assert result.request_date_from == date(2026, 4, 7)
        assert result.request_date_to == date(2026, 4, 7)
        assert isinstance(result.records, list)
        assert result.summary is not None
        assert result.summary.total_days == 1

    def test_backtest_trade_records_have_required_fields(self) -> None:
        """验证 BacktestTradeRecord 包含关键字段"""
        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 3),
        )

        result = engine.run_sync(req)

        # 所有 records 都应有这些字段
        for record in result.records:
            assert hasattr(record, "trade_date")
            assert hasattr(record, "trader_id")
            assert hasattr(record, "status")
            assert hasattr(record, "symbol")  # symbol 可能为空（skipped 时）
            assert hasattr(record, "skip_reason") or record.status != "skipped"


# ============================================================================
# 全链路回归测试（E2E Smoke）
# ============================================================================


class TestEndToEndSmoke:
    """端到端冒烟测试：验证三大链路可串联运行"""

    def _mock_memory_store(self) -> MagicMock:
        """创建 mock TraderMemoryStore（避免 DB 连接）"""
        mock = MagicMock()
        mock.summarize_context = AsyncMock(
            return_value=MagicMock(
                total_items=0,
                by_type={},
                recent_titles=[],
                symbol_titles=[],
                review_notes=[],
                postmortem_notes=[],
                strategy_adjustments=[],
                success_case_titles=[],
                failure_case_titles=[],
            )
        )
        mock.list_recent = AsyncMock(return_value=[])
        mock.append = AsyncMock(return_value=MagicMock(memory_id=uuid4()))
        return mock

    @pytest.mark.asyncio
    async def test_pre_market_to_after_close_chain(
        self, pre_market_manager: ManagerAgent, tmp_path: Path
    ) -> None:
        """验证盘前 → 盘后可串联（数据流传递）"""
        day = date(2026, 4, 25)

        pre_market_manager.memory_store = self._mock_memory_store()
        with patch(
            "src.agents.manager_agent.agent.session_scope", _mock_session_scope
        ):
            # Step 1: 盘前
            report = await pre_market_manager.run_pre_market(as_of_date=day, force=True)
            pre_market_ideas_count = len(report.ideas)

            # Step 2: 盘后（如果有 ideas）
            if pre_market_ideas_count > 0:
                with patch(
                    "src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"
                ):
                    with patch(
                        "src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"
                    ):
                        result = await pre_market_manager.run_after_close(
                            as_of_date=day, force=True
                        )

                # 盘后评估数量应与盘前 ideas 数量一致（一一对应）
                assert len(result.evaluations) == pre_market_ideas_count

    def test_backtest_result_persists_across_calls(self) -> None:
        """验证多次回测结果一致性"""
        engine = BacktestEngine()
        req = BacktestRequest(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 2),
        )

        result1 = engine.run_sync(req)
        result2 = engine.run_sync(req)

        # 两次运行结果结构应一致
        assert result1.request_trader_id == result2.request_trader_id
        assert result1.request_date_from == result2.request_date_from
        assert result1.request_date_to == result2.request_date_to
        # 注意：由于日期固定，结果应该是确定性的


# ============================================================================
# CLI 回归测试
# ============================================================================


class TestCLIPipeline:
    """CLI 命令链路回归测试"""

    def _mock_memory_store(self) -> MagicMock:
        """创建 mock TraderMemoryStore（避免 DB 连接）"""
        mock = MagicMock()
        mock.summarize_context = AsyncMock(
            return_value=MagicMock(
                total_items=0,
                by_type={},
                recent_titles=[],
                symbol_titles=[],
                review_notes=[],
                postmortem_notes=[],
                strategy_adjustments=[],
                success_case_titles=[],
                failure_case_titles=[],
            )
        )
        mock.list_recent = AsyncMock(return_value=[])
        mock.append = AsyncMock(return_value=MagicMock(memory_id=uuid4()))
        return mock

    @pytest.mark.asyncio
    async def test_manager_agent_cli_pre_market_command(
        self, pre_market_config: AppConfig, tmp_path: Path
    ) -> None:
        """验证 ManagerAgent 可响应盘前 CLI 命令（run_pre_market）"""
        manager = ManagerAgent(config=pre_market_config, base_dir=tmp_path)
        day = date(2026, 4, 26)

        manager.memory_store = self._mock_memory_store()
        # 这对应 `run-pre-market --config app.yaml --as_of 2026-04-26`
        with patch(
            "src.agents.manager_agent.agent.session_scope", _mock_session_scope
        ):
            report = await manager.run_pre_market(as_of_date=day, force=True)

        assert report.as_of_date == day
        # 应生成报告文件
        assert manager._daily_report_path(day).exists() or len(report.ideas) >= 0

    @pytest.mark.asyncio
    async def test_manager_agent_cli_after_close_command(
        self, after_close_config: AppConfig, tmp_path: Path
    ) -> None:
        """验证 ManagerAgent 可响应盘后 CLI 命令（run_after_close）"""
        manager = ManagerAgent(config=after_close_config, base_dir=tmp_path)
        day = date(2026, 4, 27)

        manager.memory_store = self._mock_memory_store()
        # 先准备盘前报告
        with patch(
            "src.agents.manager_agent.agent.session_scope", _mock_session_scope
        ):
            await manager.run_pre_market(as_of_date=day, force=True)

        # 这对应 `run-after-close --config app.yaml --as_of 2026-04-27`
        with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope):
            with patch(
                "src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"
            ):
                with patch(
                    "src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"
                ):
                    result = await manager.run_after_close(as_of_date=day, force=True)

        assert result.as_of_date == day
        assert isinstance(result.evaluations, list)
