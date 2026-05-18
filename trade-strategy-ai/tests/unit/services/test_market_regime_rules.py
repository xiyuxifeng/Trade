from __future__ import annotations

from src.services.market_regime_rules import score_market_regime


def test_score_primary_label_strong_bull() -> None:
    """强势市场应判定为 strong_bull。"""
    features = {
        "trend": {"value": {"ret_20d": 0.11, "ret_5d": 0.04}, "confidence": 0.9, "source_section": "overview"},
        "breadth": {"value": {"up_ratio": 0.68}, "confidence": 0.88, "source_section": "overview"},
        "volatility": {"value": "mid", "confidence": 0.8, "source_section": "market_state"},
        "liquidity": {"value": "good", "confidence": 0.85, "source_section": "market_state"},
        "turnover_level": {"value": "high", "confidence": 0.8, "source_section": "market_state"},
        "theme_strength": {"value": {"topic_count": 5, "constituent_count": 12, "strong_symbol_count": 8}, "confidence": 0.7, "source_section": "hot_topics"},
    }

    result = score_market_regime(features, regime_version="market-regime-v1")

    assert result.primary_label == "strong_bull"
    assert any(label.label == "strong_bull" for label in result.labels)
    assert result.quality_status == "ok"
    assert result.confidence > 0.7


def test_score_market_regime_marks_partial_when_key_features_missing() -> None:
    """关键特征缺失时应返回 partial / low_confidence。"""
    features = {
        "trend": {"value": None, "missing_reason": "missing benchmark window", "confidence": 0.0},
        "breadth": {"value": None, "missing_reason": "missing breadth ratio", "confidence": 0.0},
        "volatility": {"value": "unknown", "confidence": 0.2, "source_section": "market_state"},
    }

    result = score_market_regime(features, regime_version="market-regime-v1")

    assert result.quality_status in {"partial", "low_confidence"}
    assert result.primary_label in {"range", "weak_bear", "panic"}
    assert result.missing_reason is not None
