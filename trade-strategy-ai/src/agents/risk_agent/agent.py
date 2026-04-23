"""Risk Agent 主控逻辑"""
from typing import Any
from src.agents.base import BaseAgent
from src.strategy.types import RawSignal, Signal as StrategySignal, SignalSide
from src.risk.types import AccountSnapshot, StopLossLevel
from src.strategy.types import PositionSize
from src.agents.risk_agent.skills import (
    drawdown_control,
    calculate_stop_loss,
    calculate_position_size
)


class RiskAgent(BaseAgent):
    """风险过滤层（NTL-S15-005）。

	职责边界（NTL-S15-005）：
	- 长期保留为风险过滤层，负责信号的风控检查与调整
	- 不承担策略构建、数据抓取、头寸分配策略制定等职责
	- 接收 RawSignal 和账户快照，输出可能被拒绝的最终 Signal

	当前 Phase 0 流程：
	1. drawdown_control - 回撤控制检查
	2. stop_loss - 止损计算
	3. position_sizing - 头寸计算

	后续演进：
	- 风控规则可配置化，不硬编码在 Agent 内
	- 异常时默认拒绝信号（HOLD，confidence=0）

	禁止：
	- 在 RiskAgent 中承担策略构建、数据抓取职责
	- 越过信号直接下单
	"""

    def __init__(self):
        super().__init__("risk_agent")
        self._register_skills()

    def _register_skills(self):
        """注册 Skill"""
        self.register_skill("drawdown_control", drawdown_control)
        self.register_skill("stop_loss", calculate_stop_loss)
        self.register_skill("position_sizing", calculate_position_size)

    async def check(
        self,
        raw_signal: RawSignal,
        account: AccountSnapshot,
        market_data: dict[str, Any],
        risk_config: dict[str, Any]
    ) -> StrategySignal:
        """
        风控检查

        流程:
        1. drawdown_control - 回撤控制
        2. stop_loss - 止损计算
        3. position_sizing - 头寸计算
        4. check_and_alert - 综合检查

        Args:
            raw_signal: 原始信号
            account: 账户快照
            market_data: 市场数据
            risk_config: 风控配置

        Returns:
            最终 Signal（可能被拒绝）
        """
        try:
            # 1. 回撤控制检查
            drawdown_result = await self.call_skill(
                "drawdown_control",
                account=account,
                signal=raw_signal
            )

            if not drawdown_result["passed"]:
                return self._reject_signal(raw_signal, drawdown_result["reason"])

            # 2. 止损计算
            stop_loss = await self.call_skill(
                "stop_loss",
                signal=raw_signal,
                market_data=market_data,
                config=risk_config.get("stop_loss", {})
            )

            # 3. 头寸计算
            position_size = await self.call_skill(
                "position_sizing",
                signal=raw_signal,
                account=account,
                config=risk_config.get("position_sizing", {})
            )

            # 4. 构建最终信号
            final_signal = StrategySignal(
                signal_id=raw_signal.signal_id,
                symbol=raw_signal.symbol,
                side=raw_signal.side,
                confidence=raw_signal.confidence,
                timestamp=raw_signal.timestamp,
                triggered_rules=raw_signal.triggered_rules,
                synthesis_mode=raw_signal.synthesis_mode,
                entry_price=raw_signal.entry_price,
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=None,
                metadata=raw_signal.metadata,
            )

            return final_signal

        except Exception as e:
            # Risk Agent 异常 → 拒绝
            return self._reject_signal(raw_signal, str(e))

    def _reject_signal(self, raw_signal: RawSignal, reason: str) -> StrategySignal:
        """构建拒绝信号"""
        return StrategySignal(
            signal_id=raw_signal.signal_id,
            symbol=raw_signal.symbol,
            side=SignalSide.HOLD,
            confidence=0.0,
            timestamp=raw_signal.timestamp,
            triggered_rules=raw_signal.triggered_rules,
            synthesis_mode=raw_signal.synthesis_mode,
            entry_price=None,
            position_size=None,
            stop_loss=None,
            take_profit=None,
            metadata={"rejected_reason": reason},
        )