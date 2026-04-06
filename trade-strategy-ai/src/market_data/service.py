from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.akshare_tool import AkshareDailyRequest, AkshareMarketDataTool
from src.common.utils import ensure_dir
from src.models.market_data import MarketData
from src.pipeline.validation import DataValidator, ValidationIssue


def _safe_symbol_key(symbol: str) -> str:
    """Map a raw symbol into a filesystem-safe cache key."""
    return symbol.replace("/", "_").replace(".", "_").replace(":", "_")


def _to_utc_datetime(value: Any) -> datetime:
    """Normalize date-like values to an aware UTC datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    dt = pd.to_datetime(value)
    if isinstance(dt, pd.Timestamp):
        py_dt = dt.to_pydatetime()
        return py_dt if py_dt.tzinfo is not None else py_dt.replace(tzinfo=UTC)
    if isinstance(dt, date):
        return datetime.combine(dt, time.min, tzinfo=UTC)
    return datetime.fromisoformat(str(value)).replace(tzinfo=UTC)


def _decimal_or_zero(value: Any) -> Decimal:
    """Convert missing numeric values to Decimal(0)."""
    if value is None or pd.isna(value):
        return Decimal("0")
    return Decimal(str(value))


def _decimal_or_fallback(value: Any, fallback: Any) -> Decimal:
    """Use the fallback value when the primary numeric field is absent."""
    if value is None or pd.isna(value):
        return _decimal_or_zero(fallback)
    return Decimal(str(value))


@dataclass(frozen=True)
class MarketDataSyncResult:
    """Summary of a single sync job, used by CLI output and tests."""

    symbol: str
    cache_path: Path
    rows_written: int
    latest_close: float | None
    source: str
    validation_issues: list[ValidationIssue] = field(default_factory=list)


class MarketDataCache:
    """Filesystem cache for normalized market data frames."""

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


class MarketDataSyncService:
    """Sync AkShare market data into cache files and validate each daily row."""

    def __init__(
        self,
        *,
        cache_dir: Path,
        tool: AkshareMarketDataTool | None = None,
        validator: DataValidator | None = None,
    ) -> None:
        self.cache = MarketDataCache(cache_dir=cache_dir)
        self.tool = tool or AkshareMarketDataTool()
        self.validator = validator or DataValidator()

    def _fetch_daily_frame(
        self,
        *,
        symbol: str,
        request_symbol: str | None = None,
        market_kind: str = "stock",
        start_date: date | None = None,
        end_date: date | None = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        """Dispatch to the right AkShare endpoint for a market kind."""
        req = AkshareDailyRequest(
            symbol=request_symbol or symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        if market_kind == "index":
            return self.tool.fetch_index_daily_em(req)
        if market_kind == "industry_board":
            return self.tool.fetch_board_industry_hist_em(req)
        if market_kind == "concept_board":
            return self.tool.fetch_board_concept_hist_em(req)
        if symbol.startswith(("51", "52", "56", "58", "15")):
            return self.tool.fetch_etf_daily_em(req)
        return self.tool.fetch_stock_daily_a(req)

    def _sync_frame(
        self,
        symbol: str,
        *,
        request_symbol: str | None = None,
        market_kind: str = "stock",
        start_date: date | None = None,
        end_date: date | None = None,
        adjust: str = "",
        source: str = "akshare",
    ) -> MarketDataSyncResult:
        """Fetch, cache, and validate one market data series."""
        frame = self._fetch_daily_frame(
            symbol=symbol,
            request_symbol=request_symbol,
            market_kind=market_kind,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        cache_path = self.cache.write_daily_frame(symbol=symbol, df=frame, source=source)
        validation_issues: list[ValidationIssue] = []
        previous_close: Decimal | None = None
        for _, row in frame.sort_values("date").iterrows():
            traded_at = _to_utc_datetime(row["date"])
            record = MarketData(
                source=source,
                symbol=symbol,
                market=str(row.get("market") or "CN"),
                timeframe=str(row.get("timeframe") or "1d"),
                traded_at=traded_at,
                open=_decimal_or_fallback(row.get("open"), row.get("close")),
                high=_decimal_or_fallback(row.get("high"), row.get("close")),
                low=_decimal_or_fallback(row.get("low"), row.get("close")),
                close=_decimal_or_zero(row.get("close")),
                volume=_decimal_or_zero(row.get("volume")),
                turnover=_decimal_or_zero(row.get("turnover")),
                adj_factor=None,
                is_adjusted=False,
                indicators={},
                raw_payload=row.to_dict(),
            )
            vr = self.validator.validate_market_record(record, previous_close=previous_close)
            validation_issues.extend(vr.issues)
            previous_close = Decimal(record.close)

        latest_close = self.cache.latest_close(symbol)
        return MarketDataSyncResult(
            symbol=symbol,
            cache_path=cache_path,
            rows_written=len(frame),
            latest_close=latest_close,
            source=source,
            validation_issues=validation_issues,
        )

    def sync_symbol(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        adjust: str = "",
    ) -> MarketDataSyncResult:
        """Sync a single stock or ETF symbol into cache."""

        return self._sync_frame(symbol, start_date=start_date, end_date=end_date, adjust=adjust, source="akshare")

    def sync_index(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MarketDataSyncResult:
        """Sync a mainland index into cache."""

        return self._sync_frame(
            symbol,
            market_kind="index",
            start_date=start_date,
            end_date=end_date,
            source="akshare.index",
        )

    def sync_industry_board(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MarketDataSyncResult:
        """Sync an industry board into cache with a distinct cache key."""

        return self._sync_frame(
            f"industry:{symbol}",
            request_symbol=symbol,
            market_kind="industry_board",
            start_date=start_date,
            end_date=end_date,
            source="akshare.board.industry",
        )

    def sync_concept_board(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MarketDataSyncResult:
        """Sync a concept board into cache with a distinct cache key."""

        return self._sync_frame(
            f"concept:{symbol}",
            request_symbol=symbol,
            market_kind="concept_board",
            start_date=start_date,
            end_date=end_date,
            source="akshare.board.concept",
        )

    def sync_symbols(
        self,
        *,
        symbols: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
        adjust: str = "",
    ) -> list[MarketDataSyncResult]:
        """Sync multiple stock/ETF symbols."""

        return [
            self.sync_symbol(symbol, start_date=start_date, end_date=end_date, adjust=adjust)
            for symbol in symbols
        ]
