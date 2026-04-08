"""
特征计算脚本 — P2-015。

将 OHLCV 数据转换为特征向量，支持 Pandas/Polars 两种数据格式。

特征维度：
  - 技术指标：RSI, MACD, Bollinger, Stochastic, CCI, MA
  - 价量特征：收盘价/MA、MA斜率、成交量比、振幅
  - 形态特征：gap_ratio, close_position, breakout_ratio
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np

from src.indicators.engine import (
    atr as compute_atr,
    bollinger,
    ema,
    macd,
    rsi,
    sma,
    stochastic,
)


@dataclass
class DailyBars:
    """日线数据容器。

    支持列表格式（用于纯 Python 计算）和 DataFrame 格式（用于 Pandas/Polars）。

    Attributes:
        symbol: 股票代码
        dates: 日期列表
        opens: 开盘价列表
        highs: 最高价列表
        lows: 最低价列表
        closes: 收盘价列表
        volumes: 成交量列表
    """
    symbol: str
    dates: list[date] = field(default_factory=list)
    opens: list[float] = field(default_factory=list)
    highs: list[float] = field(default_factory=list)
    lows: list[float] = field(default_factory=list)
    closes: list[float] = field(default_factory=list)
    volumes: list[float] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.dates)

    def _to_arrays(self) -> tuple[np.ndarray, ...]:
        """转换为 numpy 数组。"""
        return (
            np.array(self.opens, dtype=np.float64),
            np.array(self.highs, dtype=np.float64),
            np.array(self.lows, dtype=np.float64),
            np.array(self.closes, dtype=np.float64),
            np.array(self.volumes, dtype=np.float64),
        )


@dataclass
class FeatureVector:
    """特征向量 dataclass。

    包含所有计算得到的特征值。
    """
    # === 基础价量特征 ===
    # 收盘价 / MA20
    price_vs_ma20: float | None = None
    # 收盘价 / MA50
    price_vs_ma50: float | None = None
    # MA5 斜率（相对于 MA20）
    ma_slope: float | None = None
    # 成交量 / 20日均量
    volume_ratio: float | None = None
    # 跳空比率（今日开盘 vs 昨日收盘）
    gap_ratio: float | None = None
    # 收盘在当日振幅中的位置（0=低点，1=高点）
    close_position: float | None = None
    # 突破日高点比率
    high_breakout_ratio: float | None = None
    # 跌破日低点比率
    low_breakout_ratio: float | None = None
    # 最近5日价格波动率（std/mean）
    price_volatility: float | None = None
    # ATR / 收盘价
    atr_ratio: float | None = None

    # === 技术指标 ===
    rsi: float | None = None
    stochastic_k: float | None = None
    stochastic_d: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    bollinger_upper: float | None = None
    bollinger_middle: float | None = None
    bollinger_lower: float | None = None
    cci: float | None = None
    ma20: float | None = None
    ma50: float | None = None
    atr: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {k: v for k, v in self.__dict__.items() if v is not None or k == "rsi"}

    def to_array(self) -> np.ndarray:
        """转换为 numpy 数组（用于模型输入）。"""
        import statistics

        values = []
        for name, default in [
            ("price_vs_ma20", 1.0),
            ("price_vs_ma50", 1.0),
            ("ma_slope", 0.0),
            ("volume_ratio", 1.0),
            ("gap_ratio", 0.0),
            ("close_position", 0.5),
            ("high_breakout_ratio", 0.0),
            ("low_breakout_ratio", 0.0),
            ("price_volatility", 0.0),
            ("atr_ratio", 0.0),
            ("rsi", 50.0),
            ("stochastic_k", 50.0),
            ("stochastic_d", 50.0),
            ("macd", 0.0),
            ("macd_signal", 0.0),
            ("macd_histogram", 0.0),
            ("bollinger_upper", 0.0),
            ("bollinger_middle", 0.0),
            ("bollinger_lower", 0.0),
            ("cci", 0.0),
            ("ma20", 0.0),
            ("ma50", 0.0),
            ("atr", 0.0),
        ]:
            val = getattr(self, name, None)
            values.append(val if val is not None else default)
        return np.array(values, dtype=np.float64)


def compute_features(bars: DailyBars) -> FeatureVector:
    """计算特征向量（核心函数）。

    基于日线数据计算所有特征值。

    Args:
        bars: DailyBars 日线数据容器

    Returns:
        FeatureVector 特征向量
    """
    n = len(bars)
    if n < 2:
        return FeatureVector()

    opens, highs, lows, closes, volumes = bars._to_arrays()
    result = FeatureVector()

    # === 基础价量特征 ===

    # MA 计算
    if n >= 20:
        ma20_arr = sma(closes, 20)
        ma20_val = ma20_arr[-1] if len(ma20_arr) > 0 and not np.isnan(ma20_arr[-1]) else None
        result.ma20 = ma20_val
        if ma20_val is not None and ma20_val > 0:
            result.price_vs_ma20 = float(closes[-1] / ma20_val)

    if n >= 50:
        ma50_arr = sma(closes, 50)
        ma50_val = ma50_arr[-1] if len(ma50_arr) > 0 and not np.isnan(ma50_arr[-1]) else None
        result.ma50 = ma50_val
        if ma50_val is not None and ma50_val > 0:
            result.price_vs_ma50 = float(closes[-1] / ma50_val)

    # MA 斜率（MA5 最近 5 日均值 vs MA20）
    if n >= 25:
        ma5_arr = sma(closes, 5)
        ma5_val = ma5_arr[-1] if len(ma5_arr) > 0 and not np.isnan(ma5_arr[-1]) else None
        ma20_arr = sma(closes, 20)
        ma20_val = ma20_arr[-1] if len(ma20_arr) > 0 and not np.isnan(ma20_arr[-1]) else None
        if ma5_val is not None and ma20_val is not None and ma20_val != 0:
            result.ma_slope = float((ma5_val - ma20_val) / ma20_val)

    # 成交量比
    if n >= 20:
        avg_volume = np.mean(volumes[-20:])
        if avg_volume > 0:
            result.volume_ratio = float(volumes[-1] / avg_volume)

    # 跳空比率
    if n >= 2:
        prev_close = closes[-2]
        today_open = opens[-1]
        if prev_close > 0:
            result.gap_ratio = float((today_open - prev_close) / prev_close)

    # 收盘位置
    day_range = highs[-1] - lows[-1]
    if day_range > 0:
        result.close_position = float((closes[-1] - lows[-1]) / day_range)
    else:
        result.close_position = 0.5

    # 突破/跌破比率
    if highs[-1] > 0:
        result.high_breakout_ratio = float((closes[-1] - highs[-1]) / highs[-1])
    if lows[-1] > 0:
        result.low_breakout_ratio = float((lows[-1] - closes[-1]) / lows[-1])

    # 价格波动率（最近5日）
    if n >= 5:
        recent_closes = closes[-5:]
        mean_c = np.mean(recent_closes)
        if mean_c > 0:
            std_c = np.std(recent_closes, ddof=0)
            result.price_volatility = float(std_c / mean_c)

    # ATR / 收盘价
    if n >= 15:
        atr_val = compute_atr(highs, lows, closes, 14)
        if not np.isnan(atr_val) and closes[-1] > 0:
            result.atr_ratio = float(atr_val / closes[-1])
            result.atr = float(atr_val)

    # === 技术指标 ===

    # RSI
    if n >= 15:
        rsi_val = rsi(closes, 14)
        if not np.isnan(rsi_val):
            result.rsi = float(rsi_val)

    # Stochastic
    if n >= 14:
        stoch = stochastic(highs, lows, closes, k_window=14, d_window=3)
        if not np.isnan(stoch.k):
            result.stochastic_k = float(stoch.k)
        if not np.isnan(stoch.d):
            result.stochastic_d = float(stoch.d)

    # MACD
    if n >= 26:
        macd_result = macd(closes, fast=12, slow=26, signal=9)
        if not np.isnan(macd_result.macd):
            result.macd = float(macd_result.macd)
        if not np.isnan(macd_result.signal):
            result.macd_signal = float(macd_result.signal)
        if not np.isnan(macd_result.histogram):
            result.macd_histogram = float(macd_result.histogram)

    # Bollinger Bands
    if n >= 20:
        bb = bollinger(closes, window=20, num_std=2.0)
        if not np.isnan(bb.middle):
            result.bollinger_upper = float(bb.upper)
            result.bollinger_middle = float(bb.middle)
            result.bollinger_lower = float(bb.lower)

    # CCI（简化实现）
    if n >= 20:
        typical_prices = (highs + lows + closes) / 3.0
        cci_arr = _cci(typical_prices, 20)
        cci_val = cci_arr[-1] if len(cci_arr) > 0 and not np.isnan(cci_arr[-1]) else None
        if cci_val is not None:
            result.cci = float(cci_val)

    return result


def _cci(typical_prices: np.ndarray, window: int) -> np.ndarray:
    """计算 Commodity Channel Index。

    Args:
        typical_prices: 典型价格（high + low + close）/ 3
        window: 窗口大小

    Returns:
        CCI 数组
    """
    n = len(typical_prices)
    if n < window:
        return np.full(n, np.nan)

    result = np.full(n, np.nan)
    sma_tp = sma(typical_prices, window)

    for i in range(window - 1, n):
        tp_window = typical_prices[i - window + 1:i + 1]
        sma_val = sma_tp[i - window + 1] if not np.isnan(sma_tp[i - window + 1]) else typical_prices[i]
        if sma_val == 0:
            continue
        mean_dev = np.mean(np.abs(tp_window - sma_val))
        if mean_dev > 0:
            result[i] = (typical_prices[i] - sma_val) / (0.015 * mean_dev)

    return result


# ---------------------------------------------------------------------------
# Pandas 支持
# ---------------------------------------------------------------------------

def compute_features_dataframe(df: Any) -> Any:
    """从 Pandas DataFrame 计算特征。

    DataFrame 必须包含列：open, high, low, close, volume

    Args:
        df: Pandas DataFrame

    Returns:
        包含特征列的 DataFrame
    """
    import pandas as pd

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected pandas DataFrame")

    required_cols = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    bars = DailyBars(
        symbol="",
        dates=df["date"].tolist() if "date" in df.columns else list(range(len(df))),
        opens=df["open"].tolist(),
        highs=df["high"].tolist(),
        lows=df["low"].tolist(),
        closes=df["close"].tolist(),
        volumes=df["volume"].tolist(),
    )

    features = compute_features(bars)
    feature_dict = features.to_dict()

    result = df.copy()
    for name, value in feature_dict.items():
        result[name] = value

    return result


# ---------------------------------------------------------------------------
# Polars 支持
# ---------------------------------------------------------------------------

def compute_features_polars(df: Any) -> Any:
    """从 Polars DataFrame 计算特征。

    DataFrame 必须包含列：open, high, low, close, volume

    Args:
        df: Polars DataFrame

    Returns:
        包含特征列的 Polars DataFrame
    """
    import polars as pl

    if not isinstance(df, pl.DataFrame):
        raise TypeError("Expected polars DataFrame")

    required_cols = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    bars = DailyBars(
        symbol="",
        dates=df["date"].to_list() if "date" in df.columns else list(range(len(df))),
        opens=df["open"].to_list(),
        highs=df["high"].to_list(),
        lows=df["low"].to_list(),
        closes=df["close"].to_list(),
        volumes=df["volume"].to_list(),
    )

    features = compute_features(bars)
    feature_dict = features.to_dict()

    # 转换为 Polars 表达式
    exprs = []
    for name, value in feature_dict.items():
        exprs.append(pl.lit(value).alias(name))

    return df.with_columns(*exprs)


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def compute_features_batch(
    bars_list: list[DailyBars],
) -> list[FeatureVector]:
    """批量计算多个标的的特征。

    Args:
        bars_list: DailyBars 列表

    Returns:
        特征向量列表
    """
    return [compute_features(bars) for bars in bars_list]
