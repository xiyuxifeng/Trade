"""特征计算引擎 - P4-001"""
from __future__ import annotations

from typing import Literal

from src.features.feature_pipeline import (
    compute_features,
    FeatureVector,
    DailyBars,
)
from src.shared.exceptions import FeatureEngineError


class FeatureEngine:
    """特征计算引擎

    支持两种模式:
    - 实时计算: 接收 OHLCV 原始数据，自己计算特征
    - 预计算: 接收已计算好的 FeatureVector，直接返回
    """

    def __init__(self, mode: Literal["pandas", "polars", "pure_python"] = "pure_python"):
        self._mode = mode

    def compute_realtime(
        self,
        bars: DailyBars | list[dict],
        mode: Literal["pandas", "polars", "pure_python"] | None = None,
    ) -> FeatureVector:
        """实时计算特征

        Args:
            bars: OHLCV 数据（DailyBars 或 dict list）
            mode: 计算模式，默认使用实例配置

        Returns:
            FeatureVector 特征向量

        Raises:
            FeatureEngineError: 计算失败时抛出
        """
        compute_mode = mode or self._mode

        # 转换为 DailyBars
        if isinstance(bars, list):
            bars = self._dict_list_to_bars(bars)

        try:
            return compute_features(bars)
        except Exception as e:
            raise FeatureEngineError(f"Feature computation failed: {e}") from e

    def from_precomputed(self, feature_vector: FeatureVector) -> FeatureVector:
        """直接返回预计算特征

        Args:
            feature_vector: 已计算好的特征向量

        Returns:
            相同的特征向量
        """
        return feature_vector

    def compute_batch(
        self,
        items: list[tuple[str, DailyBars]],
        mode: Literal["pandas", "polars", "pure_python"] | None = None,
    ) -> dict[str, FeatureVector]:
        """批量计算多标的的特征

        Args:
            items: [(symbol, bars), ...] 元组列表
            mode: 计算模式

        Returns:
            {symbol: FeatureVector} 字典
        """
        result = {}
        for symbol, bars in items:
            try:
                result[symbol] = self.compute_realtime(bars, mode)
            except FeatureEngineError:
                # 单标的失败不影响其他标的
                continue
        return result

    def _dict_list_to_bars(self, data: list[dict]) -> DailyBars:
        """将 dict 列表转换为 DailyBars"""
        if not data:
            raise FeatureEngineError("Empty data")

        sample = data[0]
        required = ["open", "high", "low", "close", "volume"]
        for key in required:
            if key not in sample:
                raise FeatureEngineError(f"Missing required field: {key}")

        return DailyBars(
            symbol=sample.get("symbol", "UNKNOWN"),
            dates=[d.get("date") for d in data],
            opens=[d["open"] for d in data],
            highs=[d["high"] for d in data],
            lows=[d["low"] for d in data],
            closes=[d["close"] for d in data],
            volumes=[d["volume"] for d in data],
        )