"""
Alignment Agent 单元测试 — P3-022~P3-025。
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.agents.alignment_agent import (
    AlignmentAgent,
    AlignmentRequest,
    AlignmentResult,
    AlignmentStorage,
)
from src.alignment import (
    BehaviorProfile,
    BehaviorFitScore,
    ConflictDetection,
    ConflictDetectionResult,
    ConflictType,
    DetailedConfidenceScore,
    RuleMatchScore,
    StrategyRule,
    TradeRecord,
)


class TestAlignmentRequest:
    """AlignmentRequest 测试。"""

    def test_basic_request(self):
        """基本请求测试。"""
        rules = [
            StrategyRule(rule_id="r1", rule_type="entry", confidence=0.8),
            StrategyRule(rule_id="r2", rule_type="exit", confidence=0.7),
        ]

        request = AlignmentRequest(
            trader_id="trader1",
            rules=rules,
        )

        assert request.trader_id == "trader1"
        assert len(request.rules) == 2
        assert request.include_suggestions == True
        assert request.use_cache == True


class TestAlignmentResult:
    """AlignmentResult 测试。"""

    def test_basic_result(self):
        """基本结果测试。"""
        result = AlignmentResult(trader_id="trader1")

        assert result.trader_id == "trader1"
        assert result.generated_at is not None
        assert len(result.rule_match_scores) == 0
        assert result.cached == False

    def test_result_with_score(self):
        """带评分的结果测试。"""
        result = AlignmentResult(trader_id="trader1")
        result.detailed_score = DetailedConfidenceScore(
            trader_id="trader1",
            overall_score=0.75,
            grade="B",
            grade_label="一般",
        )

        assert result.detailed_score is not None
        assert result.detailed_score.overall_score == 0.75


class TestAlignmentAgent:
    """AlignmentAgent 测试。"""

    @pytest.fixture
    def agent(self):
        """创建 Agent 实例。"""
        return AlignmentAgent()

    @pytest.fixture
    def sample_rules(self):
        """示例规则。"""
        return [
            StrategyRule(
                rule_id="r1",
                rule_type="entry",
                instrument_focus="stock",
                confidence=0.8,
            ),
            StrategyRule(
                rule_id="r2",
                rule_type="exit",
                instrument_focus="stock",
                confidence=0.7,
            ),
        ]

    @pytest.fixture
    def sample_trades(self):
        """示例交易。"""
        return [
            TradeRecord(
                trade_id="t1",
                symbol="000001.SZ",
                side="buy",
                price=10.0,
                quantity=100.0,
                executed_at=datetime.now(),
            ),
            TradeRecord(
                trade_id="t2",
                symbol="000001.SZ",
                side="sell",
                price=11.0,
                quantity=100.0,
                executed_at=datetime.now(),
            ),
        ]

    @pytest.mark.asyncio
    async def test_run_basic(self, agent, sample_rules):
        """基本运行测试。"""
        request = AlignmentRequest(
            trader_id="trader1",
            rules=sample_rules,
        )

        result = await agent.run(request)

        assert result.trader_id == "trader1"
        assert result.rules_analyzed == 2
        assert len(result.rule_match_scores) == 2

    @pytest.mark.asyncio
    async def test_run_with_trades(self, agent, sample_rules, sample_trades):
        """带交易的运行测试。"""
        request = AlignmentRequest(
            trader_id="trader1",
            rules=sample_rules,
            trades=sample_trades,
        )

        result = await agent.run(request)

        assert result.trader_id == "trader1"
        assert result.trades_analyzed == 2
        assert result.conflicts is not None
        assert result.detailed_score is not None

    @pytest.mark.asyncio
    async def test_run_with_profile(self, agent, sample_rules, sample_trades):
        """带行为画像的运行测试。"""
        profile = BehaviorProfile(
            trader_id="trader1",
            label_distribution={"chase_rally": 0.6, "bottom_fish": 0.4},
            avg_hold_minutes=60.0,
            win_rate=0.6,
        )

        request = AlignmentRequest(
            trader_id="trader1",
            rules=sample_rules,
            trades=sample_trades,
            profile=profile,
        )

        result = await agent.run(request)

        assert result.behavior_fit is not None
        assert result.behavior_fit.fit_score >= 0.0

    @pytest.mark.asyncio
    async def test_run_incremental(self, agent, sample_rules, sample_trades):
        """增量运行测试。"""
        request1 = AlignmentRequest(
            trader_id="trader1",
            rules=sample_rules,
            trades=sample_trades[:1],  # 只有一笔交易
        )

        result1 = await agent.run(request1)
        assert result1.trades_analyzed == 1

        # 增量更新：添加新交易
        request2 = AlignmentRequest(
            trader_id="trader1",
            rules=sample_rules,
            trades=sample_trades,  # 两笔交易
        )

        result2 = await agent.run_incremental(request2, result1)
        assert result2.trades_analyzed == 2
        assert result2.cached == False

    def test_compute_conflict_penalty(self, agent):
        """冲突扣分计算测试。"""
        # 无冲突
        assert agent._compute_conflict_penalty(None) == 0.0

        conflicts_no_issues = ConflictDetection(
            trader_id="t1",
            total_conflicts=0,
        )
        assert agent._compute_conflict_penalty(conflicts_no_issues) == 0.0

        # 有冲突
        conflicts = ConflictDetection(
            trader_id="t1",
            total_conflicts=2,
            conflicts=[
                ConflictDetectionResult(
                    conflict_type=ConflictType.RULE_CONTRADICTION,
                    severity="critical",
                    message="Test",
                    involved_rules=["r1", "r2"],
                ),
            ],
        )
        penalty = agent._compute_conflict_penalty(conflicts)
        assert penalty > 0.0
        assert penalty <= 1.0


class TestAlignmentStorage:
    """AlignmentStorage 测试。"""

    def test_save_and_load(self, tmp_path):
        """保存和加载测试。"""
        storage = AlignmentStorage(storage_dir=tmp_path)

        # 创建结果
        result = AlignmentResult(trader_id="trader1")
        result.detailed_score = DetailedConfidenceScore(
            trader_id="trader1",
            overall_score=0.75,
            grade="B",
        )
        result.rules_analyzed = 2

        # 保存
        filepath = storage.save(result)
        assert filepath.exists()

        # 加载
        loaded = storage.load("trader1")
        assert loaded is not None
        assert loaded.trader_id == "trader1"
        assert loaded.rules_analyzed == 2

    def test_list_versions(self, tmp_path):
        """列出版本测试。"""
        storage = AlignmentStorage(storage_dir=tmp_path)

        # 保存多个版本
        for i in range(3):
            result = AlignmentResult(trader_id="trader1")
            result.rules_analyzed = i
            storage.save(result)

        versions = storage.list_versions("trader1")
        assert len(versions) <= 10  # 最多 10 个

    def test_load_nonexistent(self, tmp_path):
        """加载不存在的版本测试。"""
        storage = AlignmentStorage(storage_dir=tmp_path)
        loaded = storage.load("nonexistent_trader")
        assert loaded is None


class TestIntegration:
    """集成测试。"""

    @pytest.mark.asyncio
    async def test_full_pipeline(self, tmp_path):
        """完整流程测试。"""
        # 创建 Agent
        agent = AlignmentAgent(
            cache_dir=str(tmp_path / "cache"),
            storage_dir=str(tmp_path / "storage"),
        )

        # 准备数据
        rules = [
            StrategyRule(rule_id="r1", rule_type="entry", confidence=0.8),
            StrategyRule(rule_id="r2", rule_type="exit", confidence=0.7),
        ]

        trades = [
            TradeRecord(
                trade_id="t1",
                symbol="000001.SZ",
                side="buy",
                price=10.0,
                quantity=100.0,
                executed_at=datetime.now(),
            ),
        ]

        request = AlignmentRequest(
            trader_id="trader1",
            rules=rules,
            trades=trades,
            include_suggestions=True,
        )

        # 执行
        result = await agent.run(request)

        # 验证
        assert result.trader_id == "trader1"
        assert result.rules_analyzed == 2
        assert result.trades_analyzed == 1
        assert result.detailed_score is not None
        assert result.text_report is not None
        assert len(result.text_report) > 0

        # 验证持久化
        versions = agent.list_result_versions("trader1")
        assert len(versions) > 0
