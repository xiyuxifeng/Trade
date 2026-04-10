"""Strategy Agent 主控逻辑"""
from typing import Any
from src.agents.base import BaseAgent
from src.strategy.types import RawSignal, SignalSide, SynthesisMode
from src.agents.strategy_agent.skills import (
    compute_features,
    evaluate_rules,
    combine_scores,
    generate_signal
)


class StrategyAgent(BaseAgent):
    """策略 Agent - 负责信号合成"""

    def __init__(self):
        super().__init__("strategy_agent")
        self._register_skills()

    def _register_skills(self):
        """注册 Skill"""
        self.register_skill("compute_features", compute_features)
        self.register_skill("evaluate_rules", evaluate_rules)
        self.register_skill("combine_scores", combine_scores)
        self.register_skill("generate_signal", generate_signal)

    async def generate_raw_signal(
        self,
        symbol: str,
        trade_idea: Any,
        market_data: dict[str, Any],
        features: dict[str, float],
        rules: list[dict[str, Any]],
        synthesis_mode: SynthesisMode = SynthesisMode.PRIORITY
    ) -> RawSignal:
        """
        生成原始信号

        流程:
        1. compute_features - 计算特征
        2. evaluate_rules - 评估规则
        3. combine_scores - 组合分数
        4. generate_signal - 生成信号

        Args:
            symbol: 股票代码
            trade_idea: 交易想法
            market_data: 市场数据
            features: 预计算的特征
            rules: 规则列表
            synthesis_mode: 合成模式

        Returns:
            RawSignal
        """
        # 1. 计算特征（如未预计算）
        if not features:
            features = await self.call_skill(
                "compute_features",
                symbol=symbol,
                market_data=market_data,
                context={}
            )

        # 2. 评估规则
        rule_matches = await self.call_skill(
            "evaluate_rules",
            features=features,
            rules=rules
        )

        # 3. 组合分数
        score_result = await self.call_skill(
            "combine_scores",
            rule_matches=rule_matches,
            mode=synthesis_mode
        )

        # 4. 生成信号
        context = {
            "features_snapshot": features,
            "market_state": market_data,
            "rules_snapshot": [r.to_dict() if hasattr(r, 'to_dict') else r for r in rule_matches]
        }

        raw_signal = await self.call_skill(
            "generate_signal",
            symbol=symbol,
            side=score_result["side"],
            confidence=score_result["confidence"],
            triggered_rules=score_result["triggered_rules"],
            synthesis_mode=synthesis_mode,
            context=context
        )

        return raw_signal