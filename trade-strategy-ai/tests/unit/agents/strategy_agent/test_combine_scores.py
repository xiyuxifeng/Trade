import pytest
from src.agents.strategy_agent.skills.combine_scores import combine_scores
from src.strategy.types import SynthesisMode, RuleMatch


@pytest.mark.asyncio
async def test_combine_scores_success():
    """正常调用返回包含 side, confidence, triggered_rules"""
    rule_matches = []  # 简化测试
    result = await combine_scores(rule_matches, SynthesisMode.PRIORITY)
    assert "side" in result
    assert "confidence" in result
    assert "triggered_rules" in result


@pytest.mark.asyncio
async def test_combine_scores_error_returns_hold():
    """异常时返回 HOLD"""
    result = await combine_scores([], SynthesisMode.PRIORITY)
    assert result["side"].value == "HOLD"