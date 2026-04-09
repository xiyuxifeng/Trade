"""组合分数 Skill - 调用 SignalSynthesizer"""
from typing import Any
from src.strategy.signal_synthesizer import SignalSynthesizer, SynthesisMode
from src.strategy.types import RuleMatch, SignalSide, SynthesisContext

# SignalSynthesizer 单例
_synthesizer = SignalSynthesizer()


async def combine_scores(
    rule_matches: list[RuleMatch],
    mode: SynthesisMode = SynthesisMode.PRIORITY,
) -> dict[str, Any]:
    """
    组合分数，生成信号方向和置信度

    Args:
        rule_matches: 匹配的规则列表
        mode: 合成模式

    Returns:
        {side, confidence, triggered_rules}
    """
    try:
        context = SynthesisContext(market_state={}, features={})
        result = _synthesizer.synthesize(rule_matches, context)
        return {
            "side": result.side,
            "confidence": result.confidence,
            "triggered_rules": result.triggered_rules,
        }
    except Exception as e:
        # 降级：返回 HOLD
        return {
            "side": SignalSide.HOLD,
            "confidence": 0.0,
            "triggered_rules": [],
        }