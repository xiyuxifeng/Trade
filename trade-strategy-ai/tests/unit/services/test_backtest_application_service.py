from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.services.backtest_application_service import (
    BacktestApplicationService,
    BacktestRunCreateRequest,
    BacktestSelection,
)


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
    content_fingerprint: str
    trade_date: date
    slot: str
    available_at: datetime | None
    quality_status: str = "ok"


class _FakeRepository:
    def __init__(
        self,
        *,
        rule_version: _RuleVersionFact | None = None,
        rule_family: _RuleFamilyFact | None = None,
        dataset: _DatasetFact | None = None,
        market_snapshots: list[_MarketSnapshotFact] | None = None,
    ) -> None:
        self.rule_version = rule_version
        self.rule_family = rule_family
        self.dataset = dataset
        self.market_snapshots = market_snapshots or []
        self.created_runs: list[dict] = []

    async def get_rule_version(self, rule_version_id: UUID):
        if self.rule_version and self.rule_version.rule_version_id == rule_version_id:
            return self.rule_version
        return None

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
        return payload


def _selection(
    *,
    rule_version_id: UUID | None = None,
    rule_family_id: UUID | None = None,
    requested_level: str = "level_1",
) -> BacktestSelection:
    return BacktestSelection(
        rule_version_id=rule_version_id,
        rule_family_id=rule_family_id,
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 10),
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
