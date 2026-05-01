"""NTL-S11-008: 规则池回测单元测试"""
import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.backtest.engine import BacktestEngine
from src.backtest.schemas import BacktestResult, BacktestSummary, BacktestTradeRecord
from src.rule_pool.models import RulePool
from src.rule_pool.schemas import RuleBacktestResult


class TestBacktestEngineRulePool:
    """BacktestEngine 规则池回测功能测试"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的 AsyncSession"""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def mock_loader(self):
        """创建模拟的 SnapshotLoader"""
        loader = MagicMock()
        loader.load_market_context = AsyncMock(return_value={
            "trade_date": "2026-04-01",
            "bars_by_symbol": {},
            "indicators_by_symbol": {},
        })
        return loader

    @pytest.fixture
    def sample_rules(self):
        """创建示例规则列表"""
        rules = []
        for i in range(3):
            rule = MagicMock(spec=RulePool)
            rule.rule_id = f"rule_test_{i:03d}"
            rule.initial_confidence = 0.8
            rule.validated_confidence = 0.7
            rule.review_status = "approved"
            rule.extraction_layer = {
                "rule_type": "breakout",
                "mapped_condition": {"indicator": "rsi", "operator": "<", "threshold": 30},
            }
            rules.append(rule)
        return rules

    @pytest.mark.asyncio
    async def test_run_rules_backtest_empty_rules(self, mock_session):
        """测试规则为空时的回测行为"""
        engine = BacktestEngine()

        # Mock repository 返回空列表
        with patch("src.rule_pool.repository.RulePoolRepository") as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_rules_by_status = AsyncMock(return_value=[])

            result = await engine.run_rules_backtest(
                session=mock_session,
                rule_ids=None,
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
            )

            assert result is not None
            assert isinstance(result, BacktestResult)
            assert result.request_trader_id == "rule_pool"
            assert result.summary.total_trades == 0

    @pytest.mark.asyncio
    async def test_run_rules_backtest_with_rules(self, mock_session, sample_rules):
        """测试规则池回测基本流程"""
        engine = BacktestEngine()

        with patch("src.rule_pool.repository.RulePoolRepository") as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_rules_by_status = AsyncMock(return_value=sample_rules)
            mock_repo_instance.get_rule_by_id = AsyncMock(side_effect=lambda rid: next((r for r in sample_rules if r.rule_id == rid), None))
            mock_repo_instance.update_backtest_result = AsyncMock(return_value=True)

            result = await engine.run_rules_backtest(
                session=mock_session,
                rule_ids=None,
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
                min_confidence=0.5,
            )

            assert result is not None
            assert isinstance(result, BacktestResult)
            mock_repo_instance.update_backtest_result.assert_called()

    @pytest.mark.asyncio
    async def test_run_rules_backtest_specific_rule_ids(self, mock_session, sample_rules):
        """测试指定 rule_ids 的回测"""
        engine = BacktestEngine()

        with patch("src.rule_pool.repository.RulePoolRepository") as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_rule_by_id = AsyncMock(side_effect=lambda rid: next((r for r in sample_rules if r.rule_id == rid), None))
            mock_repo_instance.update_backtest_result = AsyncMock(return_value=True)

            result = await engine.run_rules_backtest(
                session=mock_session,
                rule_ids=["rule_test_001", "rule_test_002"],
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
            )

            assert result is not None
            assert isinstance(result, BacktestResult)
            # 验证按 ID 查询被调用
            assert mock_repo_instance.get_rule_by_id.call_count == 2

    @pytest.mark.asyncio
    async def test_run_rules_backtest_min_confidence_filter(self, mock_session, sample_rules):
        """测试置信度阈值过滤"""
        engine = BacktestEngine()

        with patch("src.rule_pool.repository.RulePoolRepository") as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_rules_by_status = AsyncMock(return_value=sample_rules)
            mock_repo_instance.update_backtest_result = AsyncMock(return_value=True)

            # 设置高置信度阈值，应该过滤掉所有规则
            result = await engine.run_rules_backtest(
                session=mock_session,
                rule_ids=None,
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
                min_confidence=0.9,  # 高于所有规则的置信度
            )

            assert result is not None
            assert result.summary.total_trades == 0

    def test_aggregate_rule_results_empty(self):
        """测试空结果的聚合"""
        engine = BacktestEngine()

        result = engine._aggregate_rule_results([])

        assert result is not None
        assert isinstance(result, BacktestResult)
        assert result.summary.total_trades == 0

    def test_aggregate_rule_results_single(self):
        """测试单条规则的聚合"""
        engine = BacktestEngine()

        results = [
            RuleBacktestResult(
                run_id="run_001",
                run_at=datetime.now(),
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
                total_trades=20,
                hit_trades=12,
                miss_trades=8,
                hit_rate=0.6,
                avg_return=0.02,
                avg_win_return=0.04,
                avg_loss_return=-0.02,
                sharpe_ratio=1.2,
                max_drawdown=0.05,
                sample_count=20,
            )
        ]

        result = engine._aggregate_rule_results(results)

        assert result is not None
        assert isinstance(result, BacktestResult)
        assert result.summary.total_trades == 20
        assert result.summary.valid_trades == 12
        assert result.summary.win_rate == 0.6

    def test_aggregate_rule_results_multiple(self):
        """测试多条规则的聚合"""
        engine = BacktestEngine()

        results = [
            RuleBacktestResult(
                run_id="run_001",
                run_at=datetime.now(),
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
                total_trades=20,
                hit_trades=12,
                miss_trades=8,
                hit_rate=0.6,
                avg_return=0.02,
                avg_win_return=0.04,
                avg_loss_return=-0.02,
                sharpe_ratio=1.2,
                max_drawdown=0.05,
                sample_count=20,
            ),
            RuleBacktestResult(
                run_id="run_002",
                run_at=datetime.now(),
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
                total_trades=30,
                hit_trades=18,
                miss_trades=12,
                hit_rate=0.6,
                avg_return=0.015,
                avg_win_return=0.03,
                avg_loss_return=-0.015,
                sharpe_ratio=1.0,
                max_drawdown=0.06,
                sample_count=30,
            ),
        ]

        result = engine._aggregate_rule_results(results)

        assert result is not None
        assert isinstance(result, BacktestResult)
        assert result.summary.total_trades == 50
        assert result.summary.valid_trades == 30
        # 整体命中率：(12+18)/(20+30) = 30/50 = 0.6
        assert result.summary.win_rate == pytest.approx(0.6, rel=0.01)

    @pytest.mark.asyncio
    async def test_backtest_single_rule_returns_result(self, mock_session):
        """测试单条规则回测返回 RuleBacktestResult"""
        engine = BacktestEngine()

        # 创建模拟规则
        rule = MagicMock(spec=RulePool)
        rule.rule_id = "rule_single_001"
        rule.extraction_layer = {
            "rule_type": "breakout",
            "mapped_condition": {"indicator": "rsi", "operator": "<", "threshold": 30},
        }

        result = await engine._backtest_single_rule(
            rule=rule,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
        )

        assert result is not None
        assert isinstance(result, RuleBacktestResult)
        assert result.run_id is not None
        assert result.start_date == date(2026, 4, 1)
        assert result.end_date == date(2026, 4, 30)

    @pytest.mark.asyncio
    async def test_run_rules_backtest_updates_db(self, mock_session, sample_rules):
        """测试回测结果更新到数据库"""
        engine = BacktestEngine()

        with patch("src.rule_pool.repository.RulePoolRepository") as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_rules_by_status = AsyncMock(return_value=sample_rules)
            mock_repo_instance.update_backtest_result = AsyncMock(return_value=True)

            result = await engine.run_rules_backtest(
                session=mock_session,
                rule_ids=None,
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
            )

            # 验证每条规则都调用了 update_backtest_result
            assert mock_repo_instance.update_backtest_result.call_count == len(sample_rules)

            # 验证调用参数
            for call in mock_repo_instance.update_backtest_result.call_args_list:
                assert call[1]["rule_id"] in [r.rule_id for r in sample_rules]


class TestBacktestEngineRulePoolIntegration:
    """规则池回测与其他模块的集成测试"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的 AsyncSession"""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.mark.asyncio
    async def test_run_rules_backtest_with_confidence_computation(self, mock_session):
        """测试规则回测与置信度计算的集成"""
        from src.rule_backtest.confidence import compute_confidence_adjustment

        engine = BacktestEngine()

        # 创建规则
        rule = MagicMock(spec=RulePool)
        rule.rule_id = "rule_conf_001"
        rule.initial_confidence = 0.8
        rule.validated_confidence = 0.7
        rule.review_status = "approved"
        rule.extraction_layer = {"rule_type": "breakout"}

        with patch("src.rule_pool.repository.RulePoolRepository") as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_rule_by_id = AsyncMock(return_value=rule)
            mock_repo_instance.update_backtest_result = AsyncMock(return_value=True)

            result = await engine.run_rules_backtest(
                session=mock_session,
                rule_ids=["rule_conf_001"],
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
            )

            # 验证置信度更新被调用
            mock_repo_instance.update_backtest_result.assert_called_once()
            call_kwargs = mock_repo_instance.update_backtest_result.call_args[1]
            backtest_result = call_kwargs["backtest_result"]

            # 验证回测结果包含必要字段
            assert backtest_result.sample_count > 0
            assert backtest_result.hit_rate >= 0.0

            # 验证置信度调整计算
            adjusted = compute_confidence_adjustment(
                initial_confidence=call_kwargs["initial_confidence"],
                backtest_result=backtest_result,
                prior_weight=20,
            )
            assert 0.0 <= adjusted <= 1.0