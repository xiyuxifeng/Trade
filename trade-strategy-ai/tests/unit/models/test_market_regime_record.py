from __future__ import annotations

from datetime import UTC, date, datetime

from src.models.market_regime_record import MarketRegimeRecord, RegimeFeatureRecord, RegimeLabelRecord


def test_market_regime_record_dump_contains_versioned_labels() -> None:
    """Market Regime 记录应保留版本化标签和特征。"""
    record = MarketRegimeRecord(
        regime_id="regime-001",
        trade_date=date(2026, 5, 16),
        snapshot_id="snap-001",
        market="CN",
        regime_version="market-regime-v1",
        source_feature_version="market-regime-features-v1",
        primary_label="weak_bull",
        labels=[
            RegimeLabelRecord(
                label="weak_bull",
                label_type="primary",
                score=0.72,
                confidence=0.81,
                status="active",
                evidence=[],
                reason="trend positive but breadth incomplete",
            )
        ],
        features=[
            RegimeFeatureRecord(
                feature_key="trend",
                raw_value={"ret_20d": 0.08},
                normalized_value=0.8,
                source_section="overview",
                source_field="trend",
                source_version="market-regime-features-v1",
                confidence=0.9,
                weight=0.3,
                missing_reason=None,
            )
        ],
        confidence=0.81,
        quality_status="ok",
        missing_reason=None,
        created_at=datetime.now(UTC),
    )

    dumped = record.to_dict()
    assert dumped["primary_label"] == "weak_bull"
    assert dumped["source_feature_version"] == "market-regime-features-v1"
    assert dumped["labels"][0]["label"] == "weak_bull"
    assert dumped["features"][0]["feature_key"] == "trend"
