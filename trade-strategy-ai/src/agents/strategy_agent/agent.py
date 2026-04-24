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
from src.strategy_library.schemas import StrategyVersion


class StrategyAgent(BaseAgent):
    """规则评估与信号合成层（NTL-S15-004）。

	职责边界（NTL-S15-004）：
	- 长期保留为规则评估层，负责从特征到信号的转换
	- 不直接抓取市场数据，委托 DataAgent 获取
	- 不承担风控判断，委托 RiskAgent
	- 不管理策略版本存储，委托 StrategyVersioning
	- 接收特征和规则列表，输出 RawSignal

	当前 Phase 0 流程：
	1. compute_features - 计算特征
	2. evaluate_rules - 评估规则
	3. combine_scores - 组合分数
	4. generate_signal - 生成信号

	后续演进（Stage 3/4）：
	- 接入策略版本库后，基于版本化规则快照评估（NTL-S4-003）
	- 不再使用静态规则模板

	Stage 4 升级（NTL-S4-003）：
	- generate_raw_signal 新增 strategy_version 参数
	- 当传入 strategy_version 时，优先使用其 rules_snapshot 进行规则评估
	- 实现版本化规则评估，而不是使用静态模板

	禁止：
	- 在 StrategyAgent 中硬编码具体规则
	- 承担风控、头寸计算、数据获取等职责
	"""

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
        rules: list[dict[str, Any]] | None = None,
        synthesis_mode: SynthesisMode = SynthesisMode.PRIORITY,
        strategy_version: StrategyVersion | None = None,
    ) -> RawSignal:
        """
        生成原始信号

        Stage 4 路径（strategy_version 非 None）：
        - 规则来源：strategy_version.rules_snapshot
        - 评估基于版本化规则快照，而不是静态模板

        Phase 0 路径（strategy_version 为 None）：
        - 规则来源：显式传入的 rules 参数
        - 兼容原有调用方式

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
            rules: 规则列表（Phase 0 路径）
            synthesis_mode: 合成模式
            strategy_version: 策略版本（Stage 4 路径，包含 rules_snapshot）

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

        # === 规则来源：Stage 4 路径 vs Phase 0 降级路径 ===
        if strategy_version is not None and strategy_version.rules_snapshot:
            # Stage 4 路径：使用策略版本的 rules_snapshot
            evaluation_rules = strategy_version.rules_snapshot
            version_id = strategy_version.version_id
        elif rules is not None:
            # Phase 0 路径：使用显式传入的 rules 参数
            evaluation_rules = rules
            version_id = "phase0"
        else:
            # 无规则可用，降级到空列表
            evaluation_rules = []
            version_id = "phase0"

        # 2. 评估规则
        rule_matches = await self.call_skill(
            "evaluate_rules",
            features=features,
            rules=evaluation_rules
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
            "rules_snapshot": [r.to_dict() if hasattr(r, 'to_dict') else r for r in rule_matches],
            "strategy_version_id": version_id,  # NT L-S4-003：记录评估使用的规则版本
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