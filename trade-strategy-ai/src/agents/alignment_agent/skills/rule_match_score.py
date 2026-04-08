"""
Alignment Skill: Rule Match Score.

包装 src.alignment.rule_match_score 函数为 agent skill 格式。
"""

from __future__ import annotations

from typing import Any

from src.alignment import RuleMatchScore, StrategyRule, TradeRecord, rule_match_score


async def compute_rule_match_score(
    rule: dict[str, Any] | StrategyRule,
    trades: list[dict[str, Any] | TradeRecord],
    **kwargs,
) -> dict[str, Any]:
    """计算单条规则的匹配评分。

    Args:
        rule: 规则（dict 或 StrategyRule）
        trades: 交易记录列表

    Returns:
        包含评分结果的字典
    """
    # 转换为 StrategyRule
    if isinstance(rule, dict):
        rule = StrategyRule(**rule)

    # 转换交易记录
    if trades and isinstance(trades[0], dict):
        trades = [TradeRecord(**t) for t in trades]

    result = rule_match_score(rule, trades)

    return {
        "rule_id": result.rule_id,
        "matched_trades": result.matched_trades,
        "total_trades": result.total_trades,
        "match_rate": result.match_rate,
        "avg_score": result.avg_score,
    }


async def compute_batch_rule_match_scores(
    rules: list[dict[str, Any] | StrategyRule],
    trades: list[dict[str, Any] | TradeRecord],
    **kwargs,
) -> list[dict[str, Any]]:
    """批量计算规则匹配评分。

    Args:
        rules: 规则列表
        trades: 交易记录列表

    Returns:
        评分结果列表
    """
    results = []
    for rule in rules:
        result = await compute_rule_match_score(rule, trades, **kwargs)
        results.append(result)
    return results
