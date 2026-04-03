from __future__ import annotations

from typing import Any


def get_last_price_from_mock_prices(*, symbol: str, mock_prices: dict[str, float]) -> float | None:
	return mock_prices.get(symbol)


def batch_get_last_prices(*, symbols: list[str], mock_prices: dict[str, float]) -> dict[str, float]:
	result: dict[str, float] = {}
	for s in symbols:
		v = mock_prices.get(s)
		if v is not None:
			result[s] = float(v)
	return result


def supported_fields() -> list[str]:
	return ["last_price"]


def to_payload(*, symbols: list[str], fields: list[str], mock_prices: dict[str, float]) -> dict[str, Any]:
	payload: dict[str, Any] = {"symbols": symbols, "fields": fields}
	if "last_price" in fields:
		payload["last_price"] = batch_get_last_prices(symbols=symbols, mock_prices=mock_prices)
	return payload
