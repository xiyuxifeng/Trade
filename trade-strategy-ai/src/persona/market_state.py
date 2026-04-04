from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from src.persona.schemas import MarketRegime, MarketState, VolatilityLevel


@dataclass(frozen=True)
class DailySeriesSource:
	"""Local daily OHLCV source for MarketState classification (Phase 0.5/1).

	We intentionally start with a CSV-based source to keep dependencies minimal.
	"""

	symbol: str
	csv_path: Path
	date_col: str = "date"
	close_col: str = "close"
	volume_col: str | None = "volume"


def _to_date(x) -> date:
	if isinstance(x, date):
		return x
	return pd.to_datetime(x).date()  # type: ignore[no-any-return]


def load_daily_close_series(source: DailySeriesSource) -> pd.DataFrame:
	"""Load daily data as a DataFrame with normalized columns: date, close.

	CSV requirements (minimum): date, close
	"""

	df = pd.read_csv(source.csv_path)
	if source.date_col not in df.columns or source.close_col not in df.columns:
		raise ValueError(
			f"CSV missing required columns: {source.date_col}, {source.close_col}. got={list(df.columns)}"
		)

	df = df[[source.date_col, source.close_col] + ([source.volume_col] if source.volume_col and source.volume_col in df.columns else [])].copy()
	df.rename(columns={source.date_col: "date", source.close_col: "close"}, inplace=True)
	if source.volume_col and source.volume_col in df.columns:
		df.rename(columns={source.volume_col: "volume"}, inplace=True)

	df["date"] = df["date"].map(_to_date)
	df["close"] = df["close"].astype(float)

	df.sort_values("date", inplace=True)
	df.dropna(subset=["date", "close"], inplace=True)
	return df


def classify_market_state(*, as_of_date: date, daily_df: pd.DataFrame, symbol: str | None = None) -> MarketState:
	"""Classify regime/vol using simple, explainable daily rules.

	This is intentionally heuristic (Phase 0.5): stable + easy to tune.
	"""

	df = daily_df.copy()
	df = df[df["date"] <= as_of_date]
	if len(df) < 30:
		return MarketState(as_of_date=as_of_date, features={"reason": "insufficient_history"})

	df["ret1"] = df["close"].pct_change()
	df["ma20"] = df["close"].rolling(20).mean()
	df["ma60"] = df["close"].rolling(60).mean()
	df["vol20"] = df["ret1"].rolling(20).std()

	row = df.iloc[-1]
	close = float(row["close"])
	ma20 = float(row["ma20"]) if pd.notna(row["ma20"]) else close
	ma60 = float(row["ma60"]) if pd.notna(row["ma60"]) else close
	vol20 = float(row["vol20"]) if pd.notna(row["vol20"]) else 0.0

	# Volatility buckets by rolling percentile within last ~252 days
	lookback = df.tail(252)
	vol_series = lookback["vol20"].dropna()
	if len(vol_series) >= 30:
		p33 = float(vol_series.quantile(0.33))
		p66 = float(vol_series.quantile(0.66))
		if vol20 <= p33:
			vol_level = VolatilityLevel.low
		elif vol20 >= p66:
			vol_level = VolatilityLevel.high
		else:
			vol_level = VolatilityLevel.mid
	else:
		vol_level = VolatilityLevel.unknown

	# Trend direction heuristics
	ma20_prev = float(df.iloc[-2]["ma20"]) if pd.notna(df.iloc[-2]["ma20"]) else ma20
	ma20_rising = ma20 >= ma20_prev

	trend_up = close > ma20 > ma60 and ma20_rising
	trend_down = close < ma20 < ma60 and (not ma20_rising)

	# Shock heuristics (proxy): 5-day move
	ret5 = float(df["close"].pct_change(5).iloc[-1]) if len(df) >= 6 else 0.0

	regime = MarketRegime.range
	if trend_up:
		regime = MarketRegime.trend_up
	elif trend_down:
		regime = MarketRegime.trend_down

	# panic/euphoria override when volatility is high
	if vol_level == VolatilityLevel.high:
		if ret5 <= -0.07:
			regime = MarketRegime.panic
		elif ret5 >= 0.07:
			regime = MarketRegime.euphoria

	features = {
		"symbol": symbol,
		"close": close,
		"ma20": ma20,
		"ma60": ma60,
		"ma20_rising": bool(ma20_rising),
		"ret5": ret5,
		"vol20": vol20,
		"vol_level": vol_level.value,
	}

	return MarketState(
		as_of_date=as_of_date,
		scope="market",
		regime=regime,
		volatility=vol_level,
		features=features,
	)
