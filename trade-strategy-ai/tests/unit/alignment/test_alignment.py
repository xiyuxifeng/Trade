"""
对齐分析框架单元测试 — P3-001~P3-004。
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

from src.alignment import (
    AlignmentReport,
    BehaviorFitScore,
    ConflictDetection,
    ConflictDetectionResult,
    ConflictType,
    ConfidenceScore,
    MatchResult,
    RuleMatchScore,
    StrategyRule,
    TradeRecord,
)
from src.alignment.scoring import (
    _check_instrument_match,
    _check_rule_type_direction_match,
    _cosine_similarity,
    behavior_fit_score,
    confidence_scoring,
    rule_match_score,
)
from src.alignment.conflict import (
    _are_rules_contradictory,
    _compute_rule_overlap,
    _detect_behavior_deviations,
    _detect_parameter_mismatches,
    _detect_rule_contradictions,
    _detect_rule_overlaps,
    _detect_temporal_conflicts,
    detect_conflicts,
)
from src.persona.behavior import BehaviorLabel


class TestRuleMatchScore:
    """rule_match_score 测试 — P3-001。"""

    def test_basic_matching(self):
        """基本匹配测试。"""
        rule = StrategyRule(
            rule_id="r1",
            rule_type="entry",
            confidence=0.8,
        )
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
        result = rule_match_score(rule, trades)

        assert isinstance(result, RuleMatchScore)
        assert result.rule_id == "r1"

    def test_no_trades(self):
        """无交易时返回零值。"""
        rule = StrategyRule(rule_id="r1", rule_type="entry")
        result = rule_match_score(rule, [])

        assert result.total_trades == 0
        assert result.match_rate == 0.0

    def test_instrument_match(self):
        """标的类型匹配。"""
        assert _check_instrument_match("stock", "000001.SZ") == True
        assert _check_instrument_match("stock", "510300.SH") == False  # .SH 但是 ETF，不是股票
        assert _check_instrument_match("etf", "510300.SH") == True
        assert _check_instrument_match("mixed", "ANY") == True

    def test_direction_match(self):
        """方向匹配。"""
        assert _check_rule_type_direction_match("entry", "buy") == True
        assert _check_rule_type_direction_match("exit", "sell") == True
        assert _check_rule_type_direction_match("filter", "buy") == True


class TestBehaviorFitScore:
    """behavior_fit_score 测试 — P3-002。"""

    def test_basic_fit_score(self):
        """基本适配度测试。"""
        from src.alignment.types import BehaviorProfile

        profile = BehaviorProfile(
            trader_id="trader1",
            label_distribution={"chase_rally": 0.6, "bottom_fish": 0.4},
            avg_hold_minutes=60.0,
            win_rate=0.6,
        )
        rules = [
            StrategyRule(rule_id="r1", rule_type="entry", confidence=0.8),
            StrategyRule(rule_id="r2", rule_type="exit", confidence=0.8),
        ]
        result = behavior_fit_score(profile, rules)

        assert isinstance(result.fit_score, float)
        assert 0 <= result.fit_score <= 1.0

    def test_cosine_similarity(self):
        """余弦相似度。"""
        a = {"a": 0.5, "b": 0.5}
        b = {"a": 0.5, "b": 0.5}
        assert _cosine_similarity(a, b) == pytest.approx(1.0, abs=1e-6)

        a = {"a": 1.0, "b": 0.0}
        b = {"a": 0.0, "b": 1.0}
        assert _cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)


class TestConflictDetection:
    """conflict_detection 测试 — P3-003。"""

    def test_detect_rule_contradictions(self):
        """规则矛盾检测。"""
        rules = [
            StrategyRule(
                rule_id="r1",
                rule_type="entry",
                condition={"indicator": "MA20", "operator": ">"},
            ),
            StrategyRule(
                rule_id="r2",
                rule_type="entry",
                condition={"indicator": "MA20", "operator": "<"},
            ),
        ]
        conflicts = _detect_rule_contradictions(rules)
        assert len(conflicts) >= 1  # 应该有矛盾

    def test_detect_rule_overlaps(self):
        """规则重叠检测。"""
        rules = [
            StrategyRule(
                rule_id="r1",
                rule_type="entry",
                condition={"indicator": "MA20", "threshold": 10.0},
            ),
            StrategyRule(
                rule_id="r2",
                rule_type="entry",
                condition={"indicator": "MA20", "threshold": 10.0},
            ),
        ]
        conflicts = _detect_rule_overlaps(rules)
        assert len(conflicts) >= 1  # 应该检测到重叠

    def test_compute_rule_overlap(self):
        """规则重叠度计算。"""
        rule1 = StrategyRule(
            rule_id="r1",
            rule_type="entry",
            condition={"a": 1, "b": 2},
        )
        rule2 = StrategyRule(
            rule_id="r2",
            rule_type="entry",
            condition={"a": 1, "b": 3},
        )
        overlap = _compute_rule_overlap(rule1, rule2)
        assert 0 <= overlap <= 1.0

    def test_detect_conflicts_empty(self):
        """无规则时返回空。"""
        result = detect_conflicts([])
        assert result.total_conflicts == 0
        assert isinstance(result, ConflictDetection)

    def test_conflict_types(self):
        """冲突类型枚举。"""
        assert ConflictType.RULE_CONTRADICTION.value == "rule_contradiction"
        assert ConflictType.RULE_OVERLAP.value == "rule_overlap"
        assert ConflictType.BEHAVIOR_DEVIATION.value == "behavior_deviation"


class TestConfidenceScoring:
    """confidence_scoring 测试 — P3-004。"""

    def test_basic_confidence(self):
        """基本可信度测试。"""
        from src.alignment.types import BehaviorProfile

        rule_scores = [
            RuleMatchScore(rule_id="r1", match_rate=0.8, avg_score=0.7),
            RuleMatchScore(rule_id="r2", match_rate=0.6, avg_score=0.5),
        ]
        behavior_fit = BehaviorFitScore(
            trader_id="trader1",
            fit_score=0.75,
        )
        result = confidence_scoring(rule_scores, behavior_fit, conflict_penalty=0.1)

        assert isinstance(result, ConfidenceScore)
        assert 0 <= result.overall_score <= 1.0
        assert "rule_match_score" in result.score_breakdown
        assert "behavior_fit_score" in result.score_breakdown

    def test_conflict_penalty(self):
        """冲突扣分测试。"""
        from src.alignment.types import BehaviorProfile

        rule_scores = [RuleMatchScore(rule_id="r1", match_rate=0.9)]
        behavior_fit = BehaviorFitScore(trader_id="t1", fit_score=0.9)

        result_high_penalty = confidence_scoring(rule_scores, behavior_fit, conflict_penalty=0.5)
        result_low_penalty = confidence_scoring(rule_scores, behavior_fit, conflict_penalty=0.1)

        assert result_high_penalty.overall_score < result_low_penalty.overall_score

    def test_custom_weights(self):
        """自定义权重测试。"""
        from src.alignment.types import BehaviorProfile

        rule_scores = [RuleMatchScore(rule_id="r1", match_rate=0.5)]
        behavior_fit = BehaviorFitScore(trader_id="t1", fit_score=0.5)

        weights = {"rule_match": 0.6, "behavior_fit": 0.3, "conflict_penalty": 0.1}
        result = confidence_scoring(rule_scores, behavior_fit, conflict_penalty=0.0, weights=weights)

        assert result.overall_score > 0


class TestAreRulesContradictory:
    """规则矛盾判断测试。"""

    def test_ma_contradiction(self):
        """MA 条件矛盾。"""
        rule1 = StrategyRule(
            rule_id="r1",
            rule_type="entry",
            condition={"indicator": "MA20", "operator": ">"},
        )
        rule2 = StrategyRule(
            rule_id="r2",
            rule_type="entry",
            condition={"indicator": "MA20", "operator": "<"},
        )
        assert _are_rules_contradictory(rule1, rule2) == True

    def test_same_rule(self):
        """相同规则不矛盾。"""
        rule1 = StrategyRule(
            rule_id="r1",
            rule_type="entry",
            condition={"indicator": "MA20", "operator": ">"},
        )
        rule2 = StrategyRule(
            rule_id="r2",
            rule_type="entry",
            condition={"indicator": "MA20", "operator": ">"},
        )
        assert _are_rules_contradictory(rule1, rule2) == False


class TestDataStructures:
    """数据结构测试。"""

    def test_strategy_rule(self):
        """StrategyRule 结构。"""
        rule = StrategyRule(
            rule_id="r1",
            rule_type="entry",
            instrument_focus="stock",
            confidence=0.8,
        )
        assert rule.rule_id == "r1"
        assert rule.confidence == 0.8

    def test_trade_record(self):
        """TradeRecord 结构。"""
        trade = TradeRecord(
            trade_id="t1",
            symbol="000001.SZ",
            side="buy",
            price=10.0,
            quantity=100.0,
            executed_at=datetime.now(),
        )
        assert trade.symbol == "000001.SZ"
        assert trade.side == "buy"

    def test_match_result(self):
        """MatchResult 结构。"""
        result = MatchResult(
            rule_id="r1",
            trade_id="t1",
            matched=True,
            score=0.8,
        )
        assert result.matched == True
        assert result.score == 0.8

    def test_conflict_detection_result(self):
        """ConflictDetectionResult 结构。"""
        result = ConflictDetectionResult(
            conflict_type=ConflictType.RULE_CONTRADICTION,
            severity="major",
            message="Test conflict",
        )
        assert result.conflict_type == ConflictType.RULE_CONTRADICTION
        assert result.severity == "major"


class TestIntegration:
    """集成测试。"""

    def test_full_alignment_report(self):
        """完整对齐报告。"""
        from src.alignment.types import BehaviorProfile

        # 创建测试数据
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
        profile = BehaviorProfile(
            trader_id="trader1",
            label_distribution={"chase_rally": 0.5, "bottom_fish": 0.5},
            win_rate=0.6,
        )

        # 执行分析
        rule_scores = [rule_match_score(r, trades) for r in rules]
        fit_score = behavior_fit_score(profile, rules)
        conflicts = detect_conflicts(rules, trades)
        confidence = confidence_scoring(rule_scores, fit_score)

        # 验证
        assert len(rule_scores) == 2
        assert 0 <= fit_score.fit_score <= 1.0
        assert isinstance(conflicts, ConflictDetection)
        assert 0 <= confidence.overall_score <= 1.0
