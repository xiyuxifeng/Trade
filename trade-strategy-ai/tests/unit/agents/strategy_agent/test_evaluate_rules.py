import pytest
from src.agents.strategy_agent.skills.evaluate_rules import evaluate_rules

@pytest.mark.asyncio
async def test_evaluate_rules_success():
    """测试 evaluate_rules 基本功能"""
    features = {"rsi": 30.0, "macd": 1.5}
    rules = [
        {
            "rule_id": "rsi_oversold",
            "condition": {"op": "cmp", "field": "rsi", "cmp": "lt", "value": 40},
            "action": {"type": "enter", "side": "buy"}
        }
    ]
    result = await evaluate_rules(features, rules)
    assert isinstance(result, list)
    # RSI=30 < 40，应该匹配
    assert len(result) == 1
    assert result[0].rule_id == "rsi_oversold"
    assert result[0].matched is True

@pytest.mark.asyncio
async def test_evaluate_rules_error_returns_empty():
    """测试异常时返回空列表（降级）"""
    result = await evaluate_rules({}, [])
    assert result == []

@pytest.mark.asyncio
async def test_evaluate_rules_no_match():
    """测试无匹配的情况"""
    features = {"rsi": 70.0, "macd": 1.5}
    rules = [
        {
            "rule_id": "rsi_oversold",
            "condition": {"op": "cmp", "field": "rsi", "cmp": "lt", "value": 40},
            "action": {"type": "enter", "side": "buy"}
        }
    ]
    result = await evaluate_rules(features, rules)
    assert isinstance(result, list)
    # RSI=70 > 40，不应该匹配
    assert len(result) == 0

@pytest.mark.asyncio
async def test_evaluate_rules_string_condition():
    """测试字符串条件的解析"""
    features = {"rsi": 30.0}
    rules = [
        {
            "rule_id": "rsi_oversold",
            "condition": "rsi < 40",
            "action": {"type": "enter", "side": "buy"}
        }
    ]
    result = await evaluate_rules(features, rules)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].rule_id == "rsi_oversold"