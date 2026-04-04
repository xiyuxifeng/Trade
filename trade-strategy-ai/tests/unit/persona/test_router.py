from __future__ import annotations

from datetime import date

from src.persona.claim_keys import ClaimKey
from src.persona.router import PersonaRouter
from src.persona.schemas import (
	ActionSpec,
	ArticleStrategyRule,
	ClusterApplicability,
	InstrumentFocus,
	LiquidityLevel,
	MarketRegime,
	MarketState,
	StyleCluster,
	VolatilityLevel,
)


def test_router_prefers_applicable_trend_cluster() -> None:
	router = PersonaRouter(top_k=2)
	ms = MarketState(
		as_of_date=date(2026, 4, 4),
		regime=MarketRegime.trend_up,
		volatility=VolatilityLevel.mid,
		liquidity=LiquidityLevel.good,
	)

	trend = StyleCluster(
		cluster_id="t:etf_trend",
		label="ETF 趋势突破",
		instrument_focus=InstrumentFocus.etf,
		applicability=ClusterApplicability(preferred_regimes=[MarketRegime.trend_up]),
		rules=[
			ArticleStrategyRule(
				claim_key=ClaimKey.entry_trigger,
				rule_type="entry",
				instrument_focus=InstrumentFocus.etf,
				condition={"op": "trend_up"},
				action=ActionSpec(type="enter", side="buy"),
			),
		],
		activity_score=0.5,
		coherence_score=0.6,
		confidence_score=0.6,
	)

	mean_revert = StyleCluster(
		cluster_id="t:cb_mean_revert",
		label="可转债 低吸均值回归",
		instrument_focus=InstrumentFocus.cb,
		applicability=ClusterApplicability(preferred_regimes=[MarketRegime.range]),
		rules=[],
		activity_score=0.9,
		coherence_score=0.6,
		confidence_score=0.6,
	)

	decision = router.route_symbol(
		trader_id="trader_a",
		symbol="510300.SH",
		as_of_date=ms.as_of_date,
		instrument_focus=InstrumentFocus.etf,
		market_state=ms,
		clusters=[mean_revert, trend],
	)

	assert decision.selected_cluster_id == "t:etf_trend"
	assert decision.selected_cluster_label == "ETF 趋势突破"
	assert decision.score is not None
	assert decision.candidates
