from __future__ import annotations

from datetime import datetime

from src.persona.claim_keys import ClaimKey
from src.persona.schemas import (
	ActionSpec,
	ArticlePrecondition,
	ArticleStrategyRule,
	ClusterApplicability,
	InstrumentFocus,
	MarketRegime,
	PersonaClustersFile,
	StyleCluster,
)


def build_sample_clusters_file(*, trader_ids: list[str]) -> PersonaClustersFile:
	"""Generate a small sample cluster set.

	This exists to make the router runnable before crawler/extractor is finished.
	"""

	clusters_by_trader: dict[str, list[StyleCluster]] = {}

	for tid in trader_ids:
		clusters_by_trader[tid] = [
			StyleCluster(
				cluster_id=f"{tid}:etf_trend",
				label="ETF 趋势突破",
				instrument_focus=InstrumentFocus.etf,
				applicability=ClusterApplicability(preferred_regimes=[MarketRegime.trend_up, MarketRegime.range]),
				rules=[
					ArticleStrategyRule(
						claim_key=ClaimKey.entry_trigger,
						rule_type="entry",
						instrument_focus=InstrumentFocus.etf,
						condition={"op": "trend_up"},
						action=ActionSpec(type="enter", side="buy", order="limit", price={"var": "close"}),
						params={"target_pct": 0.06, "stop_pct": 0.03},
						confidence=0.6,
						published_at=datetime.utcnow(),
					),
				],
				activity_score=0.7,
				coherence_score=0.6,
				confidence_score=0.6,
			),
			StyleCluster(
				cluster_id=f"{tid}:cb_mean_revert",
				label="可转债 低吸均值回归",
				instrument_focus=InstrumentFocus.cb,
				applicability=ClusterApplicability(preferred_regimes=[MarketRegime.range, MarketRegime.panic]),
				rules=[
					ArticleStrategyRule(
						claim_key=ClaimKey.entry_trigger,
						rule_type="entry",
						instrument_focus=InstrumentFocus.cb,
						condition={"op": "pullback"},
						action=ActionSpec(type="enter", side="buy", order="limit", price={"var": "close"}),
						params={"target_pct": 0.08, "stop_pct": 0.04},
						confidence=0.55,
						published_at=datetime.utcnow(),
					),
				],
				preconditions=[
					ArticlePrecondition(
						instrument_focus=InstrumentFocus.cb,
						condition={"op": "range_or_panic"},
						confidence=0.5,
						published_at=datetime.utcnow(),
					)
				],
				activity_score=0.6,
				coherence_score=0.55,
				confidence_score=0.55,
			),
			StyleCluster(
				cluster_id=f"{tid}:stock_event",
				label="A股 事件驱动",
				instrument_focus=InstrumentFocus.stock,
				applicability=ClusterApplicability(preferred_regimes=[MarketRegime.trend_up, MarketRegime.euphoria]),
				rules=[
					ArticleStrategyRule(
						claim_key=ClaimKey.filter_event_risk,
						rule_type="filter",
						instrument_focus=InstrumentFocus.stock,
						condition={"op": "event"},
						action=ActionSpec(type="filter", params={"allow": True}),
						confidence=0.5,
						published_at=datetime.utcnow(),
					),
				],
				activity_score=0.5,
				coherence_score=0.5,
				confidence_score=0.5,
			),
		]

	return PersonaClustersFile(clusters_by_trader=clusters_by_trader)
