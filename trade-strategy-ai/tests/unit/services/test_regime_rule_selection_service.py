from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path


def _build_strategy_version():
    from src.strategy_library.schemas import StrategyRecommendation, StrategyVersion, StrategyVersionStatus, StrategyVersionType

    return StrategyVersion(
        version_id="sv-1",
        trader_id="trader_a",
        strategy_date=date(2026, 5, 19),
        status=StrategyVersionStatus.released,
        version_type=StrategyVersionType.manual,
        recommendations=[
            StrategyRecommendation(symbol="000001.SZ", decision="buy", confidence=0.9),
        ],
        source_article_ids=["article-1"],
        evidence_refs=["evidence-1"],
        notes="seed",
        released_at=None,
        rules_snapshot=[
            {"rule_id": "rule_applicable", "rule_text": "trend following"},
            {"rule_id": "rule_blocked", "rule_text": "fade panic"},
            {"rule_id": "rule_neutral", "rule_text": "theme hot"},
        ],
    )


def _build_trader_profile():
    from src.trader_profile.schemas import PositionBias, RiskStyle, StrategyPreference, StrategyTimeframe, SymbolStat, ThemeStat, TraderProfile

    return TraderProfile(
        trader_id="trader_a",
        top_symbols=[SymbolStat(symbol="000001.SZ", mentions=3)],
        style_cluster_ids=["style-1"],
        concept_tags=["trend"],
        strategy_preference=StrategyPreference(timeframe=StrategyTimeframe.SWING, entry_type="breakout"),
        risk_style=RiskStyle.BALANCED,
        theme_preference=[ThemeStat(theme="theme hot", mentions=2)],
        position_bias=PositionBias(directional="long", max_position_pct=20, avg_position_pct=10),
    )


def _build_market_regime():
    from src.models.market_regime_record import MarketRegimeRecord, RegimeFeatureRecord, RegimeLabelRecord, RegimeEvidenceRecord

    return MarketRegimeRecord(
        regime_id="regime-1",
        snapshot_id="snap-1",
        trade_date=date(2026, 5, 19),
        market="CN",
        regime_version="market-regime-v3",
        source_feature_version="market-regime-features-v3",
        primary_label="strong_bull",
        labels=[
            RegimeLabelRecord(
                label="strong_bull",
                label_type="primary",
                score=3.0,
                confidence=0.92,
                status="active",
                evidence=[RegimeEvidenceRecord(feature_key="trend", feature_value="strong_bull", source_section="overview")],
                reason="trend strong",
            ),
            RegimeLabelRecord(
                label="theme_hot",
                label_type="structural",
                score=1.0,
                confidence=0.8,
                status="active",
                evidence=[RegimeEvidenceRecord(feature_key="theme_strength", feature_value="high", source_section="hot_topics")],
                reason="theme concentrated",
            ),
        ],
        features=[
            RegimeFeatureRecord(
                feature_key="trend",
                raw_value="strong_bull",
                normalized_value="strong_bull",
                source_section="overview",
                source_field="trend",
                source_version="market-regime-features-v3",
                confidence=0.95,
                weight=1.0,
            ),
        ],
        confidence=0.91,
        quality_status="ok",
        storage_ref={"snapshot_id": "snap-1"},
    )


def _build_weak_bear_market_regime():
    from src.models.market_regime_record import MarketRegimeRecord, RegimeFeatureRecord, RegimeLabelRecord, RegimeEvidenceRecord

    return MarketRegimeRecord(
        regime_id="regime-2",
        snapshot_id="snap-2",
        trade_date=date(2026, 5, 19),
        market="CN",
        regime_version="market-regime-v3",
        source_feature_version="market-regime-features-v3",
        primary_label="weak_bear",
        labels=[
            RegimeLabelRecord(
                label="weak_bear",
                label_type="primary",
                score=-2.0,
                confidence=0.88,
                status="active",
                evidence=[RegimeEvidenceRecord(feature_key="trend", feature_value="weak_bear", source_section="overview")],
                reason="trend weak",
            ),
        ],
        features=[
            RegimeFeatureRecord(
                feature_key="trend",
                raw_value="weak_bear",
                normalized_value="weak_bear",
                source_section="overview",
                source_field="trend",
                source_version="market-regime-features-v3",
                confidence=0.92,
                weight=1.0,
            ),
        ],
        confidence=0.84,
        quality_status="ok",
        storage_ref={"snapshot_id": "snap-2"},
    )


def _build_applicability_profiles():
    from src.models.rule_applicability import RuleApplicabilityProfile, RuleApplicabilityRegimeRecord

    return [
        RuleApplicabilityProfile(
            rule_id="rule_applicable",
            profile_version="rule-applicability-v1",
            source_backtest_id="bt-1",
            source_rule_version="rule-v1",
            market_regime_version="market-regime-v3",
            source_feature_version="market-regime-features-v3",
            review_status="active",
            confidence=0.94,
            min_sample_count=5,
            applicable_regimes=[
                RuleApplicabilityRegimeRecord(
                    regime_label="strong_bull",
                    decision="applicable",
                    score=1.0,
                    sample_count=18,
                    win_rate=0.72,
                    avg_return=0.03,
                    avg_win_return=0.04,
                    avg_loss_return=-0.01,
                    max_drawdown=0.03,
                    profit_factor=1.6,
                    confidence=0.88,
                    low_sample=False,
                    reason="strong bull support",
                    evidence=["win_rate=72%"],
                )
            ],
            blocked_regimes=[],
            neutral_regimes=[],
            best_market_conditions={"summary": "strong bull"},
            worst_market_conditions={"summary": "panic"},
            summary={"rule_id": "rule_applicable"},
        ),
        RuleApplicabilityProfile(
            rule_id="rule_blocked",
            profile_version="rule-applicability-v1",
            source_backtest_id="bt-1",
            source_rule_version="rule-v1",
            market_regime_version="market-regime-v3",
            source_feature_version="market-regime-features-v3",
            review_status="active",
            confidence=0.91,
            min_sample_count=5,
            applicable_regimes=[],
            blocked_regimes=[
                RuleApplicabilityRegimeRecord(
                    regime_label="strong_bull",
                    decision="blocked",
                    score=-1.0,
                    sample_count=8,
                    win_rate=0.28,
                    avg_return=-0.02,
                    avg_win_return=0.01,
                    avg_loss_return=-0.03,
                    max_drawdown=0.06,
                    profit_factor=0.7,
                    confidence=0.76,
                    low_sample=False,
                    reason="blocked in strong bull",
                    evidence=["win_rate=28%"],
                )
            ],
            neutral_regimes=[],
            best_market_conditions={"summary": "other"},
            worst_market_conditions={"summary": "strong bull"},
            summary={"rule_id": "rule_blocked"},
        ),
        RuleApplicabilityProfile(
            rule_id="rule_neutral",
            profile_version="rule-applicability-v1",
            source_backtest_id="bt-1",
            source_rule_version="rule-v1",
            market_regime_version="market-regime-v3",
            source_feature_version="market-regime-features-v3",
            review_status="reviewed",
            confidence=0.7,
            min_sample_count=5,
            applicable_regimes=[],
            blocked_regimes=[],
            neutral_regimes=[
                RuleApplicabilityRegimeRecord(
                    regime_label="theme_hot",
                    decision="neutral",
                    score=0.3,
                    sample_count=12,
                    win_rate=0.55,
                    avg_return=0.01,
                    avg_win_return=0.02,
                    avg_loss_return=-0.01,
                    max_drawdown=0.02,
                    profit_factor=1.05,
                    confidence=0.74,
                    low_sample=False,
                    reason="theme hot fallback",
                    evidence=["theme concentration"],
                )
            ],
            best_market_conditions={"summary": "theme hot"},
            worst_market_conditions={"summary": "panic"},
            summary={"rule_id": "rule_neutral"},
        ),
    ]


def test_build_regime_rule_selection_prefers_applicable_and_excludes_blocked(tmp_path: Path) -> None:
    from src.services.regime_rule_selection_service import RegimeRuleSelectionService

    service = RegimeRuleSelectionService(artifact_root=tmp_path)
    result = asyncio.run(
        service.build_regime_rule_selection(
            strategy_version=_build_strategy_version(),
            trader_profile=_build_trader_profile(),
            market_regime=_build_market_regime(),
            applicability_profiles=_build_applicability_profiles(),
            selected_by="web",
        )
    )

    assert result.status == "ok"
    selection = result.payload["selection"]
    assert [item["rule_id"] for item in selection["selected_rules"]] == ["rule_applicable", "rule_neutral"]
    assert all(item["rule_id"] != "rule_blocked" for item in selection["selected_rules"])
    assert any(item["rule_id"] == "rule_blocked" for item in selection["blocked_rules"])
    assert selection["snapshot_id"] == "snap-1"
    assert selection["market_regime_version"] == "market-regime-v3"


def test_build_regime_rule_selection_handles_weak_bear_profile_mix(tmp_path: Path) -> None:
    from src.services.regime_rule_selection_service import RegimeRuleSelectionService
    from src.models.rule_applicability import RuleApplicabilityProfile, RuleApplicabilityRegimeRecord

    profiles = [
        RuleApplicabilityProfile(
            rule_id="rule_applicable",
            profile_version="rule-applicability-v1",
            source_backtest_id="bt-2",
            source_rule_version="rule-v1",
            market_regime_version="market-regime-v3",
            source_feature_version="market-regime-features-v3",
            review_status="reviewed",
            confidence=0.83,
            min_sample_count=5,
            applicable_regimes=[],
            blocked_regimes=[],
            neutral_regimes=[],
            best_market_conditions={"summary": "other"},
            worst_market_conditions={"summary": "weak bear"},
            summary={"rule_id": "rule_applicable"},
        ),
        RuleApplicabilityProfile(
            rule_id="rule_blocked",
            profile_version="rule-applicability-v1",
            source_backtest_id="bt-2",
            source_rule_version="rule-v1",
            market_regime_version="market-regime-v3",
            source_feature_version="market-regime-features-v3",
            review_status="active",
            confidence=0.91,
            min_sample_count=5,
            applicable_regimes=[],
            blocked_regimes=[
                RuleApplicabilityRegimeRecord(
                    regime_label="weak_bear",
                    decision="blocked",
                    score=-1.0,
                    sample_count=10,
                    win_rate=0.2,
                    avg_return=-0.04,
                    avg_win_return=0.01,
                    avg_loss_return=-0.05,
                    max_drawdown=0.09,
                    profit_factor=0.5,
                    confidence=0.82,
                    low_sample=False,
                    reason="weak bear should block",
                    evidence=["weak bear avoidance"],
                )
            ],
            neutral_regimes=[],
            best_market_conditions={"summary": "other"},
            worst_market_conditions={"summary": "weak bear"},
            summary={"rule_id": "rule_blocked"},
        ),
        RuleApplicabilityProfile(
            rule_id="rule_neutral",
            profile_version="rule-applicability-v1",
            source_backtest_id="bt-2",
            source_rule_version="rule-v1",
            market_regime_version="market-regime-v3",
            source_feature_version="market-regime-features-v3",
            review_status="reviewed",
            confidence=0.75,
            min_sample_count=5,
            applicable_regimes=[],
            blocked_regimes=[],
            neutral_regimes=[
                RuleApplicabilityRegimeRecord(
                    regime_label="weak_bear",
                    decision="neutral",
                    score=0.2,
                    sample_count=7,
                    win_rate=0.51,
                    avg_return=0.0,
                    avg_win_return=0.01,
                    avg_loss_return=-0.01,
                    max_drawdown=0.03,
                    profit_factor=1.02,
                    confidence=0.68,
                    low_sample=False,
                    reason="weak bear fallback",
                    evidence=["weak bear fallback"],
                )
            ],
            best_market_conditions={"summary": "weak bear"},
            worst_market_conditions={"summary": "panic"},
            summary={"rule_id": "rule_neutral"},
        ),
    ]

    service = RegimeRuleSelectionService(artifact_root=tmp_path)
    result = asyncio.run(
        service.build_regime_rule_selection(
            strategy_version=_build_strategy_version(),
            trader_profile=_build_trader_profile(),
            market_regime=_build_weak_bear_market_regime(),
            applicability_profiles=profiles,
            selected_by="web",
        )
    )

    selection = result.payload["selection"]
    assert any(item["rule_id"] == "rule_blocked" for item in selection["blocked_rules"])
    assert any(item["rule_id"] == "rule_neutral" for item in selection["selected_rules"])
    assert any(item["decision"] == "skipped" for item in selection["skipped_rules"] + selection["selected_rules"])


def test_build_regime_rule_selection_marks_theme_hot_neutral_as_low_weight_fallback(tmp_path: Path) -> None:
    from src.services.regime_rule_selection_service import RegimeRuleSelectionService

    service = RegimeRuleSelectionService(artifact_root=tmp_path)
    result = asyncio.run(
        service.build_regime_rule_selection(
            strategy_version=_build_strategy_version(),
            trader_profile=_build_trader_profile(),
            market_regime=_build_market_regime(),
            applicability_profiles=_build_applicability_profiles(),
            selected_by="web",
        )
    )

    selection = result.payload["selection"]
    assert selection["quality_status"] in {"ok", "partial"}
    assert any(item["decision"] == "neutral" for item in selection["selected_rules"] + selection["skipped_rules"])
