"""RuleEvaluator 单元测试"""
import pytest
from datetime import date
from src.strategy.rule_evaluator import RuleEvaluator
from src.persona.dsl_executor import DSLExecutor, RuleRegistry
from src.persona.dsl_compiler import compile_rule
from src.persona.dsl import CMP
from src.persona.schemas import MarketRegime, VolatilityLevel, MarketState


def _create_sample_market_state() -> MarketState:
    """创建样本市场状态"""
    return MarketState(
        as_of_date=date(2026, 4, 9),
        regime=MarketRegime.trend_up,
        volatility=VolatilityLevel.low,
    )


def _compile_sample_rule():
    """编译样本规则"""
    rule = compile_rule(
        CMP(field="regime", cmp_op="eq", value="trend_up"),
        rule_id="test_rule",
        name="Test Rule",
    )
    return rule


def test_evaluate_returns_rule_matches():
    """测试评估返回规则匹配结果"""
    registry = RuleRegistry()
    executor = DSLExecutor(registry)
    evaluator = RuleEvaluator(executor)

    rule = _compile_sample_rule()
    registry.register(rule)

    state = _create_sample_market_state()
    from src.features.feature_pipeline import FeatureVector
    features = FeatureVector()

    matches = evaluator.evaluate([rule], features, state)
    assert len(matches) == 1
    assert matches[0].rule_id == rule.rule_id


def test_evaluate_no_match():
    """测试不匹配的情况"""
    registry = RuleRegistry()
    executor = DSLExecutor(registry)
    evaluator = RuleEvaluator(executor)

    rule = compile_rule(
        CMP(field="regime", cmp_op="eq", value="trend_down"),
        rule_id="down_rule",
        name="Down Rule",
    )
    registry.register(rule)

    state = _create_sample_market_state()  # regime = trend_up
    from src.features.feature_pipeline import FeatureVector
    features = FeatureVector()

    matches = evaluator.evaluate([rule], features, state)
    assert len(matches) == 1
    assert matches[0].matched is False