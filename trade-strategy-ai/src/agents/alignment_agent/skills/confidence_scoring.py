"""
Alignment Skill: Confidence Scoring.

包装 src.alignment.detailed_confidence_scoring 函数为 agent skill 格式。
"""

from __future__ import annotations

from typing import Any

from src.alignment import (
    DetailedConfidenceScore,
    detailed_confidence_scoring,
)


async def compute_confidence_score(
    trader_id: str,
    rule_match_scores: list[dict[str, Any]] | None = None,
    rule_accuracy_scores: dict[str, float] | None = None,
    behavior_fit_score: float | None = None,
    coverage_score: float | None = None,
    conflict_penalty: float = 0.0,
    weights: dict[str, float] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """计算综合可信度评分。

    Args:
        trader_id: 交易员 ID
        rule_match_scores: 规则匹配评分列表
        rule_accuracy_scores: 规则准确度字典
        behavior_fit_score: 行为适配度评分
        coverage_score: 覆盖率
        conflict_penalty: 冲突扣分（0-1）
        weights: 各维度权重配置

    Returns:
        包含评分结果的字典
    """
    # 转换为 BehaviorFitScore 类型（如果提供）
    behavior_fit = None
    if behavior_fit_score is not None:
        from src.alignment import BehaviorFitScore
        behavior_fit = BehaviorFitScore(
            trader_id=trader_id,
            fit_score=behavior_fit_score,
        )

    result = detailed_confidence_scoring(
        trader_id=trader_id,
        rule_match_scores=None,  # 简化处理
        rule_accuracy_scores=rule_accuracy_scores,
        behavior_fit=behavior_fit,
        coverage_score=coverage_score,
        conflict_penalty=conflict_penalty,
        weights=weights,
    )

    return {
        "trader_id": result.trader_id,
        "overall_score": result.overall_score,
        "grade": result.grade,
        "grade_label": result.grade_label,
        "dimensions": [
            {
                "name": d.name,
                "score": d.score,
                "weight": d.weight,
                "description": d.description,
            }
            for d in result.dimensions
        ],
        "score_breakdown": result.score_breakdown,
    }
