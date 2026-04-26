"""NTL-S6-002: 回测执行器骨架

职责：
- 重放历史策略版本中的 recommendations
- 检测 rules_snapshot 兼容性缺口
- 不调用实时 provider，只读历史快照
"""

from __future__ import annotations

from typing import Any

from src.strategy_library.schemas import StrategyVersion


def replay_candidates(
    version: StrategyVersion, market_context: dict[str, Any]
) -> list[dict[str, Any]]:
    """从策略版本重放出候选决策列表。

    将 StrategyVersion.recommendations 转换为回测内部候选对象，
    不做信号生成或修改，只做格式转换。

    Args:
        version: 策略版本
        market_context: 市场上下文快照（由 SnapshotLoader 加载）

    Returns:
        候选决策列表，每项包含 symbol、decision、confidence、
        entry_price、target_price、stop_loss_price
    """
    return [
        {
            "symbol": rec.symbol,
            "decision": rec.decision,
            "confidence": rec.confidence,
            "entry_price": rec.entry_price,
            "target_price": rec.target_price,
            "stop_loss_price": rec.stop_loss_price,
        }
        for rec in version.recommendations
    ]


def classify_rules_snapshot_gap(version: StrategyVersion) -> str | None:
    """检测 rules_snapshot 是否存在兼容性缺口。

    缺口类型：
    - "missing_or_legacy_gap": rules_snapshot 为空或 None（历史版本可能丢失）
    - None: rules_snapshot 存在，无缺口

    Args:
        version: 策略版本

    Returns:
        缺口类型字符串或 None（无缺口）
    """
    if version.rules_snapshot:
        return None
    return "missing_or_legacy_gap"
