"""
Alignment Skill: Behavior Fit Score.

包装 src.alignment.behavior_fit_score 函数为 agent skill 格式。
"""

from __future__ import annotations

from typing import Any

from src.alignment import BehaviorProfile, StrategyRule, behavior_fit_score


async def compute_behavior_fit_score(
    profile: dict[str, Any] | BehaviorProfile,
    rules: list[dict[str, Any] | StrategyRule],
    **kwargs,
) -> dict[str, Any]:
    """计算行为适配度评分。

    Args:
        profile: 交易者行为画像
        rules: 策略规则列表

    Returns:
        包含评分结果的字典
    """
    # 转换为类型
    if isinstance(profile, dict):
        profile = BehaviorProfile(**profile)

    if rules and isinstance(rules[0], dict):
        rules = [StrategyRule(**r) for r in rules]

    result = behavior_fit_score(profile, rules)

    return {
        "trader_id": result.trader_id,
        "fit_score": result.fit_score,
        "dimension_scores": result.dimension_scores,
        "gaps": result.gaps,
    }
