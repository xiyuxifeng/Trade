"""
Alignment Skill: Conflict Detection.

包装 src.alignment.conflict_detection 函数为 agent skill 格式。
"""

from __future__ import annotations

from typing import Any

from src.alignment import ConflictDetection, StrategyRule, TradeRecord, detect_conflicts


async def detect_conflicts_skill(
    rules: list[dict[str, Any] | StrategyRule],
    trades: list[dict[str, Any] | TradeRecord] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """检测规则和交易中的冲突。

    Args:
        rules: 策略规则列表
        trades: 交易记录列表（可选）

    Returns:
        包含冲突检测结果的字典
    """
    # 转换规则
    if rules and isinstance(rules[0], dict):
        rules = [StrategyRule(**r) for r in rules]

    # 转换交易
    if trades and isinstance(trades[0], dict):
        trades = [TradeRecord(**t) for t in trades]

    result = detect_conflicts(rules, trades)

    return {
        "trader_id": result.trader_id,
        "total_conflicts": result.total_conflicts,
        "by_type": result.by_type,
        "by_severity": result.by_severity,
        "conflicts": [
            {
                "conflict_type": c.conflict_type.value,
                "severity": c.severity,
                "message": c.message,
                "involved_rules": c.involved_rules,
                "evidence": c.evidence,
            }
            for c in result.conflicts
        ],
    }
