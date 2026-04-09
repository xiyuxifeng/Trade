"""计算特征 Skill - 调用 FeatureEngine"""
from typing import Any
from src.strategy.feature_engine import FeatureEngine

# FeatureEngine 单例（复用已有实现）
_feature_engine = FeatureEngine()

async def compute_features(
    symbol: str,
    market_data: dict[str, Any],
    context: dict[str, Any]
) -> dict[str, float]:
    """
    计算特征

    Args:
        symbol: 股票代码
        market_data: 市场数据 (ohlcv, price, volume 等)
        context: 额外上下文

    Returns:
        特征名 → 特征值 字典
    """
    try:
        # FeatureEngine.compute_realtime 需要 DailyBars 格式
        bars = [market_data] if isinstance(market_data, dict) else market_data
        feature_vector = _feature_engine.compute_realtime(bars)
        return feature_vector.to_dict() if hasattr(feature_vector, 'to_dict') else {}
    except Exception as e:
        # 降级：返回空特征
        return {}
