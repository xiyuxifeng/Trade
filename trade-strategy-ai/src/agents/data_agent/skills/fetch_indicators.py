"""指标拉取 skill（NTL-S2-017）。

DataAgent skill，支持返回技术指标数据（RSI、MACD、Bollinger、ATR、Stochastic 等）。
当 DataRequest.fields 包含 "indicators" 时触发。

底层使用 PatternFeatureEngine 计算指标。
"""

from __future__ import annotations

from datetime import date
from typing import Any


def supported_fields() -> list[str]:
    """该 skill 支持的字段列表。"""
    return ["indicators"]


def to_payload(
    *,
    symbols: list[str],
    dataset: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    provider: Any = None,
) -> dict[str, Any]:
    """从 provider 获取 OHLCV 数据并计算技术指标。

    Args:
        symbols: 股票代码列表
        dataset: 数据集标识，传入 "indicators" 时触发本 skill
        start_date: 开始日期（传入 fetch_ohlcv）
        end_date: 结束日期（传入 fetch_ohlcv）
        provider: MarketDataProvider 实例，若为 None 则返回空

    Returns:
        包含 indicators 的 DataAgent payload 片段
    """
    if dataset != "indicators" and "indicators" not in (dataset or ""):
        return {}

    if provider is None or not symbols:
        return {"indicators": {}}

    # 从 provider 获取 OHLCV 数据
    ohlcv_data: dict[str, list[dict[str, Any]]] = {}
    try:
        if hasattr(provider, "fetch_ohlcv"):
            raw = provider.fetch_ohlcv(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
            )
            if isinstance(raw, dict):
                ohlcv_data = raw
        elif hasattr(provider, "market_data_provider"):
            mdp = provider.market_data_provider
            if hasattr(mdp, "fetch_ohlcv"):
                raw = mdp.fetch_ohlcv(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                )
                if isinstance(raw, dict):
                    ohlcv_data = raw
    except Exception:  # noqa: BLE001
        return {"indicators": {}}

    # 计算指标
    result: dict[str, Any] = {}
    for symbol, bars in ohlcv_data.items():
        if not bars:
            continue
        # 转换为 PatternFeatureEngine 所需格式（只保留 OHLCV 必要字段）
        ohlcv_bars = [
            {
                "open": float(b.get("open", 0)),
                "high": float(b.get("high", 0)),
                "low": float(b.get("low", 0)),
                "close": float(b.get("close", 0)),
                "volume": float(b.get("volume", 0)),
            }
            for b in bars
            if isinstance(b, dict)
        ]
        if not ohlcv_bars:
            continue

        try:
            from src.indicators.pattern_features import PatternFeatureEngine

            engine = PatternFeatureEngine(ohlcv_bars)
            features = engine.compute_all()
            result[symbol] = {
                "rsi": features.rsi,
                "macd_histogram": features.macd_histogram,
                "bb_width": features.bb_width,
                "cci": features.cci,
                "ma50": features.ma50,
                "ma200": features.ma200,
                "volume_ratio": features.volume_ratio,
                "price_vs_ma": features.price_vs_ma,
                "atr_ratio": features.atr_ratio,
                "close_position": features.close_position,
            }
        except Exception:  # noqa: BLE001
            continue

    return {"indicators": result}
