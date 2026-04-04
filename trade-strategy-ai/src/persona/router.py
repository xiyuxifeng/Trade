from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.persona.schemas import (
	InstrumentFocus,
	LiquidityLevel,
	BreadthLevel,
	MarketRegime,
	MarketState,
	RouterDecision,
	RouterExplanation,
	StyleCluster,
	VolatilityLevel,
)


@dataclass(frozen=True)
class RouterWeights:
	wE: float = 0.40
	wA: float = 0.25
	wF: float = 0.15
	wR: float = 0.10
	wC: float = 0.10
	wP: float = 0.10


class PersonaRouter:
	"""Return-maximizing router (Phase 1).

	Notes:
	- Phase 1 does not require backtest; E uses a proxy table.
	- If MarketState fields are unknown, router degrades gracefully.
	"""

	def __init__(
		self,
		*,
		weights: RouterWeights | None = None,
		top_k: int = 2,
	) -> None:
		self.weights = weights or RouterWeights()
		self.top_k = top_k

	def route_symbol(
		self,
		*,
		trader_id: str,
		symbol: str,
		as_of_date: date,
		instrument_focus: InstrumentFocus,
		market_state: MarketState,
		clusters: list[StyleCluster],
	) -> RouterDecision:
		candidates: list[tuple[float, StyleCluster, RouterExplanation]] = []

		for c in clusters:
			if not self._hard_filter(cluster=c, instrument_focus=instrument_focus, market_state=market_state):
				continue
			expl, score = self._score(
				cluster=c,
				instrument_focus=instrument_focus,
				market_state=market_state,
			)
			candidates.append((score, c, expl))

		candidates.sort(key=lambda x: x[0], reverse=True)
		top = candidates[: max(self.top_k, 1)]

		decision = RouterDecision(trader_id=trader_id, symbol=symbol, as_of_date=as_of_date)
		decision.candidates = [
			{
				"cluster_id": c.cluster_id,
				"label": c.label,
				"score": round(float(score), 6),
				"breakdown": expl.score_breakdown,
				"reasons": expl.reasons,
			}
			for score, c, expl in top
		]

		if not top:
			decision.explanation.reasons = ["No eligible style cluster (all filtered or missing)"]
			return decision

		best_score, best_cluster, best_expl = top[0]
		decision.selected_cluster_id = best_cluster.cluster_id
		decision.selected_cluster_label = best_cluster.label
		decision.score = round(float(best_score), 6)
		decision.explanation = best_expl
		return decision

	def _hard_filter(
		self,
		*,
		cluster: StyleCluster,
		instrument_focus: InstrumentFocus,
		market_state: MarketState,
	) -> bool:
		if cluster.instrument_focus not in (InstrumentFocus.mixed, instrument_focus):
			return False

		req = cluster.applicability.liquidity_requirement
		if req == LiquidityLevel.good and market_state.liquidity == LiquidityLevel.bad:
			return False

		return True

	def _applicability_score(self, *, cluster: StyleCluster, market_state: MarketState) -> float:
		pref = cluster.applicability.preferred_regimes
		if not pref:
			base = 0.6
		elif market_state.regime == MarketRegime.unknown:
			base = 0.5
		elif market_state.regime in pref:
			base = 1.0
		else:
			base = 0.2

		# volatility preference (soft)
		vol_pref = cluster.applicability.volatility_preference
		if vol_pref == VolatilityLevel.unknown or market_state.volatility == VolatilityLevel.unknown:
			return base
		if vol_pref == market_state.volatility:
			return min(1.0, base + 0.1)
		return max(0.0, base - 0.1)

	def _expected_return_proxy(self, *, cluster: StyleCluster, market_state: MarketState) -> float:
		label = cluster.label.lower()
		regime = market_state.regime

		def _trend_table() -> float:
			if regime == MarketRegime.trend_up:
				return 1.0
			if regime == MarketRegime.range:
				return 0.3
			if regime in (MarketRegime.trend_down, MarketRegime.panic):
				return 0.1
			return 0.4

		def _mean_revert_table() -> float:
			if regime == MarketRegime.range:
				return 0.8
			if regime == MarketRegime.trend_up:
				return 0.6
			if regime == MarketRegime.panic:
				return 0.5
			if regime == MarketRegime.euphoria:
				return 0.2
			return 0.5

		def _event_table() -> float:
			# In Phase 1 we approximate: high vol + breadth strong boosts event style.
			high_vol = market_state.volatility == VolatilityLevel.high
			breadth_strong = market_state.breadth == BreadthLevel.strong
			if high_vol and breadth_strong:
				return 0.9
			return 0.3

		if any(k in label for k in ["趋势", "breakout", "trend"]):
			return _trend_table()
		if any(k in label for k in ["低吸", "均值", "mean", "revert"]):
			return _mean_revert_table()
		if any(k in label for k in ["事件", "news", "event"]):
			return _event_table()

		# fallback
		if regime == MarketRegime.unknown:
			return 0.5
		return 0.4

	def _risk_penalty(self, *, cluster: StyleCluster, market_state: MarketState) -> float:
		#收益最大化下只做“基本风险约束”，惩罚较轻。
		penalty = 0.0
		if market_state.event_risk:
			penalty += 0.2
		if market_state.volatility == VolatilityLevel.high:
			penalty += 0.2
		return min(1.0, penalty)

	def _fit_score(self, *, cluster: StyleCluster, instrument_focus: InstrumentFocus) -> float:
		if cluster.instrument_focus == InstrumentFocus.mixed:
			return 0.6
		if cluster.instrument_focus == instrument_focus:
			return 1.0
		return 0.0

	def _score(
		self,
		*,
		cluster: StyleCluster,
		instrument_focus: InstrumentFocus,
		market_state: MarketState,
	) -> tuple[RouterExplanation, float]:
		A = self._applicability_score(cluster=cluster, market_state=market_state)
		E = self._expected_return_proxy(cluster=cluster, market_state=market_state)
		F = self._fit_score(cluster=cluster, instrument_focus=instrument_focus)
		R = max(0.0, min(1.0, float(cluster.activity_score)))
		C = max(0.0, min(1.0, float((cluster.coherence_score + cluster.confidence_score) / 2.0)))
		P = self._risk_penalty(cluster=cluster, market_state=market_state)

		score = (
			self.weights.wE * E
			+ self.weights.wA * A
			+ self.weights.wF * F
			+ self.weights.wR * R
			+ self.weights.wC * C
			- self.weights.wP * P
		)

		expl = RouterExplanation(
			reasons=[
				f"E={E:.2f} expected-return proxy",
				f"A={A:.2f} applicability(regime/vol/liquidity)",
				f"F={F:.2f} instrument-fit({instrument_focus})",
			],
			score_breakdown={
				"E": round(float(E), 6),
				"A": round(float(A), 6),
				"F": round(float(F), 6),
				"R": round(float(R), 6),
				"C": round(float(C), 6),
				"P": round(float(P), 6),
			},
		)

		return expl, float(score)
