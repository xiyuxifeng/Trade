from __future__ import annotations

from dataclasses import asdict, dataclass
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

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


@pytest.mark.asyncio()
async def test_build_rule_applicability_profile_prefers_job_db_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RuleApplicabilityService 应优先从 Job DB 读取回测结果。"""
    from src.services import rule_applicability_service as mod
    from src.services.rule_applicability_service import RuleApplicabilityService

    session_scope, engine = await _build_session_factory(tmp_path)
    service = RuleApplicabilityService(session_scope_factory=session_scope, artifact_root=tmp_path / "artifacts")

    class _FakeJobService:
        async def get_job(self, job_id: str):
            assert job_id == "job-123"
            return type(
                "Result",
                (),
                {
                    "status": "ok",
                    "payload": {
                        "job": {
                            "result": {
                                "status": "ok",
                                "payload": {
                                    "result": asdict(_build_backtest_result()),
                                    "summary": {"total_days": 8},
                                    "request": {
                                        "trader_id": "trader-a",
                                        "date_from": "2026-05-01",
                                        "date_to": "2026-05-08",
                                    },
                                },
                            }
                        }
                    },
                },
            )()

    monkeypatch.setattr(mod, "JobService", lambda: _FakeJobService())

    result = await service.build_profile(
        rule_id="rule-001",
        source_backtest_id="job-123",
        profile_version="rule-applicability-v1",
        min_sample_count=10,
    )

    assert result.status == "ok"
    assert result.payload["profile"]["source_backtest_id"] == "job-123"
    assert result.payload["profile"]["rule_id"] == "rule-001"
    assert result.payload["profile"]["confidence"] > 0.0

    await engine.dispose()


@dataclass(frozen=True)
class _FormalRunFact:
    run_id: UUID
    rule_version_id: UUID | None
    rule_version_fingerprint: str | None
    rule_version_no: int | None
    rule_family_id: UUID | None
    rule_family_fingerprint: str | None
    frozen_rule_version_ids: list[str]
    frozen_rule_version_fingerprints: list[str]
    market_state_model_version: str | None
    requested_level: str
    effective_level: str
    level_policy_version: str
    dataset_snapshot_id: UUID
    dataset_fingerprint: str
    market_snapshot_ids: list[str]
    market_snapshot_fingerprints: list[str]
    recommendation_policy_version: str | None
    status: str = "completed_valid"
    limitations: list[str] | None = None


@dataclass(frozen=True)
class _FormalResultFact:
    result_id: UUID
    run_id: UUID
    result_fingerprint: str
    reproducibility_fingerprint: str
    status: str
    requested_level: str
    effective_level: str
    level_policy_version: str
    market_state_model_version: str | None
    market_state_source_version: str | None
    overall_metrics: dict
    per_market_state_metrics: list[dict]
    sample_state_counts: dict
    coverage_json: dict
    warnings: list[str]
    limitations: list[str]


class _FormalProfileRepository:
    def __init__(self, *, run: _FormalRunFact | None = None, result: _FormalResultFact | None = None) -> None:
        self.run = run
        self.result = result
        self.profiles: list[RuleApplicabilityProfile] = []
        self.audit_events: list[dict] = []

    async def get_formal_backtest_run(self, _session, *, run_id: UUID):
        return self.run if self.run and self.run.run_id == run_id else None

    async def get_formal_backtest_result(self, _session, *, result_id: UUID | None = None, run_id: UUID | None = None):
        if self.result is None:
            return None
        if result_id is not None:
            return self.result if self.result.result_id == result_id else None
        if run_id is not None:
            return self.result if self.result.run_id == run_id else None
        return None

    async def next_formal_version_no(self, _session, *, applicability_profile_id: UUID) -> int:
        versions = [
            int(profile.summary_json.get("profile_version_no", 0))
            for profile in self.profiles
            if profile.applicability_profile_id == applicability_profile_id
        ]
        return (max(versions) if versions else 0) + 1

    async def find_current_formal_profile(self, _session, *, run):
        for profile in reversed(self.profiles):
            if profile.rule_version_id == run.rule_version_id and profile.review_status in {"draft", "pending_review", "approved"}:
                return profile
        return None

    async def create_formal_profile(self, _session, profile: RuleApplicabilityProfile):
        self.profiles.append(profile)
        return profile

    async def supersede_profile(self, _session, *, profile: RuleApplicabilityProfile, superseded_by: UUID, actor_id: str, reason: str):
        profile.review_status = "superseded"
        profile.summary_json = {**profile.summary_json, "superseded_by": str(superseded_by)}
        self.audit_events.append({"transition": "superseded", "profile_id": str(profile.profile_id), "actor_id": actor_id, "reason": reason})

    async def record_audit_event(self, _session, *, profile: RuleApplicabilityProfile, event: dict):
        self.audit_events.append({"profile_id": str(profile.profile_id), **event})

    async def get_by_id(self, _session, profile_id):
        profile_id = UUID(str(profile_id))
        for profile in self.profiles:
            if profile.profile_id == profile_id:
                return profile
        return None


def _formal_facts(*, sample_count: int = 12, coverage: float = 0.92, result_status: str = "completed_valid"):
    run_id = uuid4()
    rule_version_id = uuid4()
    result_id = uuid4()
    run = _FormalRunFact(
        run_id=run_id,
        rule_version_id=rule_version_id,
        rule_version_fingerprint="rv-fp",
        rule_version_no=3,
        rule_family_id=None,
        rule_family_fingerprint=None,
        frozen_rule_version_ids=[str(rule_version_id)],
        frozen_rule_version_fingerprints=["rv-fp"],
        market_state_model_version="market-state-v1",
        requested_level="level_3",
        effective_level="level_2",
        level_policy_version="stage6-level-policy-v1",
        dataset_snapshot_id=uuid4(),
        dataset_fingerprint="ds-fp",
        market_snapshot_ids=["ms-1"],
        market_snapshot_fingerprints=["ms-fp"],
        recommendation_policy_version="rule-applicability-policy-v1",
        limitations=["缺失 Kaipan 数据只能作为数据限制展示。"],
    )
    result = _FormalResultFact(
        result_id=result_id,
        run_id=run_id,
        result_fingerprint="result-fp",
        reproducibility_fingerprint="repro-fp",
        status=result_status,
        requested_level="level_3",
        effective_level="level_2",
        level_policy_version="stage6-level-policy-v1",
        market_state_model_version="market-state-v1",
        market_state_source_version="features-v1",
        overall_metrics={"total_return": 0.18, "win_rate": 0.64, "max_drawdown": -0.08},
        per_market_state_metrics=[
            {
                "market_state_label": "强势",
                "eligible_sample_count": sample_count,
                "evaluated_sample_count": sample_count,
                "coverage": coverage,
                "total_return": 0.18,
                "win_rate": 0.64,
                "max_drawdown": -0.08,
                "warnings": [],
                "result_fingerprint": "bucket-fp",
            }
        ],
        sample_state_counts={"eligible": sample_count, "evaluated_true": sample_count, "kaipan_unavailable": 2},
        coverage_json={"overall": {"coverage": coverage}, "kaipan": {"state": "insufficient_coverage"}},
        warnings=["样本包含缺失 Kaipan 数据。"],
        limitations=["缺失 Kaipan 数据只能作为数据限制展示。"],
    )
    return run, result


@pytest.mark.asyncio()
async def test_generate_formal_draft_binds_immutable_run_result_and_level_limitations(tmp_path: Path) -> None:
    from src.services.rule_applicability_service import RuleApplicabilityService

    session_scope, engine = await _build_session_factory(tmp_path)
    run, result = _formal_facts()
    repo = _FormalProfileRepository(run=run, result=result)
    service = RuleApplicabilityService(session_scope_factory=session_scope, repo_factory=lambda: repo, artifact_root=tmp_path / "artifacts")

    created = await service.generate_formal_draft(
        run_id=str(run.run_id),
        result_id=str(result.result_id),
        actor_id="operator-1",
        actor_role="operator",
        reason="生成规则适用性画像草稿",
    )

    assert created.status == "ok"
    profile = created.payload["profile"]
    assert profile["review_status"] == "draft"
    assert profile["rule_version_id"] == str(run.rule_version_id)
    assert profile["rule_version_fingerprint"] == "rv-fp"
    assert profile["source_backtest_run_ids"] == [str(run.run_id)]
    assert profile["source_backtest_result_ids"] == [str(result.result_id)]
    assert profile["source_result_fingerprints"] == ["result-fp"]
    assert profile["requested_level"] == "level_3"
    assert profile["effective_level"] == "level_2"
    assert profile["level_policy_version"] == "stage6-level-policy-v1"
    assert profile["limitations"] == ["缺失 Kaipan 数据只能作为数据限制展示。"]
    assert profile["recommendation_status"] == "recommended"
    assert profile["review_status"] != profile["recommendation_status"]
    assert repo.audit_events[-1]["transition"] == "draft_created"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_generate_formal_draft_keeps_insufficient_sample_separate_from_negative_recommendation(tmp_path: Path) -> None:
    from src.services.rule_applicability_service import RuleApplicabilityService

    session_scope, engine = await _build_session_factory(tmp_path)
    run, result = _formal_facts(sample_count=3, coverage=0.3)
    repo = _FormalProfileRepository(run=run, result=result)
    service = RuleApplicabilityService(session_scope_factory=session_scope, repo_factory=lambda: repo, artifact_root=tmp_path / "artifacts")

    created = await service.generate_formal_draft(
        run_id=str(run.run_id),
        result_id=str(result.result_id),
        actor_id="operator-1",
        actor_role="operator",
        reason="样本不足也要生成可审核草稿",
    )

    profile = created.payload["profile"]
    assert profile["insufficient_sample_status"] == "insufficient_sample"
    assert profile["recommendation_status"] == "insufficient_sample"
    assert profile["recommendation_status"] != "not_recommended"
    assert profile["confidence"] < 0.5
    assert profile["sample_count"] == 3
    assert profile["evaluated_sample_count"] == 3

    await engine.dispose()


@pytest.mark.asyncio()
async def test_generate_formal_draft_does_not_overwrite_reviewed_profile(tmp_path: Path) -> None:
    from src.services.rule_applicability_service import RuleApplicabilityService

    session_scope, engine = await _build_session_factory(tmp_path)
    run, result = _formal_facts()
    repo = _FormalProfileRepository(run=run, result=result)
    service = RuleApplicabilityService(session_scope_factory=session_scope, repo_factory=lambda: repo, artifact_root=tmp_path / "artifacts")

    first = await service.generate_formal_draft(run_id=str(run.run_id), result_id=str(result.result_id), actor_id="operator-1", actor_role="operator", reason="first")
    reviewed = await service.review_formal_profile(
        profile_id=first.payload["profile"]["profile_id"],
        review_status="approved",
        actor_id="operator-1",
        actor_role="operator",
        reason="审核通过",
    )
    second = await service.generate_formal_draft(run_id=str(run.run_id), result_id=str(result.result_id), actor_id="operator-1", actor_role="operator", reason="new evidence")

    assert reviewed.status == "ok"
    assert first.payload["profile"]["profile_id"] != second.payload["profile"]["profile_id"]
    assert second.payload["profile"]["profile_version_no"] == 2
    assert second.payload["profile"]["supersedes_profile_id"] == first.payload["profile"]["profile_id"]
    assert repo.profiles[0].review_status == "approved"
    assert repo.audit_events[-1]["transition"] == "draft_created"

    await engine.dispose()


@pytest.mark.asyncio()
async def test_formal_profile_generation_rejects_job_payload_source(tmp_path: Path) -> None:
    from src.services.rule_applicability_service import RuleApplicabilityService

    session_scope, engine = await _build_session_factory(tmp_path)
    service = RuleApplicabilityService(session_scope_factory=session_scope, artifact_root=tmp_path / "artifacts")

    result = await service.generate_formal_draft(
        run_id="job-123",
        result_id=None,
        actor_id="operator-1",
        actor_role="operator",
        reason="不能从旧任务生成正式画像",
    )

    assert result.status == "error"
    assert result.payload["error"]["type"] == "invalid_formal_source"

    await engine.dispose()
