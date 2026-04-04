from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.persona.claim_keys import ClaimKey


class InstrumentFocus(str, Enum):
	stock = "stock"
	etf = "etf"
	cb = "cb"  # convertible bond
	mixed = "mixed"


class MarketRegime(str, Enum):
	trend_up = "trend_up"
	trend_down = "trend_down"
	range = "range"
	panic = "panic"
	euphoria = "euphoria"
	unknown = "unknown"


class VolatilityLevel(str, Enum):
	low = "low"
	mid = "mid"
	high = "high"
	unknown = "unknown"


class LiquidityLevel(str, Enum):
	good = "good"
	bad = "bad"
	unknown = "unknown"


class BreadthLevel(str, Enum):
	strong = "strong"
	weak = "weak"
	unknown = "unknown"


class MarketState(BaseModel):
	as_of_date: date
	market: str = "CN"
	scope: str = "market"  # market/instrument
	regime: MarketRegime = MarketRegime.unknown
	volatility: VolatilityLevel = VolatilityLevel.unknown
	liquidity: LiquidityLevel = LiquidityLevel.unknown
	breadth: BreadthLevel = BreadthLevel.unknown
	event_risk: bool = False
	features: dict[str, Any] = Field(default_factory=dict)


# JSON expression tree; first version is intentionally flexible.
ConditionExpr = dict[str, Any]


class ActionSpec(BaseModel):
	type: str  # enter/exit/filter/sizing/risk
	side: str | None = None  # buy/sell
	order: str | None = None  # limit/market/trigger
	price: Any | None = None
	params: dict[str, Any] = Field(default_factory=dict)


class ArticleStrategyRule(BaseModel):
	"""Normalized rule extracted from a single article.

	Stored in `article_metadata.strategy_rules[]`.
	"""

	schema_version: str = "v0"
	claim_key: ClaimKey
	rule_type: str  # entry/exit/filter/sizing/risk
	instrument_focus: InstrumentFocus = InstrumentFocus.mixed
	condition: ConditionExpr = Field(default_factory=dict)
	action: ActionSpec
	params: dict[str, Any] = Field(default_factory=dict)
	confidence: float | None = None  # 0-1

	# Evidence
	source_url: str | None = None
	quoted_text: str | None = None
	published_at: datetime | None = None


class ArticlePrecondition(BaseModel):
	"""Market precondition extracted from a single article.

	Stored in `article_metadata.preconditions[]`.
	"""

	schema_version: str = "v0"
	claim_key: ClaimKey = ClaimKey.filter_market_regime
	instrument_focus: InstrumentFocus = InstrumentFocus.mixed
	condition: ConditionExpr = Field(default_factory=dict)
	confidence: float | None = None

	# Evidence
	source_url: str | None = None
	quoted_text: str | None = None
	published_at: datetime | None = None


class ClusterApplicability(BaseModel):
	preferred_regimes: list[MarketRegime] = Field(default_factory=list)
	volatility_preference: VolatilityLevel = VolatilityLevel.unknown
	liquidity_requirement: LiquidityLevel = LiquidityLevel.unknown
	timeframe_preference: str = "any"  # intraday/daily/swing/any


class StyleCluster(BaseModel):
	cluster_id: str
	label: str
	instrument_focus: InstrumentFocus = InstrumentFocus.mixed
	applicability: ClusterApplicability = Field(default_factory=ClusterApplicability)

	# Aggregated rules
	rules: list[ArticleStrategyRule] = Field(default_factory=list)
	preconditions: list[ArticlePrecondition] = Field(default_factory=list)

	# Stats for routing
	activity_score: float = 0.0
	coherence_score: float = 0.5
	confidence_score: float = 0.5

	evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class RouterExplanation(BaseModel):
	reasons: list[str] = Field(default_factory=list)
	score_breakdown: dict[str, float] = Field(default_factory=dict)


class RouterDecision(BaseModel):
	trader_id: str
	symbol: str
	as_of_date: date
	selected_cluster_id: str | None = None
	selected_cluster_label: str | None = None
	score: float | None = None
	explanation: RouterExplanation = Field(default_factory=RouterExplanation)
	candidates: list[dict[str, Any]] = Field(default_factory=list)  # top-k debug


class PersonaClustersFile(BaseModel):
	schema_version: str = "v0"
	generated_at: datetime = Field(default_factory=datetime.utcnow)
	clusters_by_trader: dict[str, list[StyleCluster]] = Field(default_factory=dict)
