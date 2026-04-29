"""基础行情 skill（NTL-S2-019）。

DataAgent skill，支持返回最新价格（last_price）。
当 DataRequest.dataset="last_price" 或无 dataset 且 fields 包含 "last_price" 时触发。

职责边界（NTL-S2-019）：
- 本 skill 仅负责 last_price 字段
- 不承担 hot_topics / topic_constituents / strong_symbols 等新数据集
- 保留用于 Phase 0 兼容路径（无 dataset 时的 fallback）

数据来源优先级：
1. mock_prices 配置（测试/本地环境）
2. ohlcv_bars 表（数据库）
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.db.session import get_session_factory
from src.market_data.ohlcv_service import OHLCVService


def get_last_price_from_mock_prices(*, symbol: str, mock_prices: dict[str, float]) -> float | None:
    """从 mock 配置中返回模拟价格。"""
    return mock_prices.get(symbol)


async def get_last_price_from_db(*, symbol: str) -> float | None:
    """从 ohlcv_bars 表读取最近收盘价作为 fallback。"""
    factory = get_session_factory()
    service = OHLCVService(session_factory=factory)
    return await service.get_latest_close(symbol)


async def batch_get_last_prices_async(
    *,
    symbols: list[str],
    mock_prices: dict[str, float],
) -> dict[str, float]:
    """从 mock 配置优先解析价格，失败后并发查 ohlcv_bars 表。"""
    import asyncio

    async def get_price_for_symbol(s: str) -> tuple[str, float] | None:
        v = mock_prices.get(s)
        if v is not None:
            return (s, float(v))
        db_price = await get_last_price_from_db(symbol=s)
        if db_price is not None:
            return (s, float(db_price))
        return None

    results = await asyncio.gather(*[get_price_for_symbol(s) for s in symbols])
    return {s: price for item in results if item is not None for s, price in [item]}


def batch_get_last_prices(
    *,
    symbols: list[str],
    mock_prices: dict[str, float],
    market_data_cache_dir: str | Path | None = None,
) -> dict[str, float]:
    """同步版本，内部调用异步版本。兼容现有同步调用方。"""
    import asyncio
    return asyncio.run(batch_get_last_prices_async(symbols=symbols, mock_prices=mock_prices))


def supported_fields() -> list[str]:
    """本 skill 支持的字段列表。"""
    return ["last_price"]


async def to_payload(
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
        market_data_cache_dir: 行情缓存目录（已废弃，保留参数兼容性）

    Returns:
        包含 last_price 的 DataAgent payload 片段
    """
    payload: dict[str, Any] = {"symbols": symbols, "fields": fields}
    if "last_price" in fields:
        payload["last_price"] = await batch_get_last_prices_async(
            symbols=symbols,
            mock_prices=mock_prices,
        )
    return payload