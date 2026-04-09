"""多规则信号合成器 - P4-003"""
from __future__ import annotations

import uuid
from typing import Any

from src.strategy.types import (
    RuleMatch,
    SynthesisContext,
    RawSignal,
    SignalSide,
    SynthesisMode,
    PriceSpec,
    PositionSize,
    PositionSizeType,
)
from src.shared.exceptions import SignalSynthesisError


class SignalSynthesizer:
    """多规则信号合成器

    支持三种合成模式:
    - WEIGHTED_SCORE: 加权评分
    - VOTING: 投票机制
    - PRIORITY: 优先级覆盖（默认）
    """

    # 默认优先级（数值越大优先级越高）
    DEFAULT_PRIORITIES = ["entry", "sizing", "exit", "filter", "risk"]

    def __init__(
        self,
        mode: SynthesisMode = SynthesisMode.PRIORITY,
        weights: dict[str, float] | None = None,
        priorities: list[str] | None = None,
    ):
        self._mode = mode
        self._weights = weights or {}
        self._priorities = priorities or self.DEFAULT_PRIORITIES

    def synthesize(
        self,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """合成信号

        Args:
            matches: 规则匹配结果列表
            context: 合成上下文

        Returns:
            RawSignal 原始信号（未经过风控）
        """
        if not matches:
            return self._create_hold_signal(context)

        # 过滤已匹配的规则
        matched = [m for m in matches if m.matched]
        if not matched:
            return self._create_hold_signal(context)

        # 根据模式合成
        if self._mode == SynthesisMode.WEIGHTED_SCORE:
            return self._synthesize_weighted(matched, context)
        elif self._mode == SynthesisMode.VOTING:
            return self._synthesize_voting(matched, context)
        else:
            return self._synthesize_priority(matched, context)

    def _synthesize_weighted(
        self,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """加权评分合成"""
        scores = {SignalSide.BUY: 0.0, SignalSide.SELL: 0.0, SignalSide.HOLD: 0.0}

        for m in matches:
            weight = self._weights.get(m.rule_type, 1.0)
            side = self._extract_side(m)
            score = weight * m.confidence
            scores[side] += score

        # 阈值判定
        total = scores[SignalSide.BUY] + scores[SignalSide.SELL]
        if total == 0:
            return self._create_hold_signal(context)

        buy_ratio = scores[SignalSide.BUY] / total
        if buy_ratio > 0.6:
            side = SignalSide.BUY
        elif buy_ratio < 0.4:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD

        confidence = scores[side] / len(matches)
        return self._create_signal(side, confidence, matches, context)

    def _synthesize_voting(
        self,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """投票合成"""
        votes = {SignalSide.BUY: 0, SignalSide.SELL: 0, SignalSide.HOLD: 0}

        for m in matches:
            side = self._extract_side(m)
            votes[side] += 1

        # 多数胜出
        max_votes = max(votes.values())
        if votes[SignalSide.BUY] == max_votes and votes[SignalSide.SELL] != max_votes:
            side = SignalSide.BUY
        elif votes[SignalSide.SELL] == max_votes and votes[SignalSide.BUY] != max_votes:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD

        confidence = max_votes / len(matches)
        return self._create_signal(side, confidence, matches, context)

    def _synthesize_priority(
        self,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """优先级合成（默认）"""
        # 按优先级排序（低索引=高优先级，排在前）
        sorted_matches = sorted(
            matches,
            key=lambda m: self._priorities.index(m.rule_type)
            if m.rule_type in self._priorities
            else len(self._priorities),
        )

        # 获取最高优先级匹配的信号
        for m in sorted_matches:
            side = self._extract_side(m)
            if side != SignalSide.HOLD:
                confidence = m.confidence
                return self._create_signal(side, confidence, matches, context)

        return self._create_hold_signal(context)

    def _extract_side(self, match: RuleMatch) -> SignalSide:
        """从匹配结果提取信号方向"""
        action = match.action
        if not action or not action.side:
            return SignalSide.HOLD

        side_map = {
            "buy": SignalSide.BUY,
            "sell": SignalSide.SELL,
        }
        return side_map.get(action.side.lower(), SignalSide.HOLD)

    def _create_signal(
        self,
        side: SignalSide,
        confidence: float,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """创建信号"""
        return RawSignal(
            signal_id=str(uuid.uuid4()),
            symbol="UNKNOWN",  # 待后续填充
            side=side,
            confidence=confidence,
            triggered_rules=[m.rule_id for m in matches if m.matched],
            synthesis_mode=self._mode,
            entry_price=PriceSpec(type="market"),
            position_size=PositionSize(
                type=PositionSizeType.FIXED_RATIO,
                value=0.05,
            ),
            timestamp=None,
            metadata={"context": context.market_state},
        )

    def _create_hold_signal(self, context: SynthesisContext) -> RawSignal:
        """创建 HOLD 信号"""
        return RawSignal(
            signal_id=str(uuid.uuid4()),
            symbol="UNKNOWN",
            side=SignalSide.HOLD,
            confidence=0.0,
            triggered_rules=[],
            synthesis_mode=self._mode,
            timestamp=None,
        )
