"""
基本面特征计算模块 — P2-017。

计算基本面相关特征：
  - PE（市盈率）、PB（市净率）
  - 涨速（价格变化率）
  - 市值相关指标
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class FundamentalFeatures:
    """基本面特征 dataclass。"""
    # 市盈率（PE）
    pe_ratio: float | None = None
    # 市净率（PB）
    pb_ratio: float | None = None
    # 涨速（N日价格变化率）
    price_change_rate: float | None = None
    # 年化涨速
    annualized_price_change: float | None = None
    # 成交量变化率
    volume_change_rate: float | None = None
    # 市值（如果提供）
    market_cap: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def to_array(self) -> np.ndarray:
        """转换为 numpy 数组（用于模型输入）。"""
        values = []
        defaults = [
            ("pe_ratio", 10.0),
            ("pb_ratio", 1.0),
            ("price_change_rate", 0.0),
            ("annualized_price_change", 0.0),
            ("volume_change_rate", 1.0),
            ("market_cap", 1e9),
        ]
        for name, default in defaults:
            val = getattr(self, name, None)
            values.append(val if val is not None else default)
        return np.array(values, dtype=np.float64)


def compute_pe_ratio(price: float, earnings_per_share: float) -> float | None:
    """计算市盈率（PE）。

    Args:
        price: 当前股价
        earnings_per_share: 每股收益（EPS）

    Returns:
        PE 值，EPS 为 0 或负数时返回 None
    """
    if earnings_per_share <= 0:
        return None
    return float(price / earnings_per_share)


def compute_pb_ratio(price: float, book_value_per_share: float) -> float | None:
    """计算市净率（PB）。

    Args:
        price: 当前股价
        book_value_per_share: 每股净资产

    Returns:
        PB 值，净资产为 0 或负数时返回 None
    """
    if book_value_per_share <= 0:
        return None
    return float(price / book_value_per_share)


def compute_price_change_rate(closes: np.ndarray, window: int = 20) -> float | None:
    """计算价格涨速。

    Args:
        closes: 收盘价数组
        window: 计算窗口（默认 20 日）

    Returns:
        涨速（百分比），数据不足时返回 None
    """
    n = len(closes)
    if n < window:
        return None
    current = closes[-1]
    past = closes[-window]
    if past == 0:
        return None
    return float((current - past) / past)


def compute_annualized_change(
    closes: np.ndarray,
    window: int = 20,
    periods_per_year: int = 252,
) -> float | None:
    """计算年化涨速。

    Args:
        closes: 收盘价数组
        window: 计算窗口
        periods_per_year: 年化交易日数

    Returns:
        年化涨速，数据不足时返回 None
    """
    change = compute_price_change_rate(closes, window)
    if change is None:
        return None
    # 年化：(1 + change)^(periods_per_year / window) - 1
    periods_ratio = periods_per_year / window
    return float((1 + change) ** periods_ratio - 1)


def compute_volume_change_rate(volumes: np.ndarray, window: int = 20) -> float | None:
    """计算成交量变化率。

    Args:
        volumes: 成交量数组
        window: 计算窗口

    Returns:
        成交量变化率，数据不足时返回 None
    """
    n = len(volumes)
    if n < window:
        return None
    current = volumes[-1]
    past = np.mean(volumes[-window:-1])  # 排除今日
    if past == 0:
        return None
    return float((current - past) / past)


def compute_fundamental_features(
    price: float,
    eps: float | None = None,
    book_value_per_share: float | None = None,
    closes: np.ndarray | None = None,
    volumes: np.ndarray | None = None,
    market_cap: float | None = None,
    window: int = 20,
) -> FundamentalFeatures:
    """计算基本面特征。

    Args:
        price: 当前股价
        eps: 每股收益（EPS）
        book_value_per_share: 每股净资产
        closes: 收盘价数组（用于涨速计算）
        volumes: 成交量数组（用于成交量变化计算）
        market_cap: 市值
        window: 计算窗口

    Returns:
        FundamentalFeatures
    """
    features = FundamentalFeatures()

    # PE
    if eps is not None:
        features.pe_ratio = compute_pe_ratio(price, eps)

    # PB
    if book_value_per_share is not None:
        features.pb_ratio = compute_pb_ratio(price, book_value_per_share)

    # 涨速
    if closes is not None and len(closes) >= window:
        features.price_change_rate = compute_price_change_rate(closes, window)
        features.annualized_price_change = compute_annualized_change(closes, window)

    # 成交量变化
    if volumes is not None and len(volumes) >= window:
        features.volume_change_rate = compute_volume_change_rate(volumes, window)

    # 市值
    if market_cap is not None:
        features.market_cap = market_cap

    return features
