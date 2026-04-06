"""TraderAgent.

Phase 0 uses a deterministic rule-based idea generator:
- request last_price for watchlist from DataAgent
- generate TradeIdea with configurable target/stop percentages

Later phases can replace/augment this with LLM + memory.
"""

from __future__ import annotations

from datetime import date

from src.common.config import TraderConfig
from src.schemas.contracts import DataRequest, DataResponseStatus, TradeEntry, TradeIdea
from src.trader_profile.schemas import TraderProfile
from src.trader_memory.service import TraderMemoryStore


class TraderAgent:
    """Deterministic idea generator that blends profile, memory, and prices."""

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

    async def generate_trade_ideas(self, *, as_of_date: date, data_agent) -> list[TradeIdea]:
        """Generate structured trade ideas from current price plus trader context."""

        candidates = self._candidate_symbols()
        if not candidates:
            return []

        req = DataRequest(
            trader_id=self.trader.trader_id,
            symbols=candidates,
            fields=["last_price"],
        )
        resp = await data_agent.handle(req)

        if resp.status != DataResponseStatus.ok:
            return []

        prices: dict[str, float] = resp.payload.get("last_price", {})
        ideas: list[TradeIdea] = []

        for symbol in candidates:
            last_price = prices.get(symbol)
            if last_price is None:
                continue

            entry_price = float(last_price)
            target = entry_price * (1.0 + float(self.trader.default_target_pct))
            stop = entry_price * (1.0 - float(self.trader.default_stop_pct))
            rationale = "Phase0: rule-based idea from watchlist + mock price"
            profile_hint = self._profile_hint(symbol=symbol)
            if profile_hint:
                rationale += profile_hint
            hint = self._memory_hint(symbol=symbol)
            if hint:
                rationale += hint

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
            if hint:
                confidence += 0.05

            ideas.append(
                TradeIdea(
                    trader_id=self.trader.trader_id,
                    as_of_date=as_of_date,
                    symbol=symbol,
                    entry=TradeEntry(type="limit", price=entry_price),
                    target_price=round(target, 4),
                    stop_loss_price=round(stop, 4),
                    rationale=rationale,
                    invalidation="Price data unavailable or market regime changes",
                    confidence=min(0.85, round(confidence, 3)),
                )
            )

        return ideas
