from __future__ import annotations

import importlib
from unittest.mock import AsyncMock

import pytest


def test_canonical_writer_flag_defaults_to_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STAGE2_CANONICAL_WRITER_ENABLED", raising=False)
    routing = importlib.import_module("src.common.stage2_writer_routing")

    assert routing.canonical_writer_enabled() is True
    with pytest.raises(routing.WriterRoutingError):
        routing.require_canonical_write("market_snapshot", "test")
    with pytest.raises(routing.WriterRoutingError):
        routing.require_legacy_compatibility_write("rule", "test")


def test_canonical_writer_flag_false_is_explicit_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STAGE2_CANONICAL_WRITER_ENABLED", "false")
    routing = importlib.import_module("src.common.stage2_writer_routing")

    assert routing.canonical_writer_enabled() is False
    routing.require_canonical_write("market_snapshot", "test")
    routing.require_legacy_compatibility_write("rule", "test")


def test_enabled_canonical_repository_requires_application_service_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STAGE2_CANONICAL_WRITER_ENABLED", "1")
    routing = importlib.import_module("src.common.stage2_writer_routing")

    with pytest.raises(routing.WriterRoutingError):
        routing.require_canonical_write("market_snapshot", "repository")

    with routing.canonical_write_scope("market_snapshot", "market-data-storage"):
        routing.require_canonical_write("market_snapshot", "repository")


def test_enabled_legacy_formal_writer_is_rejected_even_inside_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STAGE2_CANONICAL_WRITER_ENABLED", "true")
    routing = importlib.import_module("src.common.stage2_writer_routing")

    with routing.canonical_write_scope("rule", "rule-pool"):
        with pytest.raises(routing.WriterRoutingError):
            routing.require_legacy_compatibility_write("rule", "rule_pool")


def test_migration_runner_is_not_imported_by_runtime_modules() -> None:
    from pathlib import Path

    runtime_roots = [Path("api"), Path("cli"), Path("src")]
    violations: list[str] = []
    for root in runtime_roots:
        for path in root.rglob("*.py"):
            if path.as_posix() == "src/migrations/stage2_data_migration.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "stage2_data_migration" in text or "src.migrations" in text:
                violations.append(path.as_posix())

    assert violations == []


@pytest.mark.asyncio
async def test_enabled_direct_snapshot_subtable_write_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STAGE2_CANONICAL_WRITER_ENABLED", "1")
    from src.db.repositories.market_snapshot_section_repository import (
        MarketSnapshotSectionRepository,
    )
    from src.models.market_data_snapshot_section import MarketSnapshotSection
    from src.common.stage2_writer_routing import WriterRoutingError

    with pytest.raises(WriterRoutingError):
        await MarketSnapshotSectionRepository().upsert_section(
            AsyncMock(),
            MarketSnapshotSection(
                snapshot_id="snapshot-1",
                section_id="indices",
                provider="test",
                quality_status="ok",
                payload_json={},
                storage_ref={},
            ),
        )


@pytest.mark.asyncio
async def test_enabled_daily_selection_repository_requires_application_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STAGE2_CANONICAL_WRITER_ENABLED", "true")
    from src.db.repositories.strategy_regime_selection_repository import (
        StrategyRegimeSelectionRepository,
    )
    from src.models.strategy_regime_selection import StrategyRegimeSelection
    from src.common.stage2_writer_routing import WriterRoutingError

    with pytest.raises(WriterRoutingError):
        await StrategyRegimeSelectionRepository().upsert_selection(
            AsyncMock(),
            StrategyRegimeSelection(
                selection_id="selection-1",
                strategy_version_id="strategy-version-1",
                snapshot_id="snapshot-1",
                market_regime_version="market-state-v1",
                source_feature_version="features-v1",
                applicability_profile_version="applicability-v1",
                selected_rule_count=0,
                skipped_rule_count=0,
                blocked_rule_count=0,
                confidence=0.0,
                quality_status="partial",
                selection_reason="test",
                evidence_json=[],
                override_json={},
                selected_by="test",
                storage_ref={},
                artifact_ref={},
            ),
        )


@pytest.mark.asyncio
async def test_enabled_rule_pool_prediction_cannot_write_legacy_fact_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STAGE2_CANONICAL_WRITER_ENABLED", "yes")
    from src.rule_pool.prediction import RulePoolPredictionService
    from src.common.stage2_writer_routing import WriterRoutingError

    repository = AsyncMock()
    with pytest.raises(WriterRoutingError):
        await RulePoolPredictionService(
            session=AsyncMock(),
            repository=repository,
        ).predict_high_confidence_rules()

    repository.get_high_confidence_rules.assert_not_awaited()


@pytest.mark.asyncio
async def test_enabled_signal_service_establishes_canonical_repository_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STAGE2_CANONICAL_WRITER_ENABLED", "on")
    from src.common.stage2_writer_routing import require_canonical_write
    from src.services.signal_service import SignalService

    class GuardedSignalRepository:
        async def upsert_signal(self, session, signal, *, context=None):
            require_canonical_write("signal", "GuardedSignalRepository.upsert_signal")
            return signal

    signal = object()
    saved = await SignalService(
        signal_repository=GuardedSignalRepository(),
    ).persist_signal(AsyncMock(), signal, context={"source": "test"})

    assert saved is signal
