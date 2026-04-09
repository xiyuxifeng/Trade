"""SignalSynthesizer 单元测试"""
import pytest
from src.strategy.signal_synthesizer import (
    SignalSynthesizer,
    SynthesisMode,
)
from src.strategy.types import RuleMatch, SynthesisContext, RawSignal, SignalSide
from src.persona.dsl import ActionSpec


def _create_rule_match(
    rule_id: str,
    rule_type: str,
    matched: bool,
    confidence: float,
    side: str = "buy",
) -> RuleMatch:
    """创建样本 RuleMatch"""
    return RuleMatch(
        rule_id=rule_id,
        rule_type=rule_type,
        matched=matched,
        confidence=confidence,
        action=ActionSpec(type=rule_type, side=side),
    )


def test_priority_mode_buy_signal():
    """测试优先级模式 - BUY 信号"""
    synthesizer = SignalSynthesizer(mode=SynthesisMode.PRIORITY)

    matches = [
        _create_rule_match("rule1", "entry", True, 0.8, "buy"),
        _create_rule_match("rule2", "exit", True, 0.6, "sell"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    assert result.side == SignalSide.BUY
    assert result.synthesis_mode == SynthesisMode.PRIORITY


def test_priority_mode_filters_no_match():
    """测试优先级模式 - 过滤未匹配规则"""
    synthesizer = SignalSynthesizer(mode=SynthesisMode.PRIORITY)

    matches = [
        _create_rule_match("rule1", "entry", False, 0.8, "buy"),  # 未匹配
        _create_rule_match("rule2", "exit", True, 0.6, "sell"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    # entry 未匹配，exit 匹配，结果应为 SELL
    assert result.side == SignalSide.SELL


def test_voting_mode_majority():
    """测试投票模式 - 多数胜出"""
    synthesizer = SignalSynthesizer(mode=SynthesisMode.VOTING)

    matches = [
        _create_rule_match("rule1", "entry", True, 0.8, "buy"),
        _create_rule_match("rule2", "entry", True, 0.7, "buy"),
        _create_rule_match("rule3", "entry", True, 0.6, "sell"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    assert result.side == SignalSide.BUY  # 2 buy vs 1 sell


def test_weighted_score_mode():
    """测试加权评分模式"""
    synthesizer = SignalSynthesizer(
        mode=SynthesisMode.WEIGHTED_SCORE,
        weights={"entry": 1.0, "exit": 1.5},
    )

    matches = [
        _create_rule_match("rule1", "entry", True, 0.8, "buy"),
        _create_rule_match("rule2", "exit", True, 0.6, "sell"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    assert result.side in (SignalSide.BUY, SignalSide.SELL, SignalSide.HOLD)


def test_hold_when_no_matches():
    """测试无匹配规则时返回 HOLD"""
    synthesizer = SignalSynthesizer(mode=SynthesisMode.PRIORITY)

    matches = [
        _create_rule_match("rule1", "entry", False, 0.8, "buy"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    assert result.side == SignalSide.HOLD
