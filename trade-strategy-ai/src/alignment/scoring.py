"""
对齐评分算法 — P3-001, P3-002, P3-004, P3-017。

核心算法：
  - P3-001: rule_match_score() — 规则匹配评分
  - P3-002: behavior_fit_score() — 行为适配度评分
  - P3-004: confidence_scoring() — 综合可信度评分
  - P3-017: detailed_confidence_scoring() — 多维度综合评分
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.alignment.types import (
    BehaviorFitScore,
    BehaviorProfile,
    ConfidenceScore,
    MatchResult,
    RuleMatchScore,
    StrategyRule,
    TradeRecord,
)


# ---------------------------------------------------------------------------
# P3-001: 规则匹配评分算法
# ---------------------------------------------------------------------------

def rule_match_score(
    rule: StrategyRule,
    trades: list[TradeRecord],
    **kwargs,
) -> RuleMatchScore:
    """计算规则匹配评分。

    评估一条策略规则与实际交易的匹配程度。

    算法：
      1. 对每笔交易，判断是否符合规则的交易条件
      2. 计算匹配率 = 匹配交易数 / 总交易数
      3. 计算平均匹配分数（考虑置信度）

    Args:
        rule: 策略规则
        trades: 交易记录列表

    Returns:
        RuleMatchScore
    """
    if not trades:
        return RuleMatchScore(rule_id=rule.rule_id)

    match_results: list[MatchResult] = []
    matched_count = 0

    for trade in trades:
        result = _evaluate_rule_trade_match(rule, trade)
        match_results.append(result)
        if result.matched:
            matched_count += 1

    match_rate = matched_count / len(trades)
    avg_score = (
        sum(r.score for r in match_results) / len(match_results)
        if match_results else 0.0
    )

    return RuleMatchScore(
        rule_id=rule.rule_id,
        matched_trades=matched_count,
        total_trades=len(trades),
        match_rate=match_rate,
        avg_score=avg_score,
        match_results=match_results,
    )


def _evaluate_rule_trade_match(
    rule: StrategyRule,
    trade: TradeRecord,
) -> MatchResult:
    """评估单笔交易是否匹配规则。

    基于规则的 condition 和 action 进行匹配判断。

    Args:
        rule: 策略规则
        trade: 交易记录

    Returns:
        MatchResult
    """
    result = MatchResult(
        rule_id=rule.rule_id,
        trade_id=trade.trade_id,
        matched=False,
        score=0.0,
        reason="",
    )

    # 1. 标的类型匹配
    if rule.instrument_focus != "mixed":
        if not _check_instrument_match(rule.instrument_focus, trade.symbol):
            result.reason = f"Symbol {trade.symbol} doesn't match instrument focus"
            return result

    # 2. 规则类型与交易方向匹配
    if not _check_rule_type_direction_match(rule.rule_type, trade.side):
        result.reason = f"Rule type {rule.rule_type} doesn't match trade side {trade.side}"
        return result

    # 3. 条件匹配（基于 condition dict）
    condition_score = _evaluate_condition(rule.condition, trade)
    if condition_score < 0.3:
        result.reason = f"Condition score {condition_score:.2f} below threshold"
        return result

    # 4. 综合评分
    result.matched = True
    result.score = condition_score * rule.confidence
    result.reason = "Matched"

    return result


def _check_instrument_match(focus: str, symbol: str) -> bool:
    """检查标的类型是否匹配。"""
    if focus == "mixed":
        return True

    # 简化：区分股票和 ETF
    # 中国市场：510xxx.SH/SZ 是 ETF，000xxx.SZ 是股票，600xxx.SH 是股票
    is_etf = symbol.startswith("510") or symbol.startswith("159") or "ETF" in symbol.upper()
    is_stock = (symbol.startswith("000") or symbol.startswith("600") or symbol.startswith("300")) and ".SZ" in symbol or ".SH" in symbol
    is_cb = symbol.startswith("CB")

    if focus == "stock":
        return is_stock and not is_etf
    elif focus == "etf":
        return is_etf
    elif focus == "cb":
        return is_cb

    return True


def _check_rule_type_direction_match(rule_type: str, side: str) -> bool:
    """检查规则类型与交易方向是否匹配。"""
    # entry 规则通常对应 buy
    if rule_type == "entry" and side == "buy":
        return True
    # exit 规则通常对应 sell
    if rule_type == "exit" and side == "sell":
        return True
    # filter/sizing/risk 规则不直接匹配方向
    if rule_type in ("filter", "sizing", "risk"):
        return True
    return True  # 默认通过


def _evaluate_condition(condition: dict[str, Any], trade: TradeRecord) -> float:
    """评估条件匹配程度。

    Args:
        condition: 条件表达式字典
        trade: 交易记录

    Returns:
        匹配分数（0-1）
    """
    if not condition:
        return 0.5  # 无条件时返回中等分数

    score = 0.5
    matched_conditions = 0
    total_conditions = 0

    # 常见条件类型
    for key, value in condition.items():
        total_conditions += 1
        if _evaluate_single_condition(key, value, trade):
            matched_conditions += 1

    if total_conditions > 0:
        score = matched_conditions / total_conditions

    return score


def _evaluate_single_condition(key: str, value: Any, trade: TradeRecord) -> bool:
    """评估单个条件。"""
    # 这里实现简化的条件评估逻辑
    # 实际实现应该解析 condition 表达式的操作符和字段

    # 简化：如果 condition 为空，返回 True
    if not value:
        return True

    # 基础条件评估
    if key == "symbol":
        return str(value) == trade.symbol

    # 更多条件类型可扩展
    return True


# ---------------------------------------------------------------------------
# P3-002: 行为适配度评分算法
# ---------------------------------------------------------------------------

def behavior_fit_score(
    profile: BehaviorProfile,
    rules: list[StrategyRule],
    **kwargs,
) -> BehaviorFitScore:
    """计算行为适配度评分。

    评估交易者实际行为与其声称策略的匹配程度。

    算法：
      1. 分析规则中的行为特征（持仓时长、交易频率、风格标签）
      2. 与实际行为画像对比
      3. 计算各维度匹配分数
      4. 综合得到适配度

    Args:
        profile: 交易者行为画像
        rules: 策略规则列表

    Returns:
        BehaviorFitScore
    """
    if not rules or not profile:
        return BehaviorFitScore(trader_id=profile.trader_id if profile else "")

    dimension_scores: dict[str, float] = {}
    gaps: list[str] = []

    # 1. 风格标签匹配度
    style_score = _compute_style_fit(profile, rules)
    dimension_scores["style_fit"] = style_score

    # 2. 持仓时长匹配度
    hold_score = _compute_hold_time_fit(profile, rules)
    dimension_scores["hold_time_fit"] = hold_score
    if hold_score < 0.5:
        gaps.append(f"Hold time mismatch: profile={profile.avg_hold_minutes}min")

    # 3. 交易频率匹配度
    freq_score = _compute_frequency_fit(profile, rules)
    dimension_scores["frequency_fit"] = freq_score

    # 4. 胜率/期望值匹配度
    stats_score = _compute_stats_fit(profile, rules)
    dimension_scores["stats_fit"] = stats_score
    if stats_score < 0.5:
        gaps.append(f"Stats mismatch: win_rate={profile.win_rate:.2f}, ev={profile.expected_value:.4f}")

    # 综合适配度（加权平均）
    weights = {
        "style_fit": 0.3,
        "hold_time_fit": 0.25,
        "frequency_fit": 0.2,
        "stats_fit": 0.25,
    }
    fit_score = sum(
        dimension_scores.get(dim, 0.0) * weight
        for dim, weight in weights.items()
    )

    return BehaviorFitScore(
        trader_id=profile.trader_id,
        fit_score=fit_score,
        dimension_scores=dimension_scores,
        gaps=gaps,
    )


def _compute_style_fit(profile: BehaviorProfile, rules: list[StrategyRule]) -> float:
    """计算风格标签匹配度。"""
    if not profile.label_distribution:
        return 0.5

    # 从规则推断期望的风格分布
    expected_styles: dict[str, float] = {}
    for rule in rules:
        # 简化：从 rule_type 推断风格
        if rule.rule_type == "entry":
            expected_styles["chase_rally"] = expected_styles.get("chase_rally", 0) + 0.3
        elif rule.rule_type == "exit":
            expected_styles["profit_taking"] = expected_styles.get("profit_taking", 0) + 0.3

    if not expected_styles:
        return 0.5

    # 计算分布相似度（简化余弦相似度）
    return _cosine_similarity(profile.label_distribution, expected_styles)


def _compute_hold_time_fit(profile: BehaviorProfile, rules: list[StrategyRule]) -> float:
    """计算持仓时长匹配度。"""
    if profile.avg_hold_minutes is None:
        return 0.5

    # 从规则推断期望的持仓时长
    expected_hold = 60.0  # 默认 1 小时

    for rule in rules:
        if rule.rule_type == "entry" and "holding_period" in rule.action:
            expected_hold = float(rule.action["holding_period"])

    # 计算匹配度
    if expected_hold == 0:
        return 0.5

    ratio = min(profile.avg_hold_minutes, expected_hold) / max(profile.avg_hold_minutes, expected_hold)
    return ratio


def _compute_frequency_fit(profile: BehaviorProfile, rules: list[StrategyRule]) -> float:
    """计算交易频率匹配度。"""
    # 简化：使用胜率作为频率代理
    if profile.win_rate == 0:
        return 0.5

    # 期望频率基于规则复杂度
    expected_freq = min(len(rules) * 0.1, 1.0)
    actual_freq = profile.win_rate  # 简化

    return min(actual_freq, expected_freq) / max(actual_freq, expected_freq) if expected_freq > 0 else 0.5


def _compute_stats_fit(profile: BehaviorProfile, rules: list[StrategyRule]) -> float:
    """计算统计指标匹配度。"""
    # 综合胜率和期望值
    win_rate_score = profile.win_rate if profile.win_rate > 0 else 0.3

    # 期望值分数（假设 >0 表示盈利策略）
    ev_score = 1.0 if profile.expected_value > 0 else 0.5

    return (win_rate_score + ev_score) / 2.0


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """计算两个分布的余弦相似度。"""
    # 获取所有键
    all_keys = set(a.keys()) | set(b.keys())

    # 构建向量
    vec_a = np.array([a.get(k, 0.0) for k in all_keys])
    vec_b = np.array([b.get(k, 0.0) for k in all_keys])

    # 计算余弦相似度
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


# ---------------------------------------------------------------------------
# P3-017: 多维度综合评分（增强版）
# ---------------------------------------------------------------------------

# 默认评分维度及权重
DEFAULT_SCORING_WEIGHTS = {
    "rule_match": 0.30,       # 规则匹配度权重
    "rule_accuracy": 0.15,     # 规则准确度权重
    "behavior_fit": 0.25,      # 行为适配度权重
    "conflict_penalty": 0.20,  # 冲突扣分权重
    "coverage": 0.10,          # 覆盖率权重
}

# 评分等级阈值
SCORE_GRADES = [
    (0.9, "A+", "优秀"),
    (0.8, "A", "良好"),
    (0.7, "B+", "较好"),
    (0.6, "B", "一般"),
    (0.5, "C", "较差"),
    (0.0, "D", "不合格"),
]


@dataclass
class ScoringDimension:
    """评分维度。"""
    name: str
    score: float
    weight: float
    description: str = ""


@dataclass
class DetailedConfidenceScore:
    """详细综合可信度评分（P3-017）。"""
    trader_id: str
    # 综合评分（0-1）
    overall_score: float = 0.0
    # 评分等级
    grade: str = "D"
    grade_label: str = "不合格"
    # 各维度详情
    dimensions: list[ScoringDimension] = field(default_factory=list)
    # 详细评分明细
    score_breakdown: dict[str, float] = field(default_factory=dict)
    # 综合评分组成
    component_scores: dict[str, float] = field(default_factory=dict)
    # 权重配置
    weights_used: dict[str, float] = field(default_factory=dict)


def confidence_scoring(
    rule_match_scores: list[RuleMatchScore],
    behavior_fit: BehaviorFitScore,
    conflict_penalty: float = 0.0,
    weights: dict[str, float] | None = None,
    **kwargs,
) -> ConfidenceScore:
    """计算综合可信度评分。

    综合规则匹配度、行为适配度和冲突扣分，计算最终可信度评分。

    算法：
      1. 计算平均规则匹配率
      2. 获取行为适配度
      3. 应用冲突扣分
      4. 加权综合得到最终分数

    Args:
        rule_match_scores: 规则匹配评分列表
        behavior_fit: 行为适配度评分
        conflict_penalty: 冲突扣分（0-1）
        weights: 各维度权重配置

    Returns:
        ConfidenceScore
    """
    if weights is None:
        weights = {
            "rule_match": 0.4,
            "behavior_fit": 0.4,
            "conflict_penalty": 0.2,
        }

    # 1. 平均规则匹配率
    rule_match_score_val = 0.0
    if rule_match_scores:
        total_rate = sum(s.match_rate for s in rule_match_scores)
        rule_match_score_val = total_rate / len(rule_match_scores)

    # 2. 行为适配度（已归一化到 0-1）
    behavior_fit_score_val = behavior_fit.fit_score if behavior_fit else 0.5

    # 3. 冲突扣分（从 1 减去扣分比例）
    conflict_score_val = max(0.0, 1.0 - conflict_penalty)

    # 4. 加权综合
    overall_score = (
        weights["rule_match"] * rule_match_score_val
        + weights["behavior_fit"] * behavior_fit_score_val
        + weights["conflict_penalty"] * conflict_score_val
    )

    # 限制到 [0, 1]
    overall_score = max(0.0, min(1.0, overall_score))

    return ConfidenceScore(
        trader_id=behavior_fit.trader_id if behavior_fit else "",
        overall_score=overall_score,
        rule_match_score=rule_match_score_val,
        behavior_fit_score=behavior_fit_score_val,
        conflict_penalty=conflict_penalty,
        score_breakdown={
            "rule_match_score": rule_match_score_val,
            "behavior_fit_score": behavior_fit_score_val,
            "conflict_score": conflict_score_val,
            "overall_score": overall_score,
        },
    )


def detailed_confidence_scoring(
    trader_id: str,
    rule_match_scores: list[RuleMatchScore] | None = None,
    rule_accuracy_scores: dict[str, float] | None = None,
    behavior_fit: BehaviorFitScore | None = None,
    coverage_score: float | None = None,
    conflict_penalty: float = 0.0,
    weights: dict[str, float] | None = None,
    **kwargs,
) -> DetailedConfidenceScore:
    """计算详细多维度综合可信度评分（P3-017）。

    支持多维度评分：
      - rule_match: 规则匹配度
      - rule_accuracy: 规则准确度
      - behavior_fit: 行为适配度
      - coverage: 覆盖率
      - conflict_penalty: 冲突扣分

    Args:
        trader_id: 交易员 ID
        rule_match_scores: 规则匹配评分列表
        rule_accuracy_scores: 规则准确度字典（rule_id -> accuracy）
        behavior_fit: 行为适配度评分
        coverage_score: 覆盖率（可选，0-1）
        conflict_penalty: 冲突扣分（0-1）
        weights: 各维度权重配置

    Returns:
        DetailedConfidenceScore
    """
    if weights is None:
        weights = DEFAULT_SCORING_WEIGHTS.copy()

    # 验证权重总和
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 0.01:
        # 归一化权重
        weights = {k: v / weight_sum for k, v in weights.items()}

    dimensions: list[ScoringDimension] = []
    component_scores: dict[str, float] = {}

    # 1. 规则匹配度
    rule_match_val = 0.0
    if rule_match_scores:
        total_rate = sum(s.match_rate for s in rule_match_scores)
        rule_match_val = total_rate / len(rule_match_scores)
    component_scores["rule_match"] = rule_match_val
    dimensions.append(ScoringDimension(
        name="rule_match",
        score=rule_match_val,
        weight=weights.get("rule_match", 0.3),
        description="规则匹配度：规则与实际交易的匹配比例",
    ))

    # 2. 规则准确度
    rule_accuracy_val = 0.0
    if rule_accuracy_scores:
        accuracies = list(rule_accuracy_scores.values())
        rule_accuracy_val = sum(accuracies) / len(accuracies) if accuracies else 0.0
    component_scores["rule_accuracy"] = rule_accuracy_val
    dimensions.append(ScoringDimension(
        name="rule_accuracy",
        score=rule_accuracy_val,
        weight=weights.get("rule_accuracy", 0.15),
        description="规则准确度：规则预测与实际交易的一致性",
    ))

    # 3. 行为适配度
    behavior_fit_val = behavior_fit.fit_score if behavior_fit else 0.5
    component_scores["behavior_fit"] = behavior_fit_val
    dimensions.append(ScoringDimension(
        name="behavior_fit",
        score=behavior_fit_val,
        weight=weights.get("behavior_fit", 0.25),
        description="行为适配度：实际行为与声称策略的匹配程度",
    ))

    # 4. 覆盖率
    coverage_val = coverage_score if coverage_score is not None else 0.5
    component_scores["coverage"] = coverage_val
    dimensions.append(ScoringDimension(
        name="coverage",
        score=coverage_val,
        weight=weights.get("coverage", 0.1),
        description="覆盖率：被规则覆盖的交易比例",
    ))

    # 5. 冲突扣分（转换为正向分数）
    conflict_score_val = max(0.0, 1.0 - conflict_penalty)
    component_scores["conflict_penalty"] = conflict_penalty
    component_scores["conflict_score"] = conflict_score_val
    dimensions.append(ScoringDimension(
        name="conflict_penalty",
        score=conflict_score_val,
        weight=weights.get("conflict_penalty", 0.2),
        description="冲突得分：基于冲突检测结果的扣分调整",
    ))

    # 6. 计算加权综合分数
    overall_score = 0.0
    for dim in dimensions:
        overall_score += dim.score * dim.weight

    # 限制到 [0, 1]
    overall_score = max(0.0, min(1.0, overall_score))

    # 7. 确定评分等级
    grade, grade_label = _get_score_grade(overall_score)

    return DetailedConfidenceScore(
        trader_id=trader_id,
        overall_score=overall_score,
        grade=grade,
        grade_label=grade_label,
        dimensions=dimensions,
        score_breakdown={
            dim.name: dim.score for dim in dimensions
        },
        component_scores=component_scores,
        weights_used=weights.copy(),
    )


def _get_score_grade(score: float) -> tuple[str, str]:
    """根据分数获取评分等级。

    Args:
        score: 综合评分（0-1）

    Returns:
        (等级, 等级标签) 元组
    """
    for threshold, grade, label in SCORE_GRADES:
        if score >= threshold:
            return grade, label
    return "D", "不合格"


def validate_weights(weights: dict[str, float]) -> bool:
    """验证权重配置是否有效。

    Args:
        weights: 权重配置

    Returns:
        是否有效
    """
    if not weights:
        return False

    # 检查权重总和
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 0.01:
        return False

    # 检查权重是否为正
    if any(v < 0 for v in weights.values()):
        return False

    return True


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """归一化权重配置。

    Args:
        weights: 原始权重配置

    Returns:
        归一化后的权重配置
    """
    weight_sum = sum(weights.values())
    if weight_sum == 0:
        return weights
    return {k: v / weight_sum for k, v in weights.items()}
