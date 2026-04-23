"""OHLCV 拉取 skill（NTL-S2-016）。

DataAgent skill，支持返回日线行情数据。
当 DataRequest.fields 包含 "ohlcv_1d" 时触发。
"""
from __future__ import annotations

from datetime import date
from typing import Any


def supported_fields() -> list[str]:
    """该 skill 支持的字段列表。"""
    return ["ohlcv_1d"]


def to_payload(
    *,
    symbols: list[str],
    dataset: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    provider: Any = None,
) -> dict[str, Any]:
    """从 provider 获取日线行情并构建 payload。

    Args:
        symbols: 股票代码列表
        dataset: 数据集标识，传入 "ohlcv_1d" 时触发本 skill
        start_date: 开始日期，默认 None（使用 provider 决定）
        end_date: 结束日期，默认 None（使用 provider 决定）
        provider: MarketDataProvider 实例，若为 None 则返回空

    Returns:
        包含 ohlcv_1d 的 DataAgent payload 片段
    """
    if dataset != "ohlcv_1d" and "ohlcv_1d" not in (dataset or ""):
        return {}

    if provider is None or not symbols:
        return {"ohlcv_1d": {}}

    result: dict[str, Any] = {}

    try:
        if hasattr(provider, "fetch_ohlcv"):
            raw_result = provider.fetch_ohlcv(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
            )
            if isinstance(raw_result, dict):
                result = raw_result
        elif hasattr(provider, "market_data_provider"):
            # provider 是 Wrapper，包含 market_data_provider
            mdp = provider.market_data_provider
            if hasattr(mdp, "fetch_ohlcv"):
                raw_result = mdp.fetch_ohlcv(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                )
                if isinstance(raw_result, dict):
                    result = raw_result
    except Exception:  # noqa: BLE001
        return {"ohlcv_1d": {}}

    return {"ohlcv_1d": result}