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

    # ═══════════════════════════════════════════════════════════════════════
    # evaluate_condition — 核心判断接口
    # ═══════════════════════════════════════════════════════════════════════

    def evaluate_condition(self, field: str, op: str, value: Any = None) -> bool:
        """给定 field/op/value，返回条件是否满足。

        这是供 Pattern Matcher 直接调用的核心判断接口。

        Args:
            field: 字段名（对应 canonical YAML 中的 field）
            op:    操作符（对应 canonical YAML 中的 op）
            value: 操作符参数（如 cross_below: 70 中的 70）
        """
        # === volume 类 ===
        if field == "volume":
            return self._eval_volume(op, value)

        # === 基础特征类 ===
        if field == "volume_ratio":
            return self._eval_volume_ratio(op, value)
        if field == "price_vs_ma":
            return self._eval_price_vs_ma(op, value)
        if field == "ma_slope":
            return self._eval_ma_slope(op, value)
        if field == "distance_from_high":
            return self._eval_distance_from_high(op, value)
        if field == "distance_from_low":
            return self._eval_distance_from_low(op, value)
        if field == "gap_ratio":
            return self._eval_gap_ratio_op(op, value)
        if field == "price_volatility":
            return self._eval_price_volatility_op(op, value)
        if field == "atr_ratio":
            return self._eval_price_volatility_op(op, value)
        if field == "close_position":
            return self._eval_close_position_op(op, value)

        # === 指标特征类 ===
        if field == "rsi":
            return self._eval_rsi(op, value)
        if field == "stoch_k":
            return self._eval_stoch_k(op, value)
        if field == "macd_histogram":
            return self._eval_macd_histogram(op, value)
        if field == "bb_width":
            return self._eval_bb_width(op, value)
        if field == "cci":
            return self._eval_cci(op, value)
        if field == "ma50":
            return self._eval_ma_cross(op, value, self.ensure_ma50, self.ensure_ma200)
        if field == "ma200":
            return self._eval_ma_cross(op, value, self.ensure_ma200, self.ensure_ma50)

        # === 形态特征类 ===
        if field == "price_shape":
            return self._eval_price_shape(op)
        if field == "body":
            return self._eval_body(op, value)
        if field == "upper_shadow":
            return self._eval_upper_shadow(op, value)
        if field == "lower_shadow":
            return self._eval_lower_shadow(op, value)
        if field == "trend":
            return self._eval_trend(op)
        if field == "breakout":
            return self._eval_breakout(op)
        if field == "gap":
            return self._eval_gap(op)
        if field == "gap_range":
            return self._eval_gap_range_op(op)
        if field == "gap_fill":
            return self._eval_gap_fill_op(op)
        if field == "support":
            return self._eval_support(op)
        if field == "resistance":
            return self._eval_resistance(op)
        if field == "neckline":
            return self._eval_neckline(op)
        if field == "candle1":
            return self._eval_candle_n(1, op)
        if field == "candle2":
            return self._eval_candle_n(2, op)
        if field == "candle3":
            return self._eval_candle_n(3, op)
        if field == "curr_candle":
            return self._eval_curr_candle(op)
        if field == "prev_candle":
            return self._eval_prev_candle(op)
        if field == "price_range":
            return self._eval_price_range_op(op)
        if field == "sequence":
            return self._eval_sequence(op, value)
        if field == "handle_depth":
            return self._eval_handle_depth(op, value)
        if field == "pennant":
            return self._eval_pennant_op(op)
        if field == "pole":
            return self._eval_pole(op)
        if field == "flag_channel":
            return self._eval_flag_channel(op)
        if field == "channel":
            return self._eval_channel(op)
        if field == "trendline_lower":
            return self._eval_trendline_lower(op)
        if field == "trendline_upper":
            return self._eval_trendline_upper(op)
        if field == "macd":
            return self._eval_macd_cross(op)
        if field == "first_candle":
            return self._eval_candle_n(1, op)
        if field == "second_candle":
            return self._eval_candle_n(2, op)
        if field == "third_candle":
            return self._eval_candle_n(3, op)

        # 未知字段默认 False
        return False

    # ── volume ──────────────────────────────────────────────────────────────

    def _eval_volume_ratio(self, op: str, value: Any) -> bool:
        ratio = self.compute_volume_ratio()
        if op == "spike_3x":   return ratio > 3.0
        if op == "spike":      return ratio > 2.0
        if op == "confirm":    return ratio > 1.2
        if op == "increasing": return ratio > 1.0
        if op == "drying_up":  return ratio < 0.5
        if op == "dry_up":     return ratio < 0.3
        if op == "decreasing": return ratio < 1.0
        if op == "u_shape":    return self._volume_u_shape()
        return False

    def _eval_volume(self, op: str, value: Any) -> bool:
        """volume 字段的 op 均委托给 volume_ratio 判断。"""
        return self._eval_volume_ratio(op, value)

    def _volume_u_shape(self) -> bool:
        """U 形放量检测：最近 5 日成交量谷在中间，且两边高。"""
        if len(self.bars) < 5:
            return False
        recent = list(self._volumes()[-5:])
        mid = recent[2]
        return mid < recent[0] * 0.8 and mid < recent[4] * 0.8

    # ── 基础特征 op 判断 ──────────────────────────────────────────────────

    def _eval_price_vs_ma(self, op: str, value: Any) -> bool:
        ratio = self.compute_price_vs_ma()
        if op == "gt":  return ratio > float(value) if value is not None else False
        if op == "lt":  return ratio < float(value) if value is not None else False
        if op == "ge":  return ratio >= float(value) if value is not None else False
        if op == "le":  return ratio <= float(value) if value is not None else False
        return False

    def _eval_ma_slope(self, op: str, value: Any) -> bool:
        slope = self.compute_ma_slope()
        if op == "gt":  return slope > float(value) if value is not None else False
        if op == "lt":  return slope < float(value) if value is not None else False
        if op == "ge":  return slope >= float(value) if value is not None else False
        if op == "le":  return slope <= float(value) if value is not None else False
        return False

    def _eval_distance_from_high(self, op: str, value: Any) -> bool:
        d = self.compute_distance_from_high()
        if op == "gt":  return d > float(value) if value is not None else False
        if op == "lt":  return d < float(value) if value is not None else False
        return False

    def _eval_distance_from_low(self, op: str, value: Any) -> bool:
        d = self.compute_distance_from_low()
        if op == "gt":  return d > float(value) if value is not None else False
        if op == "lt":  return d < float(value) if value is not None else False
        return False

    def _eval_gap_ratio_op(self, op: str, value: Any) -> bool:
        gap = self.compute_gap_ratio()
        if op == "gt":  return gap > float(value) if value is not None else False
        if op == "lt":  return gap < float(value) if value is not None else False
        if op == "up":  return gap > 0.01
        if op == "down": return gap < -0.01
        return False

    def _eval_price_volatility_op(self, op: str, value: Any) -> bool:
        vol = self.compute_price_volatility()
        if op == "gt":  return vol > float(value) if value is not None else False
        if op == "lt":  return vol < float(value) if value is not None else False
        if op == "narrow": return vol < 0.015
        if op == "wide":   return vol > 0.03
        return False

    def _eval_close_position_op(self, op: str, value: Any) -> bool:
        pos = self.compute_close_position()
        if op == "gt":  return pos > float(value) if value is not None else False
        if op == "lt":  return pos < float(value) if value is not None else False
        return False

    # ── 指标特征判断 ──────────────────────────────────────────────────────

    def _eval_rsi(self, op: str, value: Any) -> bool:
        rsi_val = self.ensure_rsi()
        if rsi_val is None:
            return False
        if op == "cross_below":
            return rsi_val < float(value) if value is not None else False
        if op == "cross_above":
            return rsi_val > float(value) if value is not None else False
        if op == "higher_low":
            return self._rsi_higher_low()
        if op == "lower_high":
            return self._rsi_lower_high()
        return False

    def _rsi_higher_low(self) -> bool:
        """RSI 底背离：价格创阶段新低，但 RSI 未创新低。"""
        if len(self.bars) < 10:
            return False
        closes = self._closes()
        mid = len(closes) // 2
        price_low_1 = float(np.min(closes[:mid]))
        price_low_2 = float(np.min(closes[mid:]))
        if price_low_2 < price_low_1:
            rsi_val = self.ensure_rsi()
            return rsi_val is not None and rsi_val > 30
        return False

    def _rsi_lower_high(self) -> bool:
        """RSI 顶背离：价格创阶段新高，但 RSI 未创新高。"""
        if len(self.bars) < 10:
            return False
        closes = self._closes()
        mid = len(closes) // 2
        price_high_1 = float(np.max(closes[:mid]))
        price_high_2 = float(np.max(closes[mid:]))
        if price_high_2 > price_high_1:
            rsi_val = self.ensure_rsi()
            return rsi_val is not None and rsi_val < 70
        return False

    def _eval_stoch_k(self, op: str, value: Any) -> bool:
        k = self.ensure_stoch_k()
        if k is None:
            return False
        if op == "gt":  return k > float(value)
        if op == "lt":  return k < float(value)
        if op == "cross_above":  return self._stoch_cross_above()
        if op == "cross_below":  return self._stoch_cross_below()
        return False

    def _stoch_cross_above(self) -> bool:
        """简化版：%K > 50 表示从下往上穿越区域。"""
        k = self.ensure_stoch_k()
        return k is not None and k > 50

    def _stoch_cross_below(self) -> bool:
        k = self.ensure_stoch_k()
        return k is not None and k < 50

    def _eval_macd_histogram(self, op: str, value: Any) -> bool:
        h = self.ensure_macd_histogram()
        if h is None:
            return False
        if op == "higher_low":
            return self._macd_higher_low()
        if op == "lower_high":
            return self._macd_lower_high()
        if op == "cross_up":
            return h > 0
        if op == "cross_down":
            return h < 0
        return False

    def _macd_higher_low(self) -> bool:
        if len(self.bars) < 10:
            return False
        closes = self._closes()
        mid = len(closes) // 2
        price_low_2 = float(np.min(closes[mid:]))
        price_low_1 = float(np.min(closes[:mid]))
        h = self.ensure_macd_histogram()
        return price_low_2 < price_low_1 and h is not None and h > -0.5

    def _macd_lower_high(self) -> bool:
        if len(self.bars) < 10:
            return False
        closes = self._closes()
        mid = len(closes) // 2
        price_high_2 = float(np.max(closes[mid:]))
        price_high_1 = float(np.max(closes[:mid]))
        h = self.ensure_macd_histogram()
        return price_high_2 > price_high_1 and h is not None and h < 0.5

    def _eval_bb_width(self, op: str, value: Any) -> bool:
        w = self.ensure_bb_width()
        if w is None:
            return False
        if op == "narrow":
            return w < 0.03
        if op == "squeeze_confirm":
            return w < 0.03 and self.compute_volume_ratio() > 1.5
        return False

    def _eval_cci(self, op: str, value: Any) -> bool:
        cci_val = self.ensure_cci()
        if cci_val is None:
            return False
        if op == "cross_below":
            return cci_val < float(value) if value is not None else False
        if op == "cross_above":
            return cci_val > float(value) if value is not None else False
        if op == "higher_low":
            return cci_val > -50
        if op == "lower_high":
            return cci_val < 50
        return False

    def _eval_ma_cross(self, op: str, value: Any, ma_small_fn, ma_large_fn) -> bool:
        ma_small = ma_small_fn()
        ma_large = ma_large_fn()
        if ma_small is None or ma_large is None:
            return False
        if op == "cross_below":
            return ma_small < ma_large
        if op == "cross_above":
            return ma_small > ma_large
        return False

    # ── 形态特征判断 ──────────────────────────────────────────────────────

    def _eval_price_shape(self, op: str) -> bool:
        shapes = self._detect_price_shapes()
        return shapes.get(op, False)

    def _detect_price_shapes(self) -> dict[str, bool]:
        """检测所有 price_shape 类型。"""
        results: dict[str, bool] = {}
        if len(self.bars) < 30:
            return results
        closes = self._closes()
        highs = self._highs()
        lows = self._lows()
        swing_highs, swing_lows = self._find_swing_points(highs, lows)
        if swing_highs is None or len(swing_highs) < 3:
            return results
        # 头肩底：最近 3 个 swing_low 中间最低，两边相近
        if len(swing_lows) >= 3:
            l0, l1, l2 = swing_lows[-3], swing_lows[-2], swing_lows[-1]
            if lows[l1] < lows[l0] * 0.98 and lows[l1] < lows[l2] * 0.98:
                results["head_shoulder_bottom"] = True
        # 双底
        if len(swing_lows) >= 2:
            l0, l1 = swing_lows[-2], swing_lows[-1]
            if abs(lows[l0] - lows[l1]) / lows[l0] < 0.02:
                results["double_bottom"] = True
        # 三底
        if len(swing_lows) >= 3:
            l0, l1, l2 = swing_lows[-3], swing_lows[-2], swing_lows[-1]
            if (abs(lows[l0] - lows[l1]) / lows[l0] < 0.03 and
                abs(lows[l1] - lows[l2]) / lows[l1] < 0.03):
                results["triple_bottom"] = True
        # 头肩顶
        if len(swing_highs) >= 3:
            h0, h1, h2 = swing_highs[-3], swing_highs[-2], swing_highs[-1]
            if highs[h1] > highs[h0] * 1.02 and highs[h1] > highs[h2] * 1.02:
                results["head_shoulder_top"] = True
        # 双顶
        if len(swing_highs) >= 2:
            h0, h1 = swing_highs[-2], swing_highs[-1]
            if abs(highs[h0] - highs[h1]) / highs[h0] < 0.02:
                results["double_top"] = True
        # 三顶
        if len(swing_highs) >= 3:
            h0, h1, h2 = swing_highs[-3], swing_highs[-2], swing_highs[-1]
            if (abs(highs[h0] - highs[h1]) / highs[h0] < 0.03 and
                abs(highs[h1] - highs[h2]) / highs[h1] < 0.03):
                results["triple_top"] = True
        # 旗形
        if self._detect_pennant(closes, swing_highs, swing_lows):
            results["bull_pennant"] = True
            results["bear_pennant"] = True
            results["pennant"] = True
        # 杯柄
        if self._detect_cup_and_handle(closes, swing_lows):
            results["cup_handle"] = True
        # 三角
        if self._detect_triangle(highs, lows):
            results["ascending_triangle"] = True
            results["descending_triangle"] = True
            results["symmetric_triangle"] = True
        return results

    def _find_swing_points(self, highs, lows, window: int = 5):
        """找到局部极值点。"""
        if len(highs) < window * 2 + 1:
            return None, None
        swing_highs, swing_lows = [], []
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i - window : i + window + 1]):
                swing_highs.append(i)
            if lows[i] == min(lows[i - window : i + window + 1]):
                swing_lows.append(i)
        return swing_highs, swing_lows

    def _detect_pennant(self, closes, swing_highs, swing_lows) -> bool:
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            recent_highs = [closes[h] for h in swing_highs[-3:]]
            recent_lows = [closes[l] for l in swing_lows[-3:]]
            if (recent_highs[2] < recent_highs[1] < recent_highs[0] and
                recent_lows[2] > recent_lows[1] > recent_lows[0]):
                return True
        return False

    def _detect_cup_and_handle(self, closes, swing_lows) -> bool:
        if len(swing_lows) < 2:
            return False
        l0, l1 = swing_lows[-2], swing_lows[-1]
        cup_depth = (closes[l0] - closes[l1]) / closes[l0]
        if cup_depth > 0.10:
            rebound = (closes[-1] - closes[l1]) / (closes[l0] - closes[l1])
            if rebound > 0.70:
                return True
        return False

    def _detect_triangle(self, highs, lows) -> bool:
        if len(highs) < 20 or len(lows) < 20:
            return False
        high_trend = (np.mean(highs[-10:]) - np.mean(highs[-20:-10])) / np.mean(highs[-20:-10])
        low_trend = (np.mean(lows[-10:]) - np.mean(lows[-20:-10])) / np.mean(lows[-20:-10])
        return high_trend < -0.01 and low_trend > 0.01

    def _eval_body(self, op: str, value: Any) -> bool:
        if len(self.bars) < 1:
            return False
        bar = self.bars[-1]
        body = abs(float(bar["close"]) - float(bar["open"]))
        total_range = float(bar["high"]) - float(bar["low"])
        if total_range == 0:
            return False
        body_ratio = body / total_range
        if op == "small":
            return body_ratio < 0.3
        if op == "doji":
            return body_ratio < 0.1
        if op == "engulf":
            return self._is_engulfing()
        return False

    def _is_engulfing(self) -> bool:
        """吞没形态：今日实体完全包裹昨日实体（颜色相反）。"""
        if len(self.bars) < 2:
            return False
        b1, b2 = self.bars[-2], self.bars[-1]
        body1 = abs(float(b1["close"]) - float(b1["open"]))
        body2 = abs(float(b2["close"]) - float(b2["open"]))
        if body1 == 0 or body2 == 0:
            return False
        dir1 = float(b1["close"]) > float(b1["open"])
        dir2 = float(b2["close"]) > float(b2["open"])
        if dir1 == dir2:
            return False
        return (float(b2["high"]) > float(b1["high"]) and
                float(b2["low"]) < float(b1["low"]))

    def _eval_upper_shadow(self, op: str, value: Any) -> bool:
        if len(self.bars) < 1:
            return False
        bar = self.bars[-1]
        body = abs(float(bar["close"]) - float(bar["open"]))
        upper_shadow = float(bar["high"]) - max(float(bar["open"]), float(bar["close"]))
        total_range = float(bar["high"]) - float(bar["low"])
        if op == "tiny":
            return upper_shadow < body * 0.1
        if op == "long":
            return upper_shadow > body * 2.0
        if op == "gt_pct":
            pct = float(value) / 100.0
            return total_range > 0 and upper_shadow / total_range > pct
        if op == "lt_pct":
            pct = float(value) / 100.0
            return total_range > 0 and upper_shadow / total_range < pct
        return False

    def _eval_lower_shadow(self, op: str, value: Any) -> bool:
        if len(self.bars) < 1:
            return False
        bar = self.bars[-1]
        body = abs(float(bar["close"]) - float(bar["open"]))
        lower_shadow = min(float(bar["open"]), float(bar["close"])) - float(bar["low"])
        total_range = float(bar["high"]) - float(bar["low"])
        if op == "tiny":
            return lower_shadow < body * 0.1
        if op == "long":
            return lower_shadow > body * 2.0
        if op == "gt_pct":
            pct = float(value) / 100.0
            return total_range > 0 and lower_shadow / total_range > pct
        if op == "lt_pct":
            pct = float(value) / 100.0
            return total_range > 0 and lower_shadow / total_range < pct
        return False

    def _eval_trend(self, op: str) -> bool:
        slope = self.compute_ma_slope()
        if op == "up":
            return slope > 0.005
        if op == "down":
            return slope < -0.005
        return False

    def _eval_breakout(self, op: str) -> bool:
        if len(self.bars) < 2:
            return False
        price_change = (float(self.bars[-1]["close"]) - float(self.bars[-2]["close"])) / float(self.bars[-2]["close"])
        if op == "up":
            return price_change > 0.02
        if op == "down":
            return price_change < -0.02
        if op == "any":
            return abs(price_change) > 0.02
        return False

    def _eval_gap(self, op: str) -> bool:
        gap = self.compute_gap_ratio()
        if op == "up":
            return gap > 0.01
        if op == "down":
            return gap < -0.01
        if op == "between":
            return abs(gap) <= 0.01
        if op == "isolated":
            return abs(gap) > 0.01
        return False

    def _eval_gap_range_op(self, op: str) -> bool:
        return False

    def _eval_gap_fill_op(self, op: str) -> bool:
        return False

    def _eval_support(self, op: str) -> bool:
        if len(self.bars) < 10:
            return False
        lows = self._lows()
        mid = len(lows) // 2
        low_trend = (np.mean(lows[-5:]) - np.mean(lows[:5])) / np.mean(lows[:5])
        if op == "rising":
            return low_trend > 0.01
        if op == "horizontal":
            return abs(low_trend) < 0.01
        if op == "higher_low":
            return float(np.min(lows[mid:])) > float(np.min(lows[:mid]))
        return False

    def _eval_resistance(self, op: str) -> bool:
        if len(self.bars) < 10:
            return False
        highs = self._highs()
        mid = len(highs) // 2
        high_trend = (np.mean(highs[-5:]) - np.mean(highs[:5])) / np.mean(highs[:5])
        if op == "falling":
            return high_trend < -0.01
        if op == "horizontal":
            return abs(high_trend) < 0.01
        return False

    def _eval_neckline(self, op: str) -> bool:
        return False

    def _eval_candle_n(self, n: int, op: str) -> bool:
        """第 n 根 K 线方向/形态判断（n=1 最近）。"""
        if len(self.bars) < n:
            return False
        bar = self.bars[-n]
        bullish = float(bar["close"]) > float(bar["open"])
        body = abs(float(bar["close"]) - float(bar["open"]))
        total_range = float(bar["high"]) - float(bar["low"])
        is_long = total_range > 0 and body / total_range > 0.6
        if op == "bullish":       return bullish
        if op == "bearish":       return not bullish
        if op == "bullish_long":  return bullish and is_long
        if op == "bearish_long":  return not bullish and is_long
        if op == "small_body":    return total_range > 0 and body / total_range < 0.3
        return False

    def _eval_curr_candle(self, op: str) -> bool:
        return self._eval_candle_n(1, op)

    def _eval_prev_candle(self, op: str) -> bool:
        return self._eval_candle_n(2, op)

    def _eval_price_range_op(self, op: str) -> bool:
        vol = self.compute_price_volatility()
        if op == "narrow":
            return vol < 0.015
        if op == "wide":
            return vol > 0.03
        return False

    def _eval_sequence(self, op: str, value: Any) -> bool:
        return False

    def _eval_handle_depth(self, op: str, value: Any) -> bool:
        return False

    def _eval_pennant_op(self, op: str) -> bool:
        return self._detect_pennant(self._closes(),
                                     self._find_swing_points(self._highs(), self._lows())[0] or [],
                                     self._find_swing_points(self._highs(), self._lows())[1] or [])

    def _eval_pole(self, op: str) -> bool:
        return False

    def _eval_flag_channel(self, op: str) -> bool:
        return False

    def _eval_channel(self, op: str) -> bool:
        if op == "horizontal":
            return abs(self.compute_ma_slope()) < 0.005
        return False

    def _eval_trendline_lower(self, op: str) -> bool:
        if op == "rising":
            return self._eval_support("rising")
        if op == "falling_fast":
            return False
        return False

    def _eval_trendline_upper(self, op: str) -> bool:
        if op == "falling":
            return self._eval_resistance("falling")
        if op == "rising_slow":
            return False
        return False

    def _eval_macd_cross(self, op: str) -> bool:
        h = self.ensure_macd_histogram()
        if h is None:
            return False
        if op == "cross_up":
            return h > 0
        if op == "cross_down":
            return h < 0
        return False

