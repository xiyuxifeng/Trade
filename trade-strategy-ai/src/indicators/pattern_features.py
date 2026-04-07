"""Pattern feature computation for canonical pattern matching.

从 OHLCV 数据计算 canonical pattern YAML 所需的全部派生特征，
并提供 evaluate_condition(field, op, value) 判断接口。

Architecture:
  - PatternFeatures dataclass: 存储所有计算出的特征值
  - PatternFeatureEngine: 特征计算引擎 + evaluate_condition() 核心判断接口
  - 底层调用 engine.py 的 SMA/EMA/MACD/RSI/Bollinger/ATR/Stochastic
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from src.indicators.engine import (
    atr,
    bollinger,
    macd,
    rsi,
    sma,
    stochastic,
)


# ---------------------------------------------------------------------------
# PatternFeatures dataclass
# ---------------------------------------------------------------------------


@dataclass
class PatternFeatures:
    """Canonical pattern 所需的所有派生特征。

    Attributes 分为三类：
    - 基础特征（float）：直接从 OHLCV 计算，无缓存
    - 指标特征（float | None）：调用 engine.py 惰性计算
    - 形态特征（str | None）：识别价格结构后填充
    """

    # === 基础特征 ===
    volume_ratio: float = 1.0
    price_vs_ma: float = 1.0
    ma_slope: float = 0.0
    distance_from_high: float = 0.0
    distance_from_low: float = 0.0
    gap_ratio: float = 0.0
    price_volatility: float = 0.0
    atr_ratio: float = 0.0
    close_position: float = 0.5
    high_breakout_ratio: float = 0.0
    low_breakout_ratio: float = 0.0

    # === 指标特征 ===
    rsi: float | None = None
    stoch_k: float | None = None
    macd_histogram: float | None = None
    bb_width: float | None = None
    bb_position: float | None = None
    cci: float | None = None
    ma50: float | None = None
    ma200: float | None = None

    # === 形态特征 ===
    price_shape: str | None = None
    body: str | None = None
    upper_shadow: str | None = None
    lower_shadow: str | None = None
    trend: str | None = None
    breakout: str | None = None
    gap: str | None = None
    gap_range: str | None = None
    gap_fill: str | None = None
    support: str | None = None
    resistance: str | None = None
    neckline: str | None = None
    candle1: str | None = None
    candle2: str | None = None
    candle3: str | None = None
    curr_candle: str | None = None
    prev_candle: str | None = None
    price_action: str | None = None
    sequence: str | None = None
    handle_depth: str | None = None
    pennant: str | None = None
    pole: str | None = None
    flag_channel: str | None = None
    channel: str | None = None
    price_range: str | None = None
    trendline_lower: str | None = None
    trendline_upper: str | None = None
    macd: str | None = None
    first_candle: str | None = None
    second_candle: str | None = None
    third_candle: str | None = None


# ---------------------------------------------------------------------------
# PatternFeatureEngine（Task 2 完整实现）
# ---------------------------------------------------------------------------


class PatternFeatureEngine:
    """从 OHLCV 计算 canonical pattern 所需特征。"""

    def __init__(self, bars: list[dict | Any]):
        """
        Args:
            bars: 按时间升序的 OHLCV 列表。
                  每项需有 open/high/low/close/volume 字段。
        """
        self.bars = bars
        self._cache: dict[str, Any] = {}

    # ── 内部工具 ──────────────────────────────────────────────────────────────

    def _closes(self) -> np.ndarray:
        return np.array([float(b["close"]) for b in self.bars])

    def _highs(self) -> np.ndarray:
        return np.array([float(b["high"]) for b in self.bars])

    def _lows(self) -> np.ndarray:
        return np.array([float(b["low"]) for b in self.bars])

    def _volumes(self) -> np.ndarray:
        return np.array([float(b["volume"]) for b in self.bars])

    def _ensure_min_bars(self, n: int) -> bool:
        """数据不足时返回 False。"""
        return len(self.bars) >= n

    # ── 基础特征（纯函数，每次重新算）─────────────────────────────────────

    def compute_volume_ratio(self) -> float:
        """成交量 / 20日均量。"""
        volumes = self._volumes()
        if len(volumes) < 2:
            return 1.0
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        return float(volumes[-1] / avg_vol) if avg_vol > 0 else 1.0

    def compute_price_vs_ma(self, window: int = 20) -> float:
        """当前收盘价 / MA(window)。"""
        closes = self._closes()
        if len(closes) < window:
            return 1.0
        ma = np.mean(closes[-window:])
        return float(closes[-1] / ma) if ma > 0 else 1.0

    def compute_ma_slope(self, window: int = 5) -> float:
        """MA5 斜率：近期均值 vs 前期均值。"""
        closes = self._closes()
        if len(closes) < window * 2:
            return 0.0
        ma_recent = np.mean(closes[-window:])
        ma_past = np.mean(closes[-window * 2 : -window])
        return float((ma_recent - ma_past) / ma_past) if ma_past > 0 else 0.0

    def compute_distance_from_high(self, n: int = 20) -> float:
        """(N日高点 - 当前价格) / N日高点。"""
        highs = self._highs()
        closes = self._closes()
        high_n = float(np.max(highs[-n:])) if len(highs) >= n else float(np.max(highs))
        price = float(closes[-1])
        return float((high_n - price) / high_n) if high_n > 0 else 0.0

    def compute_distance_from_low(self, n: int = 20) -> float:
        """(当前价格 - N日低点) / N日低点。"""
        lows = self._lows()
        closes = self._closes()
        low_n = float(np.min(lows[-n:])) if len(lows) >= n else float(np.min(lows))
        price = float(closes[-1])
        return float((price - low_n) / low_n) if low_n > 0 else 0.0

    def compute_gap_ratio(self) -> float:
        """(今日开盘 - 昨收盘) / 昨收盘。"""
        if len(self.bars) < 2:
            return 0.0
        today_open = float(self.bars[-1]["open"])
        prev_close = float(self.bars[-2]["close"])
        return float((today_open - prev_close) / prev_close) if prev_close > 0 else 0.0

    def compute_price_volatility(self, window: int = 5) -> float:
        """最近 window 日收盘价 std / mean。"""
        closes = self._closes()[-window:]
        if len(closes) < 2:
            return 0.0
        mean_c = np.mean(closes)
        return float(np.std(closes, ddof=0) / mean_c) if mean_c > 0 else 0.0

    def compute_close_position(self) -> float:
        """收盘在当日振幅中的位置：0=低点，1=高点。"""
        bar = self.bars[-1]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        day_range = high - low
        return float((close - low) / day_range) if day_range > 0 else 0.5

    def compute_high_breakout_ratio(self) -> float:
        """(价格 - 日高点) / 日高点。"""
        bar = self.bars[-1]
        price = float(bar["close"])
        high = float(bar["high"])
        return float((price - high) / high) if high > 0 else 0.0

    def compute_low_breakout_ratio(self) -> float:
        """(日低点 - 价格) / 日低点。"""
        bar = self.bars[-1]
        price = float(bar["close"])
        low = float(bar["low"])
        return float((low - price) / low) if low > 0 else 0.0

    def compute_atr_ratio(self, window: int = 14) -> float:
        """ATR / 收盘价。"""
        closes = self._closes()
        highs = self._highs()
        lows = self._lows()
        if len(closes) < window + 1:
            return 0.0
        atr_val = atr(highs, lows, closes, window)
        last_close = float(closes[-1])
        return float(atr_val / last_close) if last_close > 0 and not np.isnan(atr_val) else 0.0

    # ── 指标特征（惰性计算）───────────────────────────────────────────────

    def ensure_rsi(self) -> float | None:
        if "rsi" in self._cache:
            return self._cache["rsi"]
        if not self._ensure_min_bars(15):
            return None
        closes = self._closes()
        val = rsi(closes, window=14)
        result = float(val) if not np.isnan(val) else None
        self._cache["rsi"] = result
        return result

    def ensure_stoch_k(self) -> float | None:
        if "stoch_k" in self._cache:
            return self._cache["stoch_k"]
        if not self._ensure_min_bars(15):
            return None
        highs, lows, closes = self._highs(), self._lows(), self._closes()
        result = stochastic(highs, lows, closes)
        val = float(result.k) if not np.isnan(result.k) else None
        self._cache["stoch_k"] = val
        return val

    def ensure_macd_histogram(self) -> float | None:
        if "macd_histogram" in self._cache:
            return self._cache["macd_histogram"]
        if not self._ensure_min_bars(27):
            return None
        closes = self._closes()
        result = macd(closes)
        val = float(result.histogram) if not np.isnan(result.histogram) else None
        self._cache["macd_histogram"] = val
        return val

    def ensure_bb_width(self) -> float | None:
        if "bb_width" in self._cache:
            return self._cache["bb_width"]
        if not self._ensure_min_bars(20):
            return None
        closes = self._closes()
        bb = bollinger(closes, window=20, num_std=2.0)
        if bb.middle == 0:
            return 0.0
        width = float((bb.upper - bb.lower) / bb.middle)
        if np.isnan(width) or np.isnan(bb.middle):
            return None
        self._cache["bb_width"] = width
        return width

    def ensure_cci(self, window: int = 14) -> float | None:
        if "cci" in self._cache:
            return self._cache["cci"]
        if not self._ensure_min_bars(window + 1):
            return None
        highs, lows, closes = self._highs(), self._lows(), self._closes()
        typical = (highs + lows + closes) / 3.0
        sma_tp = sma(typical, window)
        # sma 返回 len(typical) - window + 1 个元素，用 [-1] 取最新的有效值
        sma_last = float(sma_tp[-1]) if len(sma_tp) > 0 and not np.isnan(sma_tp[-1]) else None
        if sma_last is None:
            return None
        tp = typical[-1]
        mean_dev = np.mean(np.abs(typical[-window:] - sma_last))
        if mean_dev == 0:
            return 0.0
        cci_val = (tp - sma_last) / (0.015 * mean_dev)
        result = float(cci_val)
        self._cache["cci"] = result
        return result

    def ensure_ma50(self) -> float | None:
        if "ma50" in self._cache:
            return self._cache["ma50"]
        if not self._ensure_min_bars(50):
            return None
        closes = self._closes()
        val = float(sma(closes, 50)[-1])
        result = val if not np.isnan(val) else None
        self._cache["ma50"] = result
        return result

    def ensure_ma200(self) -> float | None:
        if "ma200" in self._cache:
            return self._cache["ma200"]
        if not self._ensure_min_bars(200):
            return None
        closes = self._closes()
        val = float(sma(closes, 200)[-1])
        result = val if not np.isnan(val) else None
        self._cache["ma200"] = result
        return result

    # ── compute_all ─────────────────────────────────────────────────────────

    def compute_all(self) -> PatternFeatures:
        """计算全部特征并返回 PatternFeatures dataclass。"""
        return PatternFeatures(
            volume_ratio=self.compute_volume_ratio(),
            price_vs_ma=self.compute_price_vs_ma(),
            ma_slope=self.compute_ma_slope(),
            distance_from_high=self.compute_distance_from_high(),
            distance_from_low=self.compute_distance_from_low(),
            gap_ratio=self.compute_gap_ratio(),
            price_volatility=self.compute_price_volatility(),
            atr_ratio=self.compute_atr_ratio(),
            close_position=self.compute_close_position(),
            high_breakout_ratio=self.compute_high_breakout_ratio(),
            low_breakout_ratio=self.compute_low_breakout_ratio(),
            rsi=self.ensure_rsi(),
            stoch_k=self.ensure_stoch_k(),
            macd_histogram=self.ensure_macd_histogram(),
            bb_width=self.ensure_bb_width(),
            cci=self.ensure_cci(),
            ma50=self.ensure_ma50(),
            ma200=self.ensure_ma200(),
        )

