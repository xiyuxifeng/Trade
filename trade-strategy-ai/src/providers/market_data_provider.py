from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from src.providers.base import ProviderBase, ProviderError


def _to_date(value: Any) -> date | None:
    """把字符串或日期值统一转换为 `date`。"""

    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _scalar_or_none(value: Any) -> Any:
    """把 DataFrame 单元格值转换为普通 Python 标量。"""

    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            return value
    return value


class MarketDataProvider(ProviderBase):
    """基础行情 provider。

    作用：
    - 统一输出日线行情 `ohlcv_1d`
    - 兼容直接返回 DataFrame 的 backend
    - 也兼容已有 `MarketDataSyncService` / cache 读写链路
    """

    _SUPPORTED_CAPABILITIES = {"ohlcv_1d", "market_data"}

    def __init__(self, *, backend: Any, provider_name: str = "market_data") -> None:
        super().__init__(provider_name=provider_name)
        self.backend = backend

    def request(self, *, capability: str, **kwargs: Any) -> dict[str, Any]:
        """拉取基础行情原始数据。"""

        if capability not in self._SUPPORTED_CAPABILITIES:
            self.unsupported(capability)

        symbol = kwargs.get("symbol")
        if not symbol:
            raise ProviderError("symbol is required")

        market_kind = str(kwargs.get("market_kind") or "stock")
        adjust = str(kwargs.get("adjust") or "")
        start_date = _to_date(kwargs.get("start_date"))
        end_date = _to_date(kwargs.get("end_date"))

        frame = self._fetch_frame(
            symbol=symbol,
            market_kind=market_kind,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

        if frame is None or frame.empty:
            raise ProviderError(f"market data frame is empty for symbol: {symbol}")

        return {
            "symbol": symbol,
            "market_kind": market_kind,
            "adjust": adjust,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "frame": frame,
        }

    def normalize(
        self,
        *,
        capability: str,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """把行情 DataFrame 归一成 `ohlcv_1d` bars 列表。"""

        if capability not in self._SUPPORTED_CAPABILITIES:
            self.unsupported(capability)

        frame = raw.get("frame")
        if not isinstance(frame, pd.DataFrame):
            raise ProviderError("market data backend must return a pandas DataFrame")
        if frame.empty:
            raise ProviderError("market data frame is empty")
        if "date" not in frame.columns or "close" not in frame.columns:
            raise ProviderError("market data frame must contain date and close columns")

        normalized = frame.copy()
        normalized.sort_values("date", inplace=True)

        bars: list[dict[str, Any]] = []
        for _, row in normalized.iterrows():
            close = _scalar_or_none(row.get("close"))
            bars.append(
                {
                    "date": pd.to_datetime(row.get("date")).date().isoformat(),
                    "open": _scalar_or_none(row.get("open", close)),
                    "high": _scalar_or_none(row.get("high", close)),
                    "low": _scalar_or_none(row.get("low", close)),
                    "close": close,
                    "volume": _scalar_or_none(row.get("volume")),
                    "turnover": _scalar_or_none(row.get("turnover")),
                }
            )

        payload = {
            "dataset": "ohlcv_1d",
            "symbol": raw.get("symbol") or (request or {}).get("symbol"),
            "market_kind": raw.get("market_kind") or (request or {}).get("market_kind") or "stock",
            "timeframe": "1d",
            "rows": len(bars),
            "bars": bars,
        }
        source = raw.get("source")
        if source is not None:
            payload["source"] = source
        return payload

    def _fetch_frame(
        self,
        *,
        symbol: str,
        market_kind: str,
        start_date: date | None,
        end_date: date | None,
        adjust: str,
    ) -> pd.DataFrame | None:
        """从 backend 读取行情 DataFrame，兼容多种实现。"""

        if hasattr(self.backend, "fetch_ohlcv_1d"):
            return self.backend.fetch_ohlcv_1d(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                market_kind=market_kind,
                adjust=adjust,
            )

        sync_method_name = {
            "stock": "sync_symbol",
            "index": "sync_index",
            "industry_board": "sync_industry_board",
            "concept_board": "sync_concept_board",
        }.get(market_kind)
        if sync_method_name and hasattr(self.backend, sync_method_name):
            sync_method = getattr(self.backend, sync_method_name)
            sync_result = sync_method(symbol, start_date=start_date, end_date=end_date, adjust=adjust)
            cache_path = getattr(sync_result, "cache_path", None)
            if cache_path is not None:
                return pd.read_csv(cache_path, parse_dates=["date"])
            synced_symbol = getattr(sync_result, "symbol", symbol)
            cache = getattr(self.backend, "cache", None)
            if cache is not None and hasattr(cache, "load_daily_frame"):
                return cache.load_daily_frame(synced_symbol)

        if hasattr(self.backend, "load_daily_frame"):
            return self.backend.load_daily_frame(symbol)

        raise ProviderError("backend does not support ohlcv_1d retrieval")
