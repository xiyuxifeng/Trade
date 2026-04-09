"""规则评估引擎 - P4-002"""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.strategy.types import RuleMatch
from src.shared.exceptions import RuleEvaluationError

if TYPE_CHECKING:
    from src.persona.dsl_executor import DSLExecutor
    from src.persona.dsl_compiler import CompiledRule
    from src.features.feature_pipeline import FeatureVector
    from src.persona.schemas import MarketState


class RuleEvaluator:
    """规则评估引擎

    将 DSL 规则（CompiledRule）作用于特征向量，返回匹配结果。
    """

    def __init__(self, executor: DSLExecutor):
        self._executor = executor

    def evaluate(
        self,
        rules: list[CompiledRule],
        features: FeatureVector,
        market_state: MarketState,
    ) -> list[RuleMatch]:
        """评估单标的规则匹配

        Args:
            rules: 编译后的规则列表
            features: 特征向量
            market_state: 市场状态

        Returns:
            RuleMatch 列表
        """
        results = []
        for rule in rules:
            try:
                # 构建执行上下文
                state = market_state.model_dump() if hasattr(market_state, "model_dump") else {}
                bar = features.to_dict() if hasattr(features, "to_dict") else {}

                # 执行规则
                matched = rule.matches(state=state, bar=bar)

                # 提取置信度
                confidence = getattr(rule, "confidence", 0.5)
                if not isinstance(confidence, (int, float)):
                    confidence = 0.5

                results.append(RuleMatch(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    matched=matched,
                    confidence=confidence,
                    action=getattr(rule, "action", None),
                ))
            except Exception as e:
                raise RuleEvaluationError(f"Rule evaluation failed for {rule.rule_id}: {e}") from e

        return results

    def evaluate_batch(
        self,
        rules: list[CompiledRule],
        features_map: dict[str, FeatureVector],
        market_state: MarketState,
    ) -> dict[str, list[RuleMatch]]:
        """批量评估多标的的规则匹配

        Args:
            rules: 规则列表
            features_map: {symbol: FeatureVector}
            market_state: 市场状态

        Returns:
            {symbol: [RuleMatch]} 字典
        """
        results = {}
        for symbol, features in features_map.items():
            try:
                results[symbol] = self.evaluate(rules, features, market_state)
            except RuleEvaluationError:
                results[symbol] = []
        return results