from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backtest.schemas import BacktestResult, RegimeBacktestMetric
from src.models.rule_applicability import RuleApplicabilityProfile


async def _build_session_factory(tmp_path: Path):
    """构建 Rule Applicability Service 单测 session factory。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'rule_applicability.db'}")

    async def _init_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(RuleApplicabilityProfile.__table__.create)

    await _init_schema()
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

    return _session_scope, engine


def _build_backtest_result() -> BacktestResult:
    """构造一份带 regime 分桶的回测结果。"""
    metrics = [
        RegimeBacktestMetric(
            regime_label="strong_bull",
            sample_count=18,
            win_trades=12,
            loss_trades=6,
            win_rate=0.67,
            avg_return=0.05,
            avg_win_return=0.08,
            avg_loss_return=-0.02,
            max_drawdown=-0.03,
            profit_factor=1.4,
            confidence=0.83,
            low_sample=False,
        ),
        RegimeBacktestMetric(
            regime_label="range",
            sample_count=12,
            win_trades=7,
            loss_trades=5,
            win_rate=0.58,
            avg_return=0.012,
            avg_win_return=0.03,
            avg_loss_return=-0.015,
            max_drawdown=-0.02,
            profit_factor=1.1,
            confidence=0.7,
            low_sample=False,
        ),
        RegimeBacktestMetric(
            regime_label="weak_bear",
            sample_count=11,
            win_trades=4,
            loss_trades=7,
            win_rate=0.36,
            avg_return=-0.04,
            avg_win_return=0.01,
            avg_loss_return=-0.06,
            max_drawdown=-0.11,
            profit_factor=0.82,
            confidence=0.78,
            low_sample=False,
        ),
    ]
    return BacktestResult(
        request_trader_id="trader-a",
        request_date_from=date(2026, 5, 1),
        request_date_to=date(2026, 5, 8),
        benchmark_symbol="000300.SH",
        regime_version="market-regime-v3",
        source_feature_version="market-regime-features-v3",
        records=[],
        summary=None,
        rule_regime_metrics={"rule-001": metrics},
    )


@pytest.mark.asyncio()
async def test_build_rule_applicability_profile_persists_and_classifies_regimes(tmp_path: Path) -> None:
    """RuleApplicabilityService 应从回测结果生成 profile 并落库。"""
    from src.services.rule_applicability_service import RuleApplicabilityService

    session_scope, engine = await _build_session_factory(tmp_path)
    service = RuleApplicabilityService(session_scope_factory=session_scope, artifact_root=tmp_path / "artifacts")

    result = await service.build_profile(
        rule_id="rule-001",
        source_backtest_id="backtest-001",
        profile_version="rule-applicability-v1",
        min_sample_count=10,
        backtest_result=_build_backtest_result(),
    )

    assert result.status == "ok"
    profile = result.payload["profile"]
    assert profile["rule_id"] == "rule-001"
    assert profile["source_backtest_id"] == "backtest-001"
    assert profile["market_regime_version"] == "market-regime-v3"
    assert profile["confidence"] > 0.0
    assert len(profile["applicable_regimes"]) == 1
    assert len(profile["blocked_regimes"]) == 1
    assert profile["applicable_regimes"][0]["regime_label"] == "strong_bull"
    assert profile["blocked_regimes"][0]["regime_label"] == "weak_bear"
    assert result.payload["artifact_path"].endswith("backtest-001.json")

    listed = await service.list_profiles(rule_id="rule-001")
    assert listed.payload["count"] == 1
    assert listed.payload["items"][0]["profile_id"] == profile["profile_id"]

    reviewed = await service.review_profile(profile_id=profile["profile_id"], review_status="active", reviewed_by="tester")
    assert reviewed.status == "ok"

    loaded = await service.get_profile(profile["profile_id"])
    assert loaded.payload["profile"]["review_status"] == "active"
    assert loaded.payload["profile"]["reviewed_by"] == "tester"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_build_rule_applicability_profile_rejects_missing_rule_metrics(tmp_path: Path) -> None:
    """没有 rule 级 regime metrics 时应返回结构化错误。"""
    from src.services.rule_applicability_service import RuleApplicabilityService

    session_scope, engine = await _build_session_factory(tmp_path)
    service = RuleApplicabilityService(session_scope_factory=session_scope, artifact_root=tmp_path / "artifacts")

    result = await service.build_profile(
        rule_id="rule-999",
        source_backtest_id="backtest-001",
        backtest_result=_build_backtest_result(),
    )

    assert result.status == "error"
    assert result.payload["error"]["type"] == "missing_rule_metrics"

    await engine.dispose()
