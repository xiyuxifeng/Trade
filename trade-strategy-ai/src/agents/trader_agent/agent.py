"""TraderAgent - per-trader 执行器。

职责边界（NTL-S15-003）：
- 长期保留为 per-trader 执行器，负责为单个 trader 生成交易想法
- 不直接抓取数据，委托 DataAgent 获取
- 不承担策略评估，委托 StrategyAgent/RiskAgent
- 不管理记忆存储，委托 TraderMemoryStore

Phase 0（当前）：
- 基于 watchlist + last_price 生成 TradeIdea
- 使用 target/stop 百分比配置

后续演进（Stage 4）：
- 输入升级为：策略版本、强势池快照、画像、记忆
- 不再以 watchlist 为核心输入
- 同一 trader 同日只产出一个 released 版本

禁止：
- 在 TraderAgent 中硬编码跨 trader 的编排逻辑
- 承担 ManagerAgent 的编排职责
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from src.common.config import TraderConfig
from src.market_universe.schemas import MarketUniverse
from src.schemas.contracts import DataRequest, DataResponseStatus, TradeEntry, TradeIdea
from src.strategy_library.schemas import StrategyVersion
from src.trader_profile.schemas import TraderProfile
from src.trader_memory.service import TraderMemoryStore

if TYPE_CHECKING:
    from src.agents.data_agent import DataAgent


class TraderAgent:
    """Per-trader 交易想法生成器。

    职责（NTL-S15-003）：
    - 接收 trader 配置、记忆、画像作为输入
    - 委托 DataAgent 获取市场数据
    - 生成 TradeIdea 列表返回给 ManagerAgent
    - 不做风控、不做评估、不做编排

    Stage 4 输入升级（NTL-S4-001）：
    - 主要候选来源：strategy_version.recommendations（替代 watchlist）
    - 额外上下文：market_universe.strong_symbols 提供强势标的评分
    - Phase 0 兼容：当未传入 strategy_version 时，降级到 watchlist + profile.top_symbols 路径
    """

    def __init__(
        self,
        *,
        trader: TraderConfig,
        memory_store: TraderMemoryStore | None = None,
        trader_profile: TraderProfile | None = None,
    ) -> None:
        self.trader = trader
        self.memory_store = memory_store
        self.trader_profile = trader_profile

    def _candidate_symbols(self) -> list[str]:
        """Merge watchlist and profile symbols into a stable candidate list."""

        candidates: list[str] = []
        seen: set[str] = set()

        for symbol in self.trader.watchlist:
            if isinstance(symbol, str) and symbol.strip() and symbol not in seen:
                candidates.append(symbol)
                seen.add(symbol)

        if self.trader_profile is not None:
            for stat in self.trader_profile.top_symbols:
                if isinstance(stat.symbol, str) and stat.symbol.strip() and stat.symbol not in seen:
                    candidates.append(stat.symbol)
                    seen.add(stat.symbol)

        return candidates

    def _memory_hint(self, *, symbol: str) -> str | None:
        """Turn recent trader memories into a short prompt hint."""

        if self.memory_store is None:
            return None

        summary = self.memory_store.summarize_context(trader_id=self.trader.trader_id, symbol=symbol, limit=3)
        if summary.total_items == 0:
            return None

        parts: list[str] = []
        if summary.symbol_titles:
            parts.append("symbol: " + ", ".join(summary.symbol_titles[:2]))
        if summary.review_notes:
            parts.append("review: " + ", ".join(summary.review_notes[:2]))
        if summary.recent_titles:
            parts.append("recent: " + ", ".join(summary.recent_titles[:2]))

        if not parts:
            return None
        return " | memory summary: " + "; ".join(parts)

    def _profile_hint(self, *, symbol: str) -> str | None:
        """Turn trader profile stats into a short prompt hint."""

        if self.trader_profile is None:
            return None

        parts: list[str] = []
        if self.trader_profile.top_symbols:
            top = ", ".join(f"{item.symbol}({item.mentions})" for item in self.trader_profile.top_symbols[:3])
            parts.append(f"profile symbols: {top}")
        if self.trader_profile.concept_tags:
            parts.append(f"tags: {', '.join(self.trader_profile.concept_tags[:3])}")
        if self.trader_profile.style_cluster_ids:
            parts.append(f"clusters: {', '.join(self.trader_profile.style_cluster_ids[:2])}")
        if self.memory_store is not None:
            summary = self.memory_store.summarize_context(trader_id=self.trader.trader_id, symbol=symbol, limit=2)
            if summary.by_type:
                type_bits = ", ".join(f"{key}={value}" for key, value in sorted(summary.by_type.items()))
                parts.append(f"memory mix: {type_bits}")

        if not parts:
            return None
        return " | profile: " + "; ".join(parts)

    def _candidates_from_strategy(
        self,
        strategy_version: StrategyVersion,
    ) -> list[tuple[str, str, float, int]]:
        """从策略版本 recommendations 提取候选标的列表。

        Args:
            strategy_version: 已发布的策略版本

        Returns:
            (symbol, decision, confidence, rec_index) 元组列表
        """
        candidates: list[tuple[str, str, float, int]] = []
        seen: set[str] = set()
        for idx, rec in enumerate(strategy_version.recommendations):
            if rec.symbol in seen:
                continue
            candidates.append((rec.symbol, rec.decision, rec.confidence, idx))
            seen.add(rec.symbol)
        return candidates

    def _strong_symbol_hint(self, *, symbol: str, market_universe: MarketUniverse) -> str | None:
        """从 MarketUniverse.strong_symbols 中提取标的的强势评分上下文。"""
        if market_universe.strong_symbols is None:
            return None
        strong_symbols = market_universe.strong_symbols.symbols
        for ss in strong_symbols:
            if ss.symbol == symbol and ss.strength_score is not None:
                parts = [f"strength={ss.strength_score}"]
                if ss.change_pct is not None:
                    parts.append(f"change={ss.change_pct}%")
                if ss.turnover is not None:
                    parts.append(f"turnover={ss.turnover}")
                if ss.topic_tags:
                    parts.append(f"topics={ss.topic_tags}")
                return " | strong_symbol: " + ", ".join(parts)
        return None

    async def generate_trade_ideas(
        self,
        *,
        as_of_date: date,
        data_agent: DataAgent,
        strategy_version: StrategyVersion | None = None,
        market_universe: MarketUniverse | None = None,
    ) -> list[TradeIdea]:
        """Generate structured trade ideas.

        Stage 4 路径（strategy_version 非 None）：
        - 候选标的来自 strategy_version.recommendations（buy/hold 决策）
        - market_universe.strong_symbols 提供强势评分上下文
        - confidence 优先使用 strategy_version 中的值

        Phase 0 路径（strategy_version 为 None）：
        - 候选标的来自 trader.watchlist + profile.top_symbols
        - 兼容原有逻辑
        """

        # === 候选标的派生：Stage 4 路径 vs Phase 0 降级路径 ===
        if strategy_version is not None:
            # Stage 4 路径：基于策略版本推荐
            strategy_candidates = self._candidates_from_strategy(strategy_version)
            if not strategy_candidates:
                return []
            # 提取纯 symbol 列表用于行情请求
            candidate_symbols = [sym for sym, _, _, _ in strategy_candidates]
            candidate_map: dict[str, tuple[str, float]] = {
                sym: (decision, conf) for sym, decision, conf, _ in strategy_candidates
            }
            candidate_rec_index: dict[str, int] = {
                sym: idx for sym, _, _, idx in strategy_candidates
            }
            idea_mode = "strategy"
        else:
            # Phase 0 降级路径：使用 watchlist + profile.top_symbols
            candidate_symbols = self._candidate_symbols()
            if not candidate_symbols:
                return []
            candidate_map = {sym: ("buy", 0.3) for sym in candidate_symbols}
            idea_mode = "phase0"

        # === 获取行情数据 ===
        req = DataRequest(
            trader_id=self.trader.trader_id,
            symbols=candidate_symbols,
            fields=["last_price"],
        )
        resp = await data_agent.handle(req)

        if resp.status != DataResponseStatus.ok:
            return []

        prices: dict[str, float] = resp.payload.get("last_price", {})
        ideas: list[TradeIdea] = []

        for symbol in candidate_symbols:
            last_price = prices.get(symbol)
            if last_price is None:
                continue

            entry_price = float(last_price)
            target = entry_price * (1.0 + float(self.trader.default_target_pct))
            stop = entry_price * (1.0 - float(self.trader.default_stop_pct))

            if idea_mode == "strategy":
                rationale = f"Stage4: strategy-based idea from version {strategy_version.version_id}"
            else:
                rationale = "Phase0: rule-based idea from watchlist + mock price"

            # strong_symbols 上下文（Stage 4 路径）
            if market_universe is not None:
                strong_hint = self._strong_symbol_hint(symbol=symbol, market_universe=market_universe)
                if strong_hint:
                    rationale += strong_hint

            # profile 上下文
            profile_hint = self._profile_hint(symbol=symbol)
            if profile_hint:
                rationale += profile_hint

            # memory 上下文
            memory_hint = self._memory_hint(symbol=symbol)
            if memory_hint:
                rationale += memory_hint

            # === confidence 计算 ===
            decision, strategy_confidence = candidate_map[symbol]
            if idea_mode == "strategy":
                # Stage 4 路径：优先使用策略版本的 confidence
                confidence = strategy_confidence
            else:
                # Phase 0 路径：使用原有的启发式 confidence
                confidence = 0.3
                if self.trader_profile is not None:
                    confidence += min(0.15, 0.03 * len(self.trader_profile.top_symbols[:5]))
                    if self.trader_profile.concept_tags:
                        confidence += 0.05
                    if self.trader_profile.style_cluster_ids:
                        confidence += 0.05
                if self.memory_store is not None:
                    summary = self.memory_store.summarize_context(trader_id=self.trader.trader_id, symbol=symbol, limit=3)
                    if summary.by_type.get("success_case", 0):
                        confidence += 0.03
                    if summary.by_type.get("failure_case", 0):
                        confidence += 0.01
                if memory_hint:
                    confidence += 0.05

            ideas.append(
                TradeIdea(
                    trader_id=self.trader.trader_id,
                    as_of_date=as_of_date,
                    symbol=symbol,
                    side=decision,
                    entry=TradeEntry(type="limit", price=entry_price),
                    target_price=round(target, 4),
                    stop_loss_price=round(stop, 4),
                    rationale=rationale,
                    invalidation="Price data unavailable or market regime changes",
                    confidence=min(0.85, round(confidence, 3)),
                    strategy_version_id=strategy_version.version_id if strategy_version else None,
                    source_recommendation_idx=candidate_rec_index.get(symbol) if idea_mode == "strategy" else None,
                )
            )

        return ideas
