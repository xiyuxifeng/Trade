"""基础行情 skill（NTL-S2-019）。

DataAgent skill，支持返回最新价格（last_price）。
当 DataRequest.dataset="last_price" 或无 dataset 且 fields 包含 "last_price" 时触发。

职责边界（NTL-S2-019）：
- 本 skill 仅负责 last_price 字段
- 不承担 hot_topics / topic_constituents / strong_symbols 等新数据集
- 保留用于 Phase 0 兼容路径（无 dataset 时的 fallback）

数据来源优先级：
1. mock_prices 配置（测试/本地环境）
2. market_data_cache_dir 中的缓存日线数据
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.market_data.service import MarketDataCache


def get_last_price_from_mock_prices(*, symbol: str, mock_prices: dict[str, float]) -> float | None:
    """从 mock 配置中返回模拟价格。"""
    return mock_prices.get(symbol)


def get_last_price_from_cache(*, symbol: str, market_data_cache_dir: str | Path | None) -> float | None:
    """从缓存日线数据中读取最近收盘价作为 fallback。"""
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
    """从 mock 配置优先解析价格，失败后读缓存。"""
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
    """本 skill 支持的字段列表。"""
    return ["last_price"]


def to_payload(
    *,
    symbols: list[str],
    fields: list[str],
    mock_prices: dict[str, float],
    market_data_cache_dir: str | Path | None = None,
) -> dict[str, Any]:
    """构建 last_price payload。

    Args:
        symbols: 股票代码列表
        fields: 请求字段列表（本 skill 只处理 last_price）
        mock_prices: mock 价格配置
        market_data_cache_dir: 行情缓存目录

    Returns:
        包含 last_price 的 DataAgent payload 片段
    """
    payload: dict[str, Any] = {"symbols": symbols, "fields": fields}
    if "last_price" in fields:
        payload["last_price"] = batch_get_last_prices(
            symbols=symbols,
            mock_prices=mock_prices,
            market_data_cache_dir=market_data_cache_dir,
        )
    return payload