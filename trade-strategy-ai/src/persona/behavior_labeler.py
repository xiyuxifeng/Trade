"""行为标签化模块 — P2-009。

从 TradeLog 分类为 BehaviorLabel。
模块化设计：BehaviorClassifier 接口 + RuleBasedClassifier 实现。
"""

from __future__ import annotations

from typing import Any


class ContextBuilder:
    """从 TradeLog 和 MarketData 构建分类所需的上下文特征。

    计算派生字段（从原始 OHLCV 推导），供规则引擎使用。
    设计支持多周期，但当前仅用日线数据计算。

    派生字段：
      - price_vs_ma: 交易价格 / MA20
      - volume_ratio: 成交量 / 20日均量
      - ma_slope: MA5 斜率（相对于 MA20）
      - distance_from_high: 距离 N 日高点百分比
      - distance_from_low: 距离 N 日低点百分比
      - hour: 交易小时
    """

    def build(self, trade: Any, bars: list) -> dict:
        """构建分类上下文。

        Args:
            trade: 交易记录（TradeLog）
            bars: 同一标的的日线数据（按 traded_at 升序）

        Returns:
            包含 features（派生字段字典）和 meta 的上下文
        """
        if not bars:
            features = self._default_features()
        else:
            features = self._compute_features(trade, bars)

        return {
            "trade": trade,
            "bars": bars,
            "features": features,
        }

    def _compute_features(self, trade: Any, bars: list) -> dict:
        """计算派生特征。"""
        closes = [float(b.close) for b in bars[-20:]]  # 最近20日
        volumes = [float(b.volume) for b in bars[-20:]]

        ma20 = sum(closes) / len(closes) if closes else 0
        avg_volume = sum(volumes) / len(volumes) if volumes else 0

        trade_price = float(trade.price)
        volume = float(trade.quantity)

        features = {}

        # 价格 vs MA20
        features["price_vs_ma"] = trade_price / ma20 if ma20 > 0 else 1.0

        # 成交量比
        features["volume_ratio"] = volume / avg_volume if avg_volume > 0 else 1.0

        # MA5 斜率（简化：最近5日 vs 前5日）
        if len(closes) >= 10:
            ma5_recent = sum(closes[-5:]) / 5
            ma5_past = sum(closes[-10:-5]) / 5
            features["ma_slope"] = (ma5_recent - ma5_past) / ma5_past if ma5_past > 0 else 0.0
        else:
            features["ma_slope"] = 0.0

        # 距离 N 日高点
        highs = [float(b.high) for b in bars[-20:]]
        high_n = max(highs) if highs else trade_price
        features["distance_from_high"] = (high_n - trade_price) / high_n if high_n > 0 else 0.0

        # 距离 N 日低点
        lows = [float(b.low) for b in bars[-20:]]
        low_n = min(lows) if lows else trade_price
        features["distance_from_low"] = (trade_price - low_n) / low_n if low_n > 0 else 0.0

        # 交易小时
        features["hour"] = trade.executed_at.hour

        return features

    def _default_features(self) -> dict:
        """K线不足时返回默认值。"""
        return {
            "price_vs_ma": 1.0,
            "volume_ratio": 1.0,
            "ma_slope": 0.0,
            "distance_from_high": 0.0,
            "distance_from_low": 0.0,
            "hour": 0,
        }
