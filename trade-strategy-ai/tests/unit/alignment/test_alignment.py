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


# ---------------------------------------------------------------------------
# P3-013~P3-016: 冲突检测增强测试
# ---------------------------------------------------------------------------

class TestConflictSeverityClassification:
    """P3-016: 冲突严重程度智能分类测试。"""

    def test_temporal_conflict_severity(self):
        """时序冲突严重程度分类。"""
        from src.alignment.conflict import _classify_conflict_severity

        # Critical: exit 时间早于 entry 时间
        evidence = {
            "entry_condition": {"time": "10:00"},
            "exit_condition": {"time": "09:00"},
            "time_conflict": True,
        }
        severity = _classify_conflict_severity(ConflictType.TEMPORAL_CONFLICT, evidence)
        assert severity == "critical"

    def test_rule_contradiction_severity(self):
        """规则矛盾严重程度分类。"""
        from src.alignment.conflict import _classify_conflict_severity

        # Critical: > 和 < 互为矛盾
        evidence = {
            "rule1_type": "entry",
            "rule2_type": "entry",
            "rule1_condition": {"indicator": "MA20", "operator": ">"},
            "rule2_condition": {"indicator": "MA20", "operator": "<"},
        }
        severity = _classify_conflict_severity(ConflictType.RULE_CONTRADICTION, evidence)
        assert severity == "critical"

    def test_behavior_deviation_severity(self):
        """行为偏离严重程度分类。"""
        from src.alignment.conflict import _classify_conflict_severity

        # Critical: 实际匹配率远低于预期
        evidence = {
            "actual_match_rate": 0.1,
            "expected_match_rate": 0.5,
        }
        severity = _classify_conflict_severity(ConflictType.BEHAVIOR_DEVIATION, evidence)
        assert severity == "critical"

    def test_parameter_mismatch_critical_params(self):
        """核心参数不一致严重程度。"""
        from src.alignment.conflict import _classify_conflict_severity

        # Major: 核心参数差异显著
        evidence = {
            "parameter": "stop_loss",
            "values": [5.0, 8.0],  # 差异 60%
            "is_risk_param": True,
        }
        severity = _classify_conflict_severity(ConflictType.PARAMETER_MISMATCH, evidence)
        assert severity == "major"

    def test_rule_overlap_severity(self):
        """规则重叠严重程度分类。"""
        from src.alignment.conflict import _classify_conflict_severity

        # Minor: 一般重叠
        evidence = {"overlap_score": 0.85}
        severity = _classify_conflict_severity(ConflictType.RULE_OVERLAP, evidence)
        assert severity == "minor"

        # Major: 完全重叠
        evidence = {"overlap_score": 0.98}
        severity = _classify_conflict_severity(ConflictType.RULE_OVERLAP, evidence)
        assert severity == "major"


class TestTemporalConflictDetection:
    """P3-013: 时序冲突检测增强测试。"""

    def test_time_order_conflict(self):
        """时间顺序冲突检测。"""
        from src.alignment.conflict import _check_entry_exit_temporal_conflict

        entry_rule = StrategyRule(
            rule_id="entry1",
            rule_type="entry",
            condition={"time": "10:00"},
        )
        exit_rule = StrategyRule(
            rule_id="exit1",
            rule_type="exit",
            condition={"time": "09:00"},
        )

        result = _check_entry_exit_temporal_conflict(entry_rule, exit_rule)
        assert result is not None
        assert result.conflict_type == ConflictType.TEMPORAL_CONFLICT
        assert result.severity == "critical"

    def test_holding_period_conflict(self):
        """持仓时长冲突检测。"""
        from src.alignment.conflict import _check_entry_exit_temporal_conflict

        entry_rule = StrategyRule(
            rule_id="entry1",
            rule_type="entry",
            condition={"holding_period": 60},
        )
        exit_rule = StrategyRule(
            rule_id="exit1",
            rule_type="exit",
            condition={"holding_period": 10},  # 太短
        )

        result = _check_entry_exit_temporal_conflict(entry_rule, exit_rule)
        assert result is not None
        assert result.severity == "critical"

    def test_no_temporal_conflict(self):
        """无时序冲突时返回 None。"""
        from src.alignment.conflict import _check_entry_exit_temporal_conflict

        entry_rule = StrategyRule(
            rule_id="entry1",
            rule_type="entry",
            condition={"time": "10:00", "holding_period": 60},
        )
        exit_rule = StrategyRule(
            rule_id="exit1",
            rule_type="exit",
            condition={"time": "14:00", "holding_period": 60},
        )

        result = _check_entry_exit_temporal_conflict(entry_rule, exit_rule)
        assert result is None

    def test_rule_internal_temporal_conflict(self):
        """单条规则内部时序冲突。"""
        from src.alignment.conflict import _check_rule_internal_temporal_conflict

        rule = StrategyRule(
            rule_id="rule1",
            rule_type="entry",
            condition={"time_window": {"start": "15:00", "end": "09:00"}},  # 开始晚于结束
        )

        result = _check_rule_internal_temporal_conflict(rule)
        assert result is not None
        assert result.conflict_type == ConflictType.TEMPORAL_CONFLICT


class TestParameterMismatchDetection:
    """P3-014: 参数冲突检测增强测试。"""

    def test_action_param_mismatch(self):
        """Action 参数不一致检测。"""
        from src.alignment.conflict import _check_action_param_consistency

        rules = [
            StrategyRule(
                rule_id="r1",
                rule_type="entry",
                action={"params": {"stop_loss": 5.0}},
            ),
            StrategyRule(
                rule_id="r2",
                rule_type="entry",
                action={"params": {"stop_loss": 8.0}},
            ),
        ]

        conflicts = _check_action_param_consistency(rules)
        assert len(conflicts) >= 1
        assert conflicts[0].conflict_type == ConflictType.PARAMETER_MISMATCH

    def test_condition_param_mismatch(self):
        """Condition 参数不一致检测。"""
        from src.alignment.conflict import _check_condition_param_consistency

        rules = [
            StrategyRule(
                rule_id="r1",
                rule_type="entry",
                condition={"threshold": 10.0},
            ),
            StrategyRule(
                rule_id="r2",
                rule_type="entry",
                condition={"threshold": 15.0},
            ),
        ]

        conflicts = _check_condition_param_consistency(rules)
        assert len(conflicts) >= 1
        assert conflicts[0].conflict_type == ConflictType.PARAMETER_MISMATCH

    def test_risk_param_mismatch(self):
        """核心风控参数不一致。"""
        from src.alignment.conflict import _detect_parameter_mismatches

        rules = [
            StrategyRule(
                rule_id="r1",
                rule_type="exit",
                action={"params": {"stop_loss": 5.0}},
            ),
            StrategyRule(
                rule_id="r2",
                rule_type="exit",
                action={"params": {"stop_loss": 10.0}},  # 差异 100%
            ),
        ]

        conflicts = _detect_parameter_mismatches(rules)
        assert len(conflicts) >= 1

        # 验证严重程度是 major 或 critical
        severities = [c.severity for c in conflicts]
        assert any(s in ("major", "critical") for s in severities)


class TestLogicalConflictDetection:
    """P3-015: 逻辑冲突检测增强测试。"""

    def test_threshold_proximity_conflict(self):
        """阈值过近冲突。"""
        from src.alignment.conflict import _check_rule_logical_conflict

        rule1 = StrategyRule(
            rule_id="r1",
            rule_type="entry",
            condition={"indicator": "MA20", "operator": ">", "threshold": 10.0},
        )
        rule2 = StrategyRule(
            rule_id="r2",
            rule_type="entry",
            condition={"indicator": "MA20", "operator": ">", "threshold": 10.3},  # 差异 3%
        )

        result = _check_rule_logical_conflict(rule1, rule2)
        assert result is not None
        assert result.conflict_type == ConflictType.RULE_CONTRADICTION

    def test_same_type_opposite_sides(self):
        """同类型规则方向互斥。"""
        from src.alignment.conflict import _check_rule_logical_conflict

        rule1 = StrategyRule(
            rule_id="r1",
            rule_type="entry",
            action={"side": "buy"},
        )
        rule2 = StrategyRule(
            rule_id="r2",
            rule_type="entry",
            action={"side": "sell"},
        )

        result = _check_rule_logical_conflict(rule1, rule2)
        assert result is not None
        assert result.conflict_type == ConflictType.RULE_CONTRADICTION
        assert result.severity == "critical"

    def test_boundary_operators_conflict(self):
        """边界操作符冲突 (>= vs <=)。"""
        from src.alignment.conflict import _check_rule_logical_conflict

        rule1 = StrategyRule(
            rule_id="r1",
            rule_type="entry",
            condition={"indicator": "MA20", "operator": ">="},
        )
        rule2 = StrategyRule(
            rule_id="r2",
            rule_type="entry",
            condition={"indicator": "MA20", "operator": "<="},
        )

        result = _check_rule_logical_conflict(rule1, rule2)
        assert result is not None
        assert result.severity == "critical"

    def test_no_logical_conflict(self):
        """无逻辑冲突时返回 None。"""
        from src.alignment.conflict import _check_rule_logical_conflict

        rule1 = StrategyRule(
            rule_id="r1",
            rule_type="entry",
            condition={"indicator": "MA20", "operator": ">", "threshold": 10.0},
        )
        rule2 = StrategyRule(
            rule_id="r2",
            rule_type="exit",
            condition={"indicator": "MA20", "operator": "<", "threshold": 8.0},
        )

        result = _check_rule_logical_conflict(rule1, rule2)
        assert result is None


class TestEnhancedDetectConflicts:
    """P3-013~P3-016 集成测试。"""

    def test_detect_conflicts_with_severity(self):
        """综合冲突检测并验证严重程度分类。"""
        rules = [
            StrategyRule(
                rule_id="r1",
                rule_type="entry",
                condition={"indicator": "MA20", "operator": ">", "threshold": 10.0},
            ),
            StrategyRule(
                rule_id="r2",
                rule_type="entry",
                condition={"indicator": "MA20", "operator": "<", "threshold": 10.0},
            ),
            StrategyRule(
                rule_id="r3",
                rule_type="exit",
                condition={"time": "09:00"},  # 与 r1 的 10:00 冲突
            ),
            StrategyRule(
                rule_id="r4",
                rule_type="exit",
                condition={"stop_loss": 5.0},
            ),
            StrategyRule(
                rule_id="r5",
                rule_type="exit",
                condition={"stop_loss": 10.0},  # 参数不一致
            ),
        ]

        conflicts = detect_conflicts(rules)

        # 验证严重程度分布
        severities = set(c.severity for c in conflicts.conflicts)
        assert "critical" in severities or "major" in severities

        # 验证冲突类型
        conflict_types = set(c.conflict_type.value for c in conflicts.conflicts)
        assert "temporal_conflict" in conflict_types or "rule_contradiction" in conflict_types
        assert "parameter_mismatch" in conflict_types

    def test_severity_classification_coverage(self):
        """验证所有冲突类型都有严重程度分类。"""
        from src.alignment.conflict import _classify_conflict_severity

        for conflict_type in ConflictType:
            evidence = {"test": True}
            severity = _classify_conflict_severity(conflict_type, evidence)
            assert severity in ("critical", "major", "minor"), f"Unknown severity: {severity}"


# ---------------------------------------------------------------------------
# P3-017~P3-021: 评分和报告测试
# ---------------------------------------------------------------------------

class TestDetailedConfidenceScoring:
    """P3-017: 多维度综合评分测试。"""

    def test_detailed_confidence_scoring(self):
        """详细综合评分测试。"""
        from src.alignment.scoring import detailed_confidence_scoring

        result = detailed_confidence_scoring(
            trader_id="trader1",
            rule_match_scores=[
                RuleMatchScore(rule_id="r1", match_rate=0.8),
                RuleMatchScore(rule_id="r2", match_rate=0.6),
            ],
            behavior_fit=BehaviorFitScore(trader_id="trader1", fit_score=0.7),
            conflict_penalty=0.1,
        )

        assert result.trader_id == "trader1"
        assert 0 <= result.overall_score <= 1.0
        assert result.grade in ("A+", "A", "B+", "B", "C", "D")
        assert len(result.dimensions) > 0

    def test_score_grades(self):
        """评分等级测试。"""
        from src.alignment.scoring import SCORE_GRADES, _get_score_grade

        assert _get_score_grade(0.95) == ("A+", "优秀")
        assert _get_score_grade(0.85) == ("A", "良好")
        assert _get_score_grade(0.4) == ("D", "不合格")

    def test_weight_validation(self):
        """权重验证测试。"""
        from src.alignment.scoring import validate_weights, normalize_weights

        # 有效权重
        valid_weights = {"rule_match": 0.4, "behavior_fit": 0.4, "conflict_penalty": 0.2}
        assert validate_weights(valid_weights) == True

        # 无效权重（负数）
        invalid_weights = {"rule_match": -0.1, "behavior_fit": 0.5, "conflict_penalty": 0.2}
        assert validate_weights(invalid_weights) == False

        # 归一化
        weights = {"a": 1.0, "b": 2.0}
        normalized = normalize_weights(weights)
        assert sum(normalized.values()) == pytest.approx(1.0)


class TestTextReportGeneration:
    """P3-018: 文本报告生成测试。"""

    def test_generate_text_report(self):
        """文本报告生成测试。"""
        from src.alignment.report_generator import generate_text_report

        rules = [
            StrategyRule(rule_id="r1", rule_type="entry", confidence=0.8),
            StrategyRule(rule_id="r2", rule_type="exit", confidence=0.7),
        ]

        report = generate_text_report(
            trader_id="trader1",
            rules=rules,
            include_suggestions=False,
        )

        assert "对齐分析报告" in report
        assert "trader1" in report
        assert "执行摘要" in report

    def test_generate_conflict_inventory(self):
        """冲突清单生成测试。"""
        from src.alignment.report_generator import generate_conflict_inventory

        conflicts = ConflictDetection(
            trader_id="trader1",
            total_conflicts=2,
            by_type={"rule_contradiction": 1, "rule_overlap": 1},
            by_severity={"critical": 1, "minor": 1},
            conflicts=[
                ConflictDetectionResult(
                    conflict_type=ConflictType.RULE_CONTRADICTION,
                    severity="critical",
                    message="Test conflict",
                    involved_rules=["r1", "r2"],
                ),
            ],
        )

        inventory = generate_conflict_inventory(conflicts)
        assert "冲突清单" in inventory
        assert "总计: 2" in inventory


class TestVisualization:
    """P3-019: 可视化报告测试。"""

    def test_generate_radar_chart_data(self):
        """雷达图数据生成测试。"""
        from src.alignment.visualizer import generate_radar_chart_data
        from src.alignment.scoring import DetailedConfidenceScore, ScoringDimension

        score = DetailedConfidenceScore(
            trader_id="trader1",
            overall_score=0.75,
            dimensions=[
                ScoringDimension(name="rule_match", score=0.8, weight=0.3),
                ScoringDimension(name="behavior_fit", score=0.7, weight=0.4),
            ],
        )

        chart = generate_radar_chart_data(score)
        assert chart.chart_type == "radar"
        assert "labels" in chart.data

    def test_generate_conflict_distribution_chart(self):
        """冲突分布图生成测试。"""
        from src.alignment.visualizer import generate_conflict_distribution_chart

        conflicts = ConflictDetection(
            trader_id="trader1",
            total_conflicts=3,
            by_type={"rule_contradiction": 2, "rule_overlap": 1},
            by_severity={"critical": 1, "major": 2},
            conflicts=[],
        )

        chart = generate_conflict_distribution_chart(conflicts)
        assert chart.chart_type == "multi"
        assert "by_type" in chart.data

    def test_generate_html_dashboard(self):
        """HTML 仪表板生成测试。"""
        from src.alignment.visualizer import generate_html_dashboard

        html = generate_html_dashboard(trader_id="trader1")
        assert "<!DOCTYPE html>" in html
        assert "对齐分析仪表板" in html


class TestOptimizationSuggestions:
    """P3-020: 优化建议生成测试。"""

    def test_generate_optimization_suggestions(self):
        """优化建议生成测试。"""
        from src.alignment.report_generator import generate_optimization_suggestions

        conflicts = ConflictDetection(
            trader_id="trader1",
            total_conflicts=1,
            by_type={"rule_contradiction": 1},
            by_severity={"critical": 1},
            conflicts=[
                ConflictDetectionResult(
                    conflict_type=ConflictType.RULE_CONTRADICTION,
                    severity="critical",
                    message="Rules contradict each other",
                    involved_rules=["r1", "r2"],
                ),
            ],
        )

        suggestions = generate_optimization_suggestions(conflicts)
        assert len(suggestions) > 0
        assert suggestions[0]["priority"] in ("high", "medium", "low")

    def test_suggestion_for_temporal_conflict(self):
        """时序冲突优化建议测试。"""
        from src.alignment.report_generator import _suggestion_for_temporal_conflict

        conflict = ConflictDetectionResult(
            conflict_type=ConflictType.TEMPORAL_CONFLICT,
            severity="critical",
            message="Temporal conflict",
            involved_rules=["entry1", "exit1"],
            evidence={
                "entry_condition": {"time": "10:00"},
                "exit_condition": {"time": "09:00"},
            },
        )

        suggestion = _suggestion_for_temporal_conflict(conflict, "critical")
        assert suggestion["priority"] == "high"
        assert "时序" in suggestion["title"] or "Temporal" in suggestion["title"]


class TestAlignmentCache:
    """P3-021: 缓存和版本管理测试。"""

    def test_compute_data_hash(self):
        """数据指纹计算测试。"""
        from src.alignment.cache import AlignmentCache
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AlignmentCache(cache_dir=tmpdir)
            hash1 = cache.compute_data_hash([{"rule_id": "r1"}], None)
            hash2 = cache.compute_data_hash([{"rule_id": "r1"}], None)
            hash3 = cache.compute_data_hash([{"rule_id": "r2"}], None)

            assert hash1 == hash2  # 相同数据应产生相同哈希
            assert hash1 != hash3  # 不同数据应产生不同哈希

    def test_cache_result(self):
        """缓存结果测试。"""
        from src.alignment.cache import AlignmentCache
        from src.alignment.scoring import DetailedConfidenceScore, ScoringDimension
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AlignmentCache(cache_dir=tmpdir)

            score = DetailedConfidenceScore(
                trader_id="trader1",
                overall_score=0.75,
                dimensions=[ScoringDimension(name="test", score=0.5, weight=1.0)],
            )

            version = cache.cache_result(
                trader_id="trader1",
                detailed_score=score,
            )

            assert version.trader_id == "trader1"
            assert version.version_id is not None

    def test_get_latest_version(self):
        """获取最新版本测试。"""
        from src.alignment.cache import AlignmentCache
        from src.alignment.scoring import DetailedConfidenceScore, ScoringDimension
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AlignmentCache(cache_dir=tmpdir)

            # 缓存多个版本
            for i in range(3):
                score = DetailedConfidenceScore(
                    trader_id="trader1",
                    overall_score=0.7 + i * 0.1,
                    dimensions=[ScoringDimension(name="test", score=0.5, weight=1.0)],
                )
                cache.cache_result(trader_id="trader1", detailed_score=score)

            latest = cache.get_latest_version("trader1")
            assert latest is not None
            assert latest.trader_id == "trader1"

    def test_cache_validity(self):
        """缓存有效性测试。"""
        from src.alignment.cache import AlignmentCache
        from src.alignment.scoring import DetailedConfidenceScore, ScoringDimension
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AlignmentCache(cache_dir=tmpdir)

            # 无缓存时应返回 False
            assert cache.is_cache_valid("trader1", "hash123") == False

            # 缓存结果
            hash_val = cache.compute_data_hash([{"rule_id": "r1"}], None)
            score = DetailedConfidenceScore(
                trader_id="trader1",
                overall_score=0.75,
                dimensions=[ScoringDimension(name="test", score=0.5, weight=1.0)],
            )
            cache.cache_result(trader_id="trader1", detailed_score=score)

            # 缓存后（无数据哈希对比），默认应返回 False（因为没传 current_data_hash）
            assert cache.is_cache_valid("trader1", "hash123", max_age_hours=24.0) == False
