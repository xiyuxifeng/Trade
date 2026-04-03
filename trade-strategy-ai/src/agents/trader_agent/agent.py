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


class TraderAgent:
	def __init__(self, *, trader: TraderConfig) -> None:
		self.trader = trader

	async def generate_trade_ideas(self, *, as_of_date: date, data_agent) -> list[TradeIdea]:
		if not self.trader.watchlist:
			return []

		req = DataRequest(
			trader_id=self.trader.trader_id,
			symbols=self.trader.watchlist,
			fields=["last_price"],
		)
		resp = await data_agent.handle(req)

		if resp.status != DataResponseStatus.ok:
			return []

		prices: dict[str, float] = resp.payload.get("last_price", {})
		ideas: list[TradeIdea] = []

		for symbol in self.trader.watchlist:
			last_price = prices.get(symbol)
			if last_price is None:
				continue

			entry_price = float(last_price)
			target = entry_price * (1.0 + float(self.trader.default_target_pct))
			stop = entry_price * (1.0 - float(self.trader.default_stop_pct))

			ideas.append(
				TradeIdea(
					trader_id=self.trader.trader_id,
					as_of_date=as_of_date,
					symbol=symbol,
					entry=TradeEntry(type="limit", price=entry_price),
					target_price=round(target, 4),
					stop_loss_price=round(stop, 4),
					rationale="Phase0: rule-based idea from watchlist + mock price",
					invalidation="Price data unavailable or market regime changes",
					confidence=0.3,
				)
			)

		return ideas
