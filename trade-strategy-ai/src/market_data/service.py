from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.common.utils import ensure_dir


def _safe_symbol_key(symbol: str) -> str:
    """Map a raw symbol into a filesystem-safe cache key."""
    return symbol.replace("/", "_").replace(".", "_").replace(":", "_")


class MarketDataCache:
    """Filesystem cache for normalized market data frames.

    保留用于 build-market-state CLI 命令的 CSV fallback。
    Agent 侧 price 查询已迁移到 ohlcv_bars 表。
    """

    def __init__(self, cache_dir: Path) -> None:
        """Store the base directory used for cached CSV snapshots."""
        self.cache_dir = cache_dir

    def path_for_symbol(self, symbol: str) -> Path:
        """Return the canonical cache file path for one symbol."""
        return self.cache_dir / f"{_safe_symbol_key(symbol)}_daily.csv"

    def write_daily_frame(self, *, symbol: str, df: pd.DataFrame, source: str) -> Path:
        """Persist one normalized daily frame to disk."""
        if df.empty:
            raise ValueError(f"Cannot cache empty market data frame for {symbol}")
        if "date" not in df.columns or "close" not in df.columns:
            raise ValueError(f"Market data frame must contain date and close columns: {list(df.columns)}")

        out = df.copy()
        if "symbol" not in out.columns:
            out["symbol"] = symbol
        if "market" not in out.columns:
            out["market"] = "CN"
        if "timeframe" not in out.columns:
            out["timeframe"] = "1d"
        if "source" not in out.columns:
            out["source"] = source

        out.sort_values("date", inplace=True)
        path = self.path_for_symbol(symbol)
        ensure_dir(path.parent)
        out.to_csv(path, index=False)
        return path

    def load_daily_frame(self, symbol: str) -> pd.DataFrame:
        """Load a cached daily frame back into a DataFrame."""
        path = self.path_for_symbol(symbol)
        if not path.exists():
            raise FileNotFoundError(path)
        return pd.read_csv(path, parse_dates=["date"])

    def latest_close(self, symbol: str) -> float | None:
        """Read the most recent close from the cached daily CSV."""
        path = self.path_for_symbol(symbol)
        if not path.exists():
            return None
        df = pd.read_csv(path)
        if df.empty or "close" not in df.columns:
            return None
        closes = df["close"].dropna()
        if closes.empty:
            return None
        return float(closes.iloc[-1])
