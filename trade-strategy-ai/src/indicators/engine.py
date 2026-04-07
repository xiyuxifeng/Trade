"""
Technical indicators computation engine.

Pure Python / NumPy implementation — no external TA library required.

Implemented indicators:
  - SMA / EMA (simple and exponential moving averages)
  - MACD (Moving Average Convergence Divergence)
  - RSI (Relative Strength Index)
  - Bollinger Bands
  - ATR (Average True Range)
  - Stochastic Oscillator (%K, %D)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Dataclasses for indicator results
# ---------------------------------------------------------------------------

@dataclass
class MACDResult:
    macd: float
    signal: float
    histogram: float


@dataclass
class BollingerResult:
    upper: float
    middle: float
    lower: float


@dataclass
class StochasticResult:
    k: float  # %K
    d: float  # %D


# ---------------------------------------------------------------------------
# Moving averages
# ---------------------------------------------------------------------------

def sma(closes: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average."""
    if len(closes) < window:
        return np.full_like(closes, np.nan)
    return np.convolve(closes, np.ones(window) / window, mode="valid")


def ema(closes: np.ndarray, window: int) -> np.ndarray:
    """Exponential moving average (span = window)."""
    if len(closes) < window:
        return np.full_like(closes, np.nan)
    alpha = 2.0 / (window + 1)
    ema_vals = np.empty_like(closes)
    ema_vals[0] = closes[0]
    for i in range(1, len(closes)):
        ema_vals[i] = alpha * closes[i] + (1 - alpha) * ema_vals[i - 1]
    # Align with sma convention (first valid at index window-1)
    result = np.full_like(closes, np.nan)
    result[window - 1 :] = ema_vals[window - 1 :]
    return result


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------

def macd(
    closes: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> MACDResult:
    """MACD indicator.

    Returns:
        MACD line, Signal line (EMA of MACD), Histogram (MACD - Signal)
    """
    if len(closes) < slow:
        return MACDResult(macd=np.nan, signal=np.nan, histogram=np.nan)

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)

    macd_line = ema_fast - ema_slow
    # macd_line is nan-aligned with closes; use the valid portion
    macd_valid = macd_line[slow - 1 :]
    if len(macd_valid) < signal:
        return MACDResult(macd=np.nan, signal=np.nan, histogram=np.nan)

    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line

    last_valid = len(closes) - 1
    return MACDResult(
        macd=macd_line[last_valid],
        signal=signal_line[last_valid],
        histogram=hist[last_valid],
    )


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------

def rsi(closes: np.ndarray, window: int = 14) -> float:
    """Relative Strength Index (RSI).

    Returns the latest RSI value in range [0, 100].
    """
    if len(closes) < window + 1:
        return np.nan

    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # First average: simple mean
    avg_gain = np.mean(gains[:window])
    avg_loss = np.mean(losses[:window])

    if avg_loss == 0:
        return 100.0

    # Subsequent: smoothed (Wilder smoothing)
    for i in range(window, len(deltas)):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window

    rs = avg_gain / avg_loss
    rsi_val = 100.0 - (100.0 / (1.0 + rs))
    return float(rsi_val)


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------

def bollinger(
    closes: np.ndarray,
    window: int = 20,
    num_std: float = 2.0,
) -> BollingerResult:
    """Bollinger Bands.

    Returns latest upper, middle (SMA), lower band.
    """
    if len(closes) < window:
        return BollingerResult(upper=np.nan, middle=np.nan, lower=np.nan)

    middle = sma(closes, window)
    std = np.nanstd(closes[-window:], ddof=0)
    # sma returns len(closes) - window + 1 elements; use [-1] for the last valid value
    middle_val = float(middle[-1]) if len(middle) > 0 and not np.isnan(middle[-1]) else np.nan

    return BollingerResult(
        upper=float(middle_val + num_std * std),
        middle=middle_val,
        lower=middle_val - num_std * std,
    )


# ---------------------------------------------------------------------------
# ATR (Average True Range)
# ---------------------------------------------------------------------------

def atr(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    window: int = 14,
) -> float:
    """Average True Range.

    Returns the latest ATR value.
    """
    if len(closes) < 2:
        return np.nan

    tr = np.empty(len(closes))
    tr[0] = highs[0] - lows[0]
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i] = max(hl, hc, lc)

    if len(tr) < window:
        return np.nan

    # Wilder smoothing
    alpha = 1.0 / window
    atr_val = np.mean(tr[:window])
    for i in range(window, len(tr)):
        atr_val = (atr_val * (window - 1) + tr[i]) / window

    return float(atr_val)


# ---------------------------------------------------------------------------
# Stochastic Oscillator
# ---------------------------------------------------------------------------

def stochastic(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    k_window: int = 14,
    d_window: int = 3,
) -> StochasticResult:
    """Stochastic Oscillator (%K and %D).

    Returns latest %K and %D values in range [0, 100].
    """
    if len(closes) < k_window:
        return StochasticResult(k=np.nan, d=np.nan)

    k_vals = np.empty(len(closes))
    for i in range(k_window - 1, len(closes)):
        window_high = np.max(highs[i - k_window + 1 : i + 1])
        window_low = np.min(lows[i - k_window + 1 : i + 1])
        if window_high == window_low:
            k_vals[i] = 50.0
        else:
            k_vals[i] = 100.0 * (closes[i] - window_low) / (window_high - window_low)

    # %D = SMA of %K
    k_vals_valid = k_vals[k_window - 1 :]  # 长度 len(closes) - k_window + 1
    d_vals = sma(k_vals_valid, d_window)  # 长度 len(closes) - k_window - d_window + 2

    last_idx = len(closes) - 1
    k_val = k_vals[last_idx]
    # d_val 取 %D 序列的最后一个有效值
    d_val = float(d_vals[-1]) if len(d_vals) > 0 and not np.isnan(d_vals[-1]) else np.nan

    return StochasticResult(k=float(k_val), d=d_val)
