from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


def _normalize_cn_symbol(symbol: str) -> str:
	"""Normalize `510300.SH` -> `510300` for AkShare EM endpoints."""
	return symbol.split(".")[0].strip()


def _to_yyyymmdd(d: date) -> str:
	return d.strftime("%Y%m%d")


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
	for c in candidates:
		if c in df.columns:
			return c
	return None


@dataclass(frozen=True)
class AkshareDailyRequest:
	symbol: str
	start_date: date | None = None
	end_date: date | None = None
	adjust: str = ""  # no adjust by default


class AkshareMarketDataTool:
	"""AkShare market data helper.

	Design goals:
	- Small, reusable wrapper around AkShare
	- Normalize output columns to English: date, open, high, low, close, volume
	- Provide a stable CSV export for downstream steps (MarketState, caching, etc.)
	"""

	def __init__(self) -> None:
		try:
			import akshare as ak  # type: ignore
		except Exception as exc:  # noqa: BLE001
			raise RuntimeError(
				"AkShare is not available. Install dependencies with: pip install -e trade-strategy-ai"
			) from exc
		self._ak = ak

	def fetch_etf_daily_em(self, req: AkshareDailyRequest) -> pd.DataFrame:
		"""Fetch ETF daily history via Eastmoney endpoint.

		Returns a DataFrame with columns: date, open, high, low, close, volume (volume optional).
		"""

		symbol = _normalize_cn_symbol(req.symbol)
		kwargs: dict[str, Any] = {
			"symbol": symbol,
			"period": "daily",
			"adjust": req.adjust,
		}
		if req.start_date:
			kwargs["start_date"] = _to_yyyymmdd(req.start_date)
		if req.end_date:
			kwargs["end_date"] = _to_yyyymmdd(req.end_date)

		# AkShare API may evolve; keep this isolated.
		df = self._ak.fund_etf_hist_em(**kwargs)
		if df is None or df.empty:
			raise ValueError(f"AkShare returned empty ETF daily data: {req.symbol}")

		date_col = _pick_col(df, ["日期", "date", "交易日期"]) or "日期"
		open_col = _pick_col(df, ["开盘", "open"])
		high_col = _pick_col(df, ["最高", "high"])
		low_col = _pick_col(df, ["最低", "low"])
		close_col = _pick_col(df, ["收盘", "close"])
		vol_col = _pick_col(df, ["成交量", "volume"])

		out = pd.DataFrame()
		out["date"] = pd.to_datetime(df[date_col]).dt.date
		if open_col:
			out["open"] = pd.to_numeric(df[open_col], errors="coerce")
		if high_col:
			out["high"] = pd.to_numeric(df[high_col], errors="coerce")
		if low_col:
			out["low"] = pd.to_numeric(df[low_col], errors="coerce")
		if close_col:
			out["close"] = pd.to_numeric(df[close_col], errors="coerce")
		else:
			raise ValueError("Unable to find close column from AkShare ETF data")
		if vol_col:
			out["volume"] = pd.to_numeric(df[vol_col], errors="coerce")

		out.dropna(subset=["date", "close"], inplace=True)
		out.sort_values("date", inplace=True)
		return out

	def write_daily_csv(self, *, df: pd.DataFrame, dest_path: str | Path) -> Path:
		p = Path(dest_path)
		p.parent.mkdir(parents=True, exist_ok=True)
		df.to_csv(p, index=False)
		return p
