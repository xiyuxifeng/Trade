from __future__ import annotations

from enum import Enum


class ClaimKey(str, Enum):
	# Entry
	entry_trigger = "entry.trigger"
	entry_confirmation = "entry.confirmation"
	entry_timing = "entry.timing"
	entry_price_type = "entry.price_type"

	# Filters
	filter_market_regime = "filter.market_regime"
	filter_volatility = "filter.volatility"
	filter_event_risk = "filter.event_risk"
	filter_liquidity = "filter.liquidity"
	filter_avoid_gap = "filter.avoid_gap"
	filter_avoid_limitup = "filter.avoid_high_limitup"

	# Exit
	exit_take_profit = "exit.take_profit"
	exit_stop_loss = "exit.stop_loss"
	exit_time_stop = "exit.time_stop"
	exit_invalidation = "exit.invalidation"

	# Scaling
	scale_in = "scale.in"
	scale_out = "scale.out"
	pyramid_allow = "pyramid.allow"
	averaging_down_allow = "averaging_down.allow"

	# Sizing & Risk
	sizing_base_pct = "sizing.base_pct"
	sizing_max_pct = "sizing.max_pct"
	sizing_concentration = "sizing.concentration"
	risk_max_drawdown = "risk.max_drawdown"
	risk_daily_loss_limit = "risk.daily_loss_limit"
	risk_no_trade_conditions = "risk.no_trade_conditions"

	# Universe
	universe_instruments = "universe.instruments"
	universe_sectors_bias = "universe.sectors_bias"
	universe_symbol_blacklist = "universe.symbol_blacklist"


# 用于文档/校验/聚合的“分类字典”
CLAIM_KEY_CATALOG: dict[str, list[ClaimKey]] = {
	"entry": [
		ClaimKey.entry_trigger,
		ClaimKey.entry_confirmation,
		ClaimKey.entry_timing,
		ClaimKey.entry_price_type,
	],
	"filters": [
		ClaimKey.filter_market_regime,
		ClaimKey.filter_volatility,
		ClaimKey.filter_event_risk,
		ClaimKey.filter_liquidity,
		ClaimKey.filter_avoid_gap,
		ClaimKey.filter_avoid_limitup,
	],
	"exit": [
		ClaimKey.exit_take_profit,
		ClaimKey.exit_stop_loss,
		ClaimKey.exit_time_stop,
		ClaimKey.exit_invalidation,
	],
	"scaling": [
		ClaimKey.scale_in,
		ClaimKey.scale_out,
		ClaimKey.pyramid_allow,
		ClaimKey.averaging_down_allow,
	],
	"risk": [
		ClaimKey.sizing_base_pct,
		ClaimKey.sizing_max_pct,
		ClaimKey.sizing_concentration,
		ClaimKey.risk_max_drawdown,
		ClaimKey.risk_daily_loss_limit,
		ClaimKey.risk_no_trade_conditions,
	],
	"universe": [
		ClaimKey.universe_instruments,
		ClaimKey.universe_sectors_bias,
		ClaimKey.universe_symbol_blacklist,
	],
}
