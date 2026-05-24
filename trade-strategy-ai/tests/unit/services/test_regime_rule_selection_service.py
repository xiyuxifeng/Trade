from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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


def _build_regime_rule_selection_service(tmp_path: Path):
    from src.models.strategy_regime_selection import RegimeRuleSelection, StrategyRegimeSelection
    from src.services.regime_rule_selection_service import RegimeRuleSelectionService

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'regime_selection.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(StrategyRegimeSelection.__table__.create)
            await conn.run_sync(RegimeRuleSelection.__table__.create)

    asyncio.run(_init_schema())

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return RegimeRuleSelectionService(artifact_root=tmp_path), engine, _session_scope


def test_build_regime_rule_selection_prefers_applicable_and_excludes_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, engine, session_scope = _build_regime_rule_selection_service(tmp_path)
    from src.services import regime_rule_selection_service as module

    monkeypatch.setattr(module, "session_scope", session_scope)
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
    asyncio.run(engine.dispose())


def test_build_regime_rule_selection_handles_weak_bear_profile_mix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    service, engine, session_scope = _build_regime_rule_selection_service(tmp_path)
    from src.services import regime_rule_selection_service as module

    monkeypatch.setattr(module, "session_scope", session_scope)
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
    asyncio.run(engine.dispose())


def test_build_regime_rule_selection_marks_theme_hot_neutral_as_low_weight_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, engine, session_scope = _build_regime_rule_selection_service(tmp_path)
    from src.services import regime_rule_selection_service as module

    monkeypatch.setattr(module, "session_scope", session_scope)
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
    asyncio.run(engine.dispose())


def test_build_regime_rule_selection_persists_summary_and_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regime-aware selection 完成后应同步落库摘要和规则明细。"""
    from src.db.repositories import RegimeRuleSelectionRepository, StrategyRegimeSelectionRepository
    from src.services.regime_rule_selection_service import RegimeRuleSelectionService
    service, engine, session_scope = _build_regime_rule_selection_service(tmp_path)
    monkeypatch.setattr("src.services.regime_rule_selection_service.session_scope", session_scope)
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

    async def _assert_rows() -> None:
        async with session_scope() as session:
            selection_repo = StrategyRegimeSelectionRepository()
            rule_repo = RegimeRuleSelectionRepository()
            summary = await selection_repo.get_by_selection_id(session, result.payload["selection"]["selection_id"])
            assert summary is not None
            assert summary.strategy_version_id == "sv-1"
            assert summary.selected_rule_count == len(result.payload["selection"]["selected_rules"])
            rules = await rule_repo.list_by_selection_id(session, result.payload["selection"]["selection_id"])
            assert len(rules) == len(result.payload["selection"]["selected_rules"]) + len(result.payload["selection"]["skipped_rules"]) + len(result.payload["selection"]["blocked_rules"])

    asyncio.run(_assert_rows())
    asyncio.run(engine.dispose())


def test_build_regime_rule_selection_marks_partial_when_persistence_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """摘要落库失败时不应返回 ok。"""
    service, engine, session_scope = _build_regime_rule_selection_service(tmp_path)
    monkeypatch.setattr("src.services.regime_rule_selection_service.session_scope", session_scope)

    async def _boom(*args, **kwargs):  # noqa: ANN001, ANN002
        raise RuntimeError("selection persistence boom")

    monkeypatch.setattr(
        "src.services.regime_rule_selection_service.StrategyRegimeSelectionRepository.upsert_selection",
        _boom,
    )

    result = asyncio.run(
        service.build_regime_rule_selection(
            strategy_version=_build_strategy_version(),
            trader_profile=_build_trader_profile(),
            market_regime=_build_market_regime(),
            applicability_profiles=_build_applicability_profiles(),
            selected_by="web",
        )
    )

    assert result.status == "partial"
    assert any("selection persistence boom" in warning for warning in result.warnings)
    assert any("selection persistence boom" in warning for warning in result.payload["warnings"])
    assert Path(result.payload["artifact_path"]).suffix == ".json"
    asyncio.run(engine.dispose())
