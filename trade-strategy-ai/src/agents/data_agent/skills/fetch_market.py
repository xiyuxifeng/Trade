from __future__ import annotations

from pathlib import Path
from typing import Any

from src.market_data.service import MarketDataCache


def get_last_price_from_mock_prices(*, symbol: str, mock_prices: dict[str, float]) -> float | None:
    """Return a mocked last price for tests and local runs."""
    return mock_prices.get(symbol)


def get_last_price_from_cache(*, symbol: str, market_data_cache_dir: str | Path | None) -> float | None:
    """Read the last cached close as a fallback market price."""
    if not market_data_cache_dir:
        return None
    cache = MarketDataCache(Path(market_data_cache_dir))
    return cache.latest_close(symbol)


def batch_get_last_prices(
	*,
	symbols: list[str],
	mock_prices: dict[str, float],
	market_data_cache_dir: str | Path | None = None,
) -> dict[str, float]:
    """Resolve last prices from mock config first, then market cache."""
    result: dict[str, float] = {}
    cache = MarketDataCache(Path(market_data_cache_dir)) if market_data_cache_dir else None
    for s in symbols:
        v = mock_prices.get(s)
        if v is not None:
            result[s] = float(v)
            continue
        if cache is not None:
            cached = cache.latest_close(s)
            if cached is not None:
                result[s] = float(cached)
    return result


def supported_fields() -> list[str]:
    return ["last_price"]


def to_payload(
	*,
	symbols: list[str],
	fields: list[str],
	mock_prices: dict[str, float],
	market_data_cache_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build the DataAgent payload for supported market fields."""
    payload: dict[str, Any] = {"symbols": symbols, "fields": fields}
    if "last_price" in fields:
        payload["last_price"] = batch_get_last_prices(
            symbols=symbols,
            mock_prices=mock_prices,
            market_data_cache_dir=market_data_cache_dir,
        )
    return payload
