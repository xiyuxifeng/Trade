"""生成信号 Skill - 生成 RawSignal"""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any
from src.strategy.types import RawSignal, SignalSide, SignalContext, SynthesisMode, PriceSpec, PositionSize


def generate_signal(
    symbol: str,
    side: SignalSide,
    confidence: float,
    triggered_rules: list[str],
    synthesis_mode: SynthesisMode,
    context: dict[str, Any]
) -> RawSignal:
    """
    生成原始信号

    Args:
        symbol: 股票代码
        side: 信号方向
        confidence: 置信度
        triggered_rules: 触发的规则列表
        synthesis_mode: 合成模式
        context: 上下文（包含 features_snapshot, market_state 等）

    Returns:
        RawSignal
    """
    try:
        features_snapshot = context.get("features_snapshot", {})
        market_state = context.get("market_state", {})
        rules_snapshot = context.get("rules_snapshot", [])

        signal_context = SignalContext(
            features_snapshot=features_snapshot,
            market_state=market_state,
            rules_snapshot=rules_snapshot,
            timestamp=datetime.now(timezone.utc)
        )

        signal = RawSignal(
            signal_id=str(uuid4()),
            symbol=symbol,
            side=side,
            confidence=confidence,
            triggered_rules=triggered_rules,
            synthesis_mode=synthesis_mode,
            entry_price=None,
            position_size=None,
            timestamp=datetime.now(timezone.utc),
            metadata={},
        )
        return signal
    except Exception as e:
        # 降级：返回 HOLD 信号
        return RawSignal(
            signal_id=str(uuid4()),
            symbol=symbol,
            side=SignalSide.HOLD,
            confidence=0.0,
            triggered_rules=[],
            synthesis_mode=synthesis_mode,
            entry_price=None,
            position_size=None,
            timestamp=datetime.now(timezone.utc),
            metadata={},
        )