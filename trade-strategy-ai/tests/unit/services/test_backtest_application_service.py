from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from src.services.backtest_application_service import (
    BacktestApplicationService,
    BacktestRunCreateRequest,
    BacktestSelection,
)
from tests.fixtures.taxonomy_samples import PAYLOADS


def test_formal_backtest_service_does_not_use_legacy_runtime_inputs() -> None:
    source = (
        Path(__file__).parents[3]
        / "src/services/backtest_application_service.py"
    ).read_text(encoding="utf-8")

    forbidden = [
        "JobService",
        "SnapshotLoader",
        "EvidencePack",
        "config_path",
        "Provider",
        "create_job",
        "backtest_results",
    ]
    for term in forbidden:
        assert term not in source


@dataclass(frozen=True)
class _RuleVersionFact:
    rule_version_id: UUID
    canonical_fingerprint: str
    version_no: int
    lifecycle_state: str = "pending_backtest"
    data_dependencies: dict | None = None
    source_extraction_item_id: UUID = field(default_factory=uuid4)
    source_candidate_id: UUID | None = None


@dataclass(frozen=True)
class _RuleFamilyFact:
    rule_family_id: UUID
    canonical_fingerprint: str
    members: list[_RuleVersionFact]


@dataclass(frozen=True)
class _DatasetFact:
    dataset_snapshot_id: UUID
    content_fingerprint: str
    date_from: date
    date_to: date
    benchmark_symbol: str
    available_at: datetime | None
    lifecycle_state: str = "ready"
    symbol_manifest: dict | None = None
    ohlcv_manifest: dict | None = None
    market_state_definition_version: str | None = "market-state-v1"


@dataclass(frozen=True)
class _MarketSnapshotFact:
    id: UUID
    snapshot_id: str
    content_fingerprint: str
    trade_date: date
    slot: str
    available_at: datetime | None
    captured_at: datetime | None = None
    data_version: str = "kaipan-normalizer-v2"
    provider_sources: list[str] | None = None
    quality_status: str = "ok"


@dataclass(frozen=True)
class _MarketStateFact:
    market_state_id: UUID
    market_snapshot_id: UUID
    snapshot_id: str
    trade_date: date
    market: str
    definition_version: str
    source_feature_version: str
    available_at: datetime | None
    primary_label: str
    quality_status: str = "ready"
    confidence: float = 0.9


@dataclass(frozen=True)
class _FormalSampleFact:
    trade_date: date
    symbol: str
    sample_state: str
    condition_result: bool | None = None
    return_pct: float | None = None
    reason: str | None = None


class _FakeRepository:
    def __init__(
        self,
        *,
        rule_version: _RuleVersionFact | None = None,
        rule_family: _RuleFamilyFact | None = None,
        dataset: _DatasetFact | None = None,
        market_snapshots: list[_MarketSnapshotFact] | None = None,
        market_states: list[_MarketStateFact] | None = None,
        samples: list[_FormalSampleFact] | None = None,
        backtest_run: dict | None = None,
    ) -> None:
        self.rule_version = rule_version
        self.rule_family = rule_family
        self.dataset = dataset
        self.market_snapshots = market_snapshots or []
        self.market_states = market_states or []
        self.samples = samples or []
        self.backtest_run = backtest_run
        self.created_runs: list[dict] = []
        self.created_results: list[dict] = []
        self.reused_result = None

    async def get_rule_version(self, rule_version_id: UUID):
        if self.rule_version and self.rule_version.rule_version_id == rule_version_id:
            return self.rule_version
        return None

    async def get_extraction_item(self, extraction_item_id: UUID):
        return SimpleNamespace(
            extraction_item_id=extraction_item_id,
            primary_type="executable_rule",
            taxonomy_payload={"primary_type": "executable_rule", **PAYLOADS["executable_rule"]},
            source_evidence={
                "article_id": str(uuid4()),
                "article_structure_id": str(uuid4()),
                "prompt_run_id": str(uuid4()),
                "evidence_kind": "explicit_quote",
                "rationale": "strict test fixture",
                "quote": "指数跌破共振日低点立即退出。",
            },
            review_destination="executable_rule_validation",
            quality_state="valid",
            review_state="accepted",
        )

    async def get_rule_family_with_members(self, rule_family_id: UUID):
        if self.rule_family and self.rule_family.rule_family_id == rule_family_id:
            return self.rule_family
        return None

    async def find_dataset_snapshot(self, **_: object):
        return self.dataset

    async def list_market_snapshots(self, **_: object):
        return self.market_snapshots

    async def create_backtest_run(self, payload: dict):
        self.created_runs.append(payload)
        self.backtest_run = payload
        return payload

    async def get_backtest_run(self, run_id: UUID):
        if self.backtest_run and self.backtest_run["run_id"] == run_id:
            return self.backtest_run
        return None

    async def list_market_states_for_run(self, **_: object):
        return self.market_states

    async def list_formal_samples_for_run(self, **_: object):
        return self.samples

    async def create_backtest_result(self, payload: dict):
        self.created_results.append(payload)
        return payload

    async def get_backtest_result_by_run(self, run_id: UUID):
        for payload in self.created_results:
            if payload["run_id"] == run_id:
                return payload
        return None

    async def find_reusable_backtest_result(
        self,
        *,
        input_fingerprint: str,
        rule_family_fingerprint: str | None,
        rule_version_fingerprint: str | None,
        dataset_fingerprint: str,
        market_state_model_version: str | None,
        engine_version: str,
        decision_time_policy: str,
    ):
        del (
            input_fingerprint,
            rule_family_fingerprint,
            rule_version_fingerprint,
            dataset_fingerprint,
            market_state_model_version,
            engine_version,
            decision_time_policy,
        )
        return self.reused_result


def _selection(
    *,
    rule_version_id: UUID | None = None,
    rule_family_id: UUID | None = None,
    requested_level: str = "level_1",
    date_from_value: date = date(2026, 4, 1),
    date_to_value: date = date(2026, 4, 10),
) -> BacktestSelection:
    return BacktestSelection(
        rule_version_id=rule_version_id,
        rule_family_id=rule_family_id,
        date_from=date_from_value,
        date_to=date_to_value,
        universe={"symbols": ["000001.SZ"]},
        benchmark_symbol="000300.SH",
        mode="full",
        requested_level=requested_level,
        profile_id="context-only",
    )


@pytest.mark.asyncio()
async def test_dependency_check_keeps_missing_dataset_unavailable_not_false_or_success() -> None:
    rule_version_id = uuid4()
    service = BacktestApplicationService(
        repository=_FakeRepository(
            rule_version=_RuleVersionFact(rule_version_id, "rv-fp", 1, data_dependencies={"requires": ["ohlcv"]}),
            dataset=None,
        )
    )

    result = await service.check_dependencies(_selection(rule_version_id=rule_version_id), actor_id="viewer", actor_role="viewer")

    assert result.business_state == "数据不可用"
    assert result.canonical_state == "unavailable"
    assert result.can_create_run is False
    assert "dataset_snapshot" in result.unavailable_reasons[0]["code"]
    assert result.coverage["ohlcv"]["state"] == "unavailable"
    assert result.coverage["ohlcv"]["available"] is None


@pytest.mark.asyncio()
async def test_dependency_check_marks_level_2_missing_market_state_as_repair_needed() -> None:
    rule_version_id = uuid4()
    service = BacktestApplicationService(
        repository=_FakeRepository(
            rule_version=_RuleVersionFact(rule_version_id, "rv-fp", 1),
            dataset=_DatasetFact(
                dataset_snapshot_id=uuid4(),
                content_fingerprint="ds-fp",
                date_from=date(2026, 4, 1),
                date_to=date(2026, 4, 10),
                benchmark_symbol="000300.SH",
                available_at=datetime(2026, 3, 31, 9, 0, tzinfo=UTC),
                symbol_manifest={"symbols": ["000001.SZ"]},
                ohlcv_manifest={"coverage": "complete"},
            ),
            market_snapshots=[],
        )
    )

    result = await service.check_dependencies(
        _selection(rule_version_id=rule_version_id, requested_level="level_2"),
        actor_id="viewer",
        actor_role="viewer",
    )

    assert result.business_state == "需修复"
    assert result.canonical_state == "insufficient_coverage"
    assert result.can_create_run is False
    assert result.coverage["market_state"]["state"] == "insufficient_coverage"
    assert result.coverage["market_state"]["available"] is None


@pytest.mark.asyncio()
async def test_create_run_freezes_rule_family_membership_and_snapshot_identity() -> None:
    first = _RuleVersionFact(uuid4(), "rv-fp-1", 1)
    second = _RuleVersionFact(uuid4(), "rv-fp-2", 1)
    family_id = uuid4()
    dataset_id = uuid4()
    repository = _FakeRepository(
        rule_family=_RuleFamilyFact(family_id, "family-fp", [first, second]),
        dataset=_DatasetFact(
            dataset_snapshot_id=dataset_id,
            content_fingerprint="ds-fp",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 10),
            benchmark_symbol="000300.SH",
            available_at=datetime(2026, 3, 31, 9, 0, tzinfo=UTC),
            symbol_manifest={"symbols": ["000001.SZ"]},
            ohlcv_manifest={"coverage": "complete"},
        ),
    )
    service = BacktestApplicationService(repository=repository)

    run = await service.create_run(
        BacktestRunCreateRequest(
            selection=_selection(rule_family_id=family_id),
            actor_id="operator-1",
            actor_role="operator",
            reason="验证规则族",
            source_surface="/rules/backtests",
        )
    )

    assert run.run_id
    assert run.status == "dependency_checked"
    assert run.snapshot_only is True
    assert run.rule_family_id == str(family_id)
    assert run.frozen_rule_version_ids == [str(first.rule_version_id), str(second.rule_version_id)]
    assert run.dataset_snapshot_id == str(dataset_id)
    assert repository.created_runs[0]["audit_json"]["actor_id"] == "operator-1"
    assert repository.created_runs[0]["audit_json"]["source_surface"] == "/rules/backtests"
    assert repository.created_runs[0]["request_fingerprint"] == run.request_fingerprint


@pytest.mark.asyncio()
async def test_create_run_rejects_viewer_and_does_not_create_raw_job() -> None:
    rule_version_id = uuid4()
    repository = _FakeRepository(
        rule_version=_RuleVersionFact(rule_version_id, "rv-fp", 1),
        dataset=_DatasetFact(
            dataset_snapshot_id=uuid4(),
            content_fingerprint="ds-fp",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 10),
            benchmark_symbol="000300.SH",
            available_at=datetime(2026, 3, 31, 9, 0, tzinfo=UTC),
            symbol_manifest={"symbols": ["000001.SZ"]},
            ohlcv_manifest={"coverage": "complete"},
        ),
    )
    service = BacktestApplicationService(repository=repository)

    with pytest.raises(PermissionError):
        await service.create_run(
            BacktestRunCreateRequest(
                selection=_selection(rule_version_id=rule_version_id),
                actor_id="viewer-1",
                actor_role="viewer",
                reason="viewer cannot mutate",
                source_surface="/rules/backtests",
            )
        )

    assert repository.created_runs == []


@pytest.mark.asyncio()
async def test_level_2_dependency_check_requires_point_in_time_market_state() -> None:
    rule_version_id = uuid4()
    snapshot_id = uuid4()
    repository = _FakeRepository(
        rule_version=_RuleVersionFact(rule_version_id, "rv-fp", 1),
        dataset=_DatasetFact(
            dataset_snapshot_id=uuid4(),
            content_fingerprint="ds-fp",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 10),
            benchmark_symbol="000300.SH",
            available_at=datetime(2026, 3, 31, 9, 0, tzinfo=UTC),
            symbol_manifest={"symbols": ["000001.SZ"]},
            ohlcv_manifest={"coverage": "complete"},
            market_state_definition_version="market-state-v1",
        ),
        market_snapshots=[
            _MarketSnapshotFact(
                id=snapshot_id,
                snapshot_id="ms-20260401",
                content_fingerprint="ms-fp",
                trade_date=date(2026, 4, 1),
                slot="17-30",
                available_at=datetime(2026, 4, 2, 9, 0, tzinfo=UTC),
            )
        ],
        market_states=[
            _MarketStateFact(
                market_state_id=uuid4(),
                market_snapshot_id=snapshot_id,
                snapshot_id="ms-20260401",
                trade_date=date(2026, 4, 1),
                market="CN",
                definition_version="market-state-v1",
                source_feature_version="features-v1",
                available_at=datetime(2026, 4, 1, 7, 0, tzinfo=UTC),
                primary_label="震荡",
            )
        ],
    )
    service = BacktestApplicationService(repository=repository)

    result = await service.check_dependencies(
        _selection(rule_version_id=rule_version_id, requested_level="level_2"),
        actor_id="viewer",
        actor_role="viewer",
    )

    assert result.can_create_run is False
    assert result.canonical_state == "insufficient_coverage"
    assert result.coverage["market_state"]["state"] == "insufficient_coverage"
    assert result.unavailable_reasons[0]["code"] == "market_state_future_snapshot"


@pytest.mark.asyncio()
async def test_execute_run_persists_market_state_metrics_and_fingerprints() -> None:
    run_id = uuid4()
    snapshot_id = uuid4()
    repository = _FakeRepository(
        backtest_run={
            "run_id": run_id,
            "requested_level": "level_2",
            "effective_level": "level_2",
            "date_from": date(2026, 4, 1),
            "date_to": date(2026, 4, 2),
            "dataset_snapshot_id": uuid4(),
            "dataset_fingerprint": "ds-fp",
            "market_snapshot_ids": [str(snapshot_id)],
            "market_snapshot_fingerprints": ["ms-fp"],
            "market_state_model_version": "market-state-v1",
            "indicator_version": "dataset-bound-v1",
            "engine_version": "stage6-foundation-v1",
            "execution_policy_version": "stage6-snapshot-only-v1",
            "decision_time_policy": "cn-a-share-close-plus-availability-v1",
            "request_fingerprint": "request-fp",
            "reproducibility_fingerprint": "run-rp-fp",
            "snapshot_only": True,
            "status": "dependency_checked",
            "coverage_state": "runnable",
            "quality_state": "not_executed",
            "unavailable_reasons": [],
            "limitations": [],
        },
        market_states=[
            _MarketStateFact(
                market_state_id=uuid4(),
                market_snapshot_id=snapshot_id,
                snapshot_id="ms-20260401",
                trade_date=date(2026, 4, 1),
                market="CN",
                definition_version="market-state-v1",
                source_feature_version="features-v1",
                available_at=datetime(2026, 3, 31, 23, 30, tzinfo=UTC),
                primary_label="强势",
            ),
            _MarketStateFact(
                market_state_id=uuid4(),
                market_snapshot_id=snapshot_id,
                snapshot_id="ms-20260402",
                trade_date=date(2026, 4, 2),
                market="CN",
                definition_version="market-state-v1",
                source_feature_version="features-v1",
                available_at=datetime(2026, 4, 2, 0, 30, tzinfo=UTC),
                primary_label="震荡",
            ),
        ],
        samples=[
            _FormalSampleFact(date(2026, 4, 1), "000001.SZ", "eligible", True, 0.05),
            _FormalSampleFact(date(2026, 4, 1), "000002.SZ", "eligible", False, None),
            _FormalSampleFact(date(2026, 4, 2), "000003.SZ", "condition_unavailable", None, None, "indicator_missing"),
        ],
    )
    service = BacktestApplicationService(repository=repository)

    result = await service.execute_run(run_id=str(run_id), actor_id="operator", actor_role="operator")

    assert result.status == "completed_valid"
    assert result.market_state_model_version == "market-state-v1"
    assert result.market_state_source_version == "features-v1"
    assert "market-state-v1" in result.reproducibility_fingerprint
    assert repository.created_results[0]["per_market_state_metrics"][0]["market_state_label"] == "强势"
    metric = result.per_market_state_metrics[0]
    assert metric.eligible_sample_count == 2
    assert metric.evaluated_sample_count == 2
    assert metric.hit_trade_count == 1
    assert metric.win_rate == 1.0
    assert metric.unavailable_sample_count == 0
    assert result.sample_state_counts["condition_unavailable"] == 1


@pytest.mark.asyncio()
async def test_execute_run_reuses_matching_rule_family_result_without_recomputing_samples() -> None:
    run_id = uuid4()
    repository = _FakeRepository(
        backtest_run={
            "run_id": run_id,
            "requested_level": "level_2",
            "effective_level": "level_2",
            "date_from": date(2026, 4, 1),
            "date_to": date(2026, 4, 2),
            "dataset_snapshot_id": uuid4(),
            "dataset_fingerprint": "ds-fp",
            "market_snapshot_ids": ["snapshot-1"],
            "market_snapshot_fingerprints": ["ms-fp"],
            "rule_family_id": uuid4(),
            "rule_family_fingerprint": "family-fp",
            "rule_version_id": uuid4(),
            "rule_version_fingerprint": "rule-fp",
            "market_state_model_version": "market-state-v1",
            "indicator_version": "dataset-bound-v1",
            "engine_version": "stage6-foundation-v1",
            "execution_policy_version": "stage6-snapshot-only-v1",
            "decision_time_policy": "cn-a-share-close-plus-availability-v1",
            "request_fingerprint": "request-fp",
            "reproducibility_fingerprint": "run-rp-fp",
            "snapshot_only": True,
            "status": "dependency_checked",
            "coverage_state": "runnable",
            "quality_state": "not_executed",
            "unavailable_reasons": [],
            "limitations": [],
            "level_policy_version": "stage6-level-policy-v1",
        },
        samples=[],
    )
    repository.reused_result = {
        "result_id": uuid4(),
        "run_id": uuid4(),
        "input_fingerprint": "request-fp",
        "result_fingerprint": "result-fp-existing",
        "reproducibility_fingerprint": "repro-fp-existing",
        "status": "completed_valid",
        "requested_level": "level_2",
        "effective_level": "level_2",
        "market_state_model_version": "market-state-v1",
        "market_state_source_version": "features-v1",
        "market_state_result_version": "stage6-market-state-result-v1",
        "level_policy_version": "stage6-level-policy-v1",
        "decision_time_policy": "cn-a-share-close-plus-availability-v1",
        "overall_metrics": {"eligible_sample_count": 2, "evaluated_sample_count": 2, "hit_trade_count": 1, "avg_return": 0.05, "total_return": 0.05},
        "per_market_state_metrics": [],
        "per_rule_metrics": [],
        "sample_state_counts": {"eligible": 2},
        "coverage_json": {"coverage_state": "ready"},
        "warnings": [],
        "limitations": [],
        "provenance_json": {"source_result_fingerprints": ["result-fp-existing"]},
        "audit_json": {"after_state": "completed_valid"},
    }
    service = BacktestApplicationService(repository=repository)

    result = await service.execute_run(run_id=str(run_id), actor_id="operator", actor_role="operator")

    assert result.status == "completed_valid"
    assert repository.created_results[0]["run_id"] == run_id
    assert repository.created_results[0]["input_fingerprint"] == "request-fp"
    assert repository.created_results[0]["provenance_json"]["source_result_fingerprints"] == ["result-fp-existing"]
    assert repository.created_results[0]["audit_json"]["reuse_contract"]["status"] == "reused"
    assert repository.created_results[0]["audit_json"]["reuse_contract"]["source_result_fingerprint"] == "result-fp-existing"


@pytest.mark.asyncio()
async def test_execute_run_keeps_missing_market_state_out_of_loss_denominator() -> None:
    run_id = uuid4()
    repository = _FakeRepository(
        backtest_run={
            "run_id": run_id,
            "requested_level": "level_2",
            "effective_level": "level_2",
            "date_from": date(2026, 4, 1),
            "date_to": date(2026, 4, 1),
            "dataset_snapshot_id": uuid4(),
            "dataset_fingerprint": "ds-fp",
            "market_snapshot_ids": [],
            "market_snapshot_fingerprints": [],
            "market_state_model_version": "market-state-v1",
            "indicator_version": "dataset-bound-v1",
            "engine_version": "stage6-foundation-v1",
            "execution_policy_version": "stage6-snapshot-only-v1",
            "decision_time_policy": "cn-a-share-close-plus-availability-v1",
            "request_fingerprint": "request-fp",
            "reproducibility_fingerprint": "run-rp-fp",
            "snapshot_only": True,
            "status": "dependency_checked",
            "coverage_state": "runnable",
            "quality_state": "not_executed",
            "unavailable_reasons": [],
            "limitations": [],
        },
        market_states=[],
        samples=[_FormalSampleFact(date(2026, 4, 1), "000001.SZ", "eligible", True, 0.05)],
    )
    service = BacktestApplicationService(repository=repository)

    result = await service.execute_run(run_id=str(run_id), actor_id="operator", actor_role="operator")

    assert result.status == "completed_invalid"
    assert result.coverage["market_state"]["state"] == "insufficient_coverage"
    assert result.per_market_state_metrics == []
    assert result.sample_state_counts["market_state_unavailable"] == 1
    assert "缺少可证明当时可用的市场状态" in result.warnings[0]


@pytest.mark.asyncio()
async def test_execute_run_marks_partial_market_state_coverage_invalid() -> None:
    run_id = uuid4()
    snapshot_id = uuid4()
    repository = _FakeRepository(
        backtest_run={
            "run_id": run_id,
            "requested_level": "level_2",
            "effective_level": "level_2",
            "date_from": date(2026, 4, 1),
            "date_to": date(2026, 4, 2),
            "dataset_snapshot_id": uuid4(),
            "dataset_fingerprint": "ds-fp",
            "market_snapshot_ids": [str(snapshot_id)],
            "market_snapshot_fingerprints": ["ms-fp"],
            "market_state_model_version": "market-state-v1",
            "indicator_version": "dataset-bound-v1",
            "engine_version": "stage6-foundation-v1",
            "execution_policy_version": "stage6-snapshot-only-v1",
            "decision_time_policy": "cn-a-share-close-plus-availability-v1",
            "request_fingerprint": "request-fp",
            "reproducibility_fingerprint": "run-rp-fp",
            "snapshot_only": True,
            "status": "dependency_checked",
            "coverage_state": "runnable",
            "quality_state": "not_executed",
            "unavailable_reasons": [],
            "limitations": [],
        },
        market_states=[
            _MarketStateFact(
                market_state_id=uuid4(),
                market_snapshot_id=snapshot_id,
                snapshot_id="ms-20260401",
                trade_date=date(2026, 4, 1),
                market="CN",
                definition_version="market-state-v1",
                source_feature_version="features-v1",
                available_at=datetime(2026, 3, 31, 23, 30, tzinfo=UTC),
                primary_label="强势",
            )
        ],
        samples=[
            _FormalSampleFact(date(2026, 4, 1), "000001.SZ", "eligible", True, 0.05),
            _FormalSampleFact(date(2026, 4, 2), "000002.SZ", "eligible", True, -0.03),
        ],
    )
    service = BacktestApplicationService(repository=repository)

    result = await service.execute_run(run_id=str(run_id), actor_id="operator", actor_role="operator")

    assert result.status == "completed_invalid"
    assert result.coverage["market_state"]["state"] == "insufficient_coverage"
    assert result.coverage["market_state"]["missing_trade_dates"] == ["2026-04-02"]
    assert result.sample_state_counts["market_state_unavailable"] == 1
    assert result.per_market_state_metrics[0].hit_trade_count == 1
    assert result.per_market_state_metrics[0].win_rate == 1.0


@pytest.mark.asyncio()
async def test_level_3_missing_kaipan_is_downgradeable_limitation_not_success() -> None:
    rule_version_id = uuid4()
    snapshot_id = uuid4()
    repository = _FakeRepository(
        rule_version=_RuleVersionFact(
            rule_version_id,
            "rv-fp",
            1,
            data_dependencies={"minimum_level": "level_1", "requires": ["ohlcv"]},
        ),
        dataset=_DatasetFact(
            dataset_snapshot_id=uuid4(),
            content_fingerprint="ds-fp",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
            benchmark_symbol="000300.SH",
            available_at=datetime(2026, 3, 31, 9, 0, tzinfo=UTC),
            symbol_manifest={"symbols": ["000001.SZ"]},
            ohlcv_manifest={"coverage": "complete"},
            market_state_definition_version="market-state-v1",
        ),
        market_snapshots=[
            _MarketSnapshotFact(
                id=snapshot_id,
                snapshot_id="post-close",
                content_fingerprint="post-close-fp",
                trade_date=date(2026, 4, 1),
                slot="17-30",
                available_at=datetime(2026, 4, 1, 0, 30, tzinfo=UTC),
                captured_at=datetime(2026, 4, 1, 0, 25, tzinfo=UTC),
            )
        ],
        market_states=[
            _MarketStateFact(
                market_state_id=uuid4(),
                market_snapshot_id=snapshot_id,
                snapshot_id="post-close",
                trade_date=date(2026, 4, 1),
                market="CN",
                definition_version="market-state-v1",
                source_feature_version="features-v1",
                available_at=datetime(2026, 4, 1, 0, 30, tzinfo=UTC),
                primary_label="震荡",
            )
        ],
    )
    service = BacktestApplicationService(repository=repository)

    result = await service.check_dependencies(
        _selection(rule_version_id=rule_version_id, requested_level="level_3", date_to_value=date(2026, 4, 1)),
        actor_id="viewer",
        actor_role="viewer",
    )

    assert result.canonical_state == "downgradeable"
    assert result.can_create_run is False
    assert result.effective_level == "level_2"
    assert result.minimum_required_level == "level_1"
    assert result.coverage["kaipan"]["state"] == "insufficient_coverage"
    assert result.coverage["kaipan"]["required_slot"] == "09-25"
    assert result.downgrade_reason
    assert any(item["code"] == "kaipan_slot_unavailable" for item in result.missing_requirements)
    assert "缺失 Kaipan 数据" in result.limitations[0]


@pytest.mark.asyncio()
async def test_level_3_missing_kaipan_rejects_when_rule_requires_level_3() -> None:
    rule_version_id = uuid4()
    repository = _FakeRepository(
        rule_version=_RuleVersionFact(
            rule_version_id,
            "rv-fp",
            1,
            data_dependencies={"minimum_level": "level_3", "requires": ["kaipan"]},
        ),
        dataset=_DatasetFact(
            dataset_snapshot_id=uuid4(),
            content_fingerprint="ds-fp",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
            benchmark_symbol="000300.SH",
            available_at=datetime(2026, 3, 31, 9, 0, tzinfo=UTC),
            symbol_manifest={"symbols": ["000001.SZ"]},
            ohlcv_manifest={"coverage": "complete"},
            market_state_definition_version="market-state-v1",
        ),
        market_snapshots=[],
    )
    service = BacktestApplicationService(repository=repository)

    result = await service.check_dependencies(
        _selection(rule_version_id=rule_version_id, requested_level="level_3", date_to_value=date(2026, 4, 1)),
        actor_id="viewer",
        actor_role="viewer",
    )

    assert result.canonical_state == "not_runnable"
    assert result.effective_level == "unavailable"
    assert result.minimum_required_level == "level_3"
    assert any(item["code"] == "kaipan_slot_unavailable" for item in result.missing_requirements)
    assert result.coverage["kaipan"]["available"] is None


@pytest.mark.asyncio()
async def test_explicit_downgrade_acceptance_persists_effective_level_and_audit() -> None:
    rule_version_id = uuid4()
    repository = _FakeRepository(
        rule_version=_RuleVersionFact(rule_version_id, "rv-fp", 1),
        dataset=_DatasetFact(
            dataset_snapshot_id=uuid4(),
            content_fingerprint="ds-fp",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 1),
            benchmark_symbol="000300.SH",
            available_at=datetime(2026, 3, 31, 9, 0, tzinfo=UTC),
            symbol_manifest={"symbols": ["000001.SZ"]},
            ohlcv_manifest={"coverage": "complete"},
            market_state_definition_version="market-state-v1",
        ),
    )
    service = BacktestApplicationService(repository=repository)

    with pytest.raises(ValueError):
        await service.create_run(
            BacktestRunCreateRequest(
                selection=_selection(rule_version_id=rule_version_id, requested_level="level_3", date_to_value=date(2026, 4, 1)),
                actor_id="operator-1",
                actor_role="operator",
                reason="没有确认降级",
            )
        )

    run = await service.create_run(
            BacktestRunCreateRequest(
                selection=_selection(rule_version_id=rule_version_id, requested_level="level_3", date_to_value=date(2026, 4, 1)),
            actor_id="operator-1",
            actor_role="operator",
            reason="接受缺少 Kaipan 数据时先按 Level 1 回测",
            accept_downgrade=True,
            accepted_effective_level="level_1",
        )
    )

    payload = repository.created_runs[0]
    assert run.requested_level == "level_3"
    assert run.effective_level == "level_1"
    assert payload["level_policy_version"] == "stage6-level-policy-v1"
    assert payload["audit_json"]["downgrade_acceptance"]["actor_id"] == "operator-1"
    assert payload["audit_json"]["downgrade_acceptance"]["accepted_effective_level"] == "level_1"
    assert "Kaipan" in payload["downgrade_reason"]


@pytest.mark.asyncio()
async def test_rule_family_mixed_level_reports_blocking_member() -> None:
    level_1_rule = _RuleVersionFact(uuid4(), "rv-fp-1", 1, data_dependencies={"minimum_level": "level_1"})
    level_3_rule = _RuleVersionFact(uuid4(), "rv-fp-3", 1, data_dependencies={"minimum_level": "level_3", "requires": ["kaipan"]})
    family_id = uuid4()
    service = BacktestApplicationService(
        repository=_FakeRepository(
            rule_family=_RuleFamilyFact(family_id, "family-fp", [level_1_rule, level_3_rule]),
            dataset=_DatasetFact(
                dataset_snapshot_id=uuid4(),
                content_fingerprint="ds-fp",
                date_from=date(2026, 4, 1),
                date_to=date(2026, 4, 1),
                benchmark_symbol="000300.SH",
                available_at=datetime(2026, 3, 31, 9, 0, tzinfo=UTC),
                symbol_manifest={"symbols": ["000001.SZ"]},
                ohlcv_manifest={"coverage": "complete"},
                market_state_definition_version="market-state-v1",
            ),
        )
    )

    result = await service.check_dependencies(
        _selection(rule_family_id=family_id, requested_level="level_2", date_to_value=date(2026, 4, 1)),
        actor_id="viewer",
        actor_role="viewer",
    )

    assert result.canonical_state == "not_runnable"
    assert result.minimum_required_level == "level_3"
    assert result.effective_level == "unavailable"
    assert result.rule_dependency_details[1]["rule_version_id"] == str(level_3_rule.rule_version_id)
    assert result.rule_dependency_details[1]["status"] == "unsupported_by_requested_level"
    assert result.missing_requirements[0]["rule_version_id"] == str(level_3_rule.rule_version_id)


@pytest.mark.asyncio()
async def test_level_3_execution_keeps_missing_kaipan_out_of_false_loss_and_success_counts() -> None:
    run_id = uuid4()
    repository = _FakeRepository(
        backtest_run={
            "run_id": run_id,
            "requested_level": "level_3",
            "effective_level": "level_3",
            "date_from": date(2026, 4, 1),
            "date_to": date(2026, 4, 1),
            "dataset_snapshot_id": uuid4(),
            "dataset_fingerprint": "ds-fp",
            "market_snapshot_ids": [],
            "market_snapshot_fingerprints": [],
            "market_state_model_version": "market-state-v1",
            "indicator_version": "dataset-bound-v1",
            "engine_version": "stage6-foundation-v1",
            "execution_policy_version": "stage6-snapshot-only-v1",
            "decision_time_policy": "cn-a-share-close-plus-availability-v1",
            "request_fingerprint": "request-fp",
            "reproducibility_fingerprint": "run-rp-fp",
            "snapshot_only": True,
            "status": "dependency_checked",
            "coverage_state": "runnable",
            "quality_state": "not_executed",
            "unavailable_reasons": [],
            "limitations": ["缺失 Kaipan 数据时样本只能标记为限制，不能计为条件不成立。"],
        },
        market_states=[],
        samples=[_FormalSampleFact(date(2026, 4, 1), "000001.SZ", "eligible", True, -0.08)],
    )
    service = BacktestApplicationService(repository=repository)

    result = await service.execute_run(run_id=str(run_id), actor_id="operator", actor_role="operator")

    assert result.status == "completed_invalid"
    assert result.coverage["kaipan"]["state"] == "insufficient_coverage"
    assert result.sample_state_counts["kaipan_unavailable"] == 1
    assert result.sample_state_counts["evaluated_false"] == 0
    assert result.overall_metrics["hit_trade_count"] == 0
    assert result.overall_metrics["total_return"] is None
