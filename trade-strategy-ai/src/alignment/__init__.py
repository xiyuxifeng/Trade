"""
对齐分析框架 — P3-001~P3-012。

核心模块：
  - P3-001: rule_match_score() — 规则匹配评分
  - P3-002: behavior_fit_score() — 行为适配度评分
  - P3-003: conflict_detection() — 冲突检测
  - P3-004: confidence_scoring() — 综合可信度评分
  - P3-005: detect_unmatched_trades() — 规则漏配检测
  - P3-006: compute_rule_coverage() — 规则覆盖率
  - P3-007: compute_rule_accuracy() — 规则准确度
  - P3-008: detect_rule_conflicts() — 规则冲突检测
  - P3-009: cosine_similarity() — 特征向量相似度
  - P3-010: kl_divergence() — 概率分布拟合度
  - P3-011: dtw_distance() — 时间序列相似度
  - P3-012: compute_stats_match_score() — 统计量匹配度
"""

from __future__ import annotations

from src.alignment.types import (
    AlignmentReport,
    BehaviorProfile,
    ConflictDetectionResult,
    ConflictType,
    MatchResult,
    RuleMatchScore,
    BehaviorFitScore,
    ConflictDetection,
    ConfidenceScore,
    TradeRecord,
    StrategyRule,
)

from src.alignment.scoring import (
    rule_match_score,
    behavior_fit_score,
    confidence_scoring,
)

from src.alignment.conflict import detect_conflicts

from src.alignment.rule_matching import (
    RuleCoverageResult,
    RuleAccuracyResult,
    RuleConflictResult,
    RuleMissDetectionResult,
    UnmatchedTrade,
    RuleMatchingReport,
    detect_unmatched_trades,
    compute_rule_coverage,
    compute_rule_accuracy,
    detect_rule_conflicts,
    generate_rule_matching_report,
)

from src.alignment.behavior_fit import (
    # P3-009: 特征向量相似度
    cosine_similarity,
    euclidean_distance,
    manhattan_distance,
    chebyshev_distance,
    cosine_similarity_dict,
    # P3-010: 概率分布拟合度
    kl_divergence,
    js_divergence,
    wasserstein_distance_1d,
    kolmogorov_smirnov_statistic,
    # P3-011: 时间序列相似度
    dtw_distance,
    cross_correlation,
    pearson_correlation,
    similarity_from_distance,
    # P3-012: 统计量匹配度
    StatsMatchScore,
    compute_win_rate_score,
    compute_expected_value_score,
    compute_stats_match_score,
)

__all__ = [
    # Types
    "AlignmentReport",
    "BehaviorProfile",
    "ConflictDetectionResult",
    "ConflictType",
    "MatchResult",
    "RuleMatchScore",
    "BehaviorFitScore",
    "ConflictDetection",
    "ConfidenceScore",
    "TradeRecord",
    "StrategyRule",
    # P3-005~008 Types
    "RuleCoverageResult",
    "RuleAccuracyResult",
    "RuleConflictResult",
    "RuleMissDetectionResult",
    "UnmatchedTrade",
    "RuleMatchingReport",
    # P3-009~012 Types
    "StatsMatchScore",
    # Functions
    "rule_match_score",
    "behavior_fit_score",
    "confidence_scoring",
    "detect_conflicts",
    # P3-005~008 Functions
    "detect_unmatched_trades",
    "compute_rule_coverage",
    "compute_rule_accuracy",
    "detect_rule_conflicts",
    "generate_rule_matching_report",
    # P3-009 Functions
    "cosine_similarity",
    "euclidean_distance",
    "manhattan_distance",
    "chebyshev_distance",
    "cosine_similarity_dict",
    # P3-010 Functions
    "kl_divergence",
    "js_divergence",
    "wasserstein_distance_1d",
    "kolmogorov_smirnov_statistic",
    # P3-011 Functions
    "dtw_distance",
    "cross_correlation",
    "pearson_correlation",
    "similarity_from_distance",
    # P3-012 Functions
    "compute_win_rate_score",
    "compute_expected_value_score",
    "compute_stats_match_score",
]
