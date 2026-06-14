from __future__ import annotations


def test_stage2_repository_foundation_exposes_canonical_interfaces_and_legacy_read_adapters() -> None:
    from src.domain.stage2_repositories import (
        CanonicalDatasetSnapshotRepository,
        CanonicalDailyRuleSelectionRepository,
        CanonicalPromptRunRepository,
        CanonicalRuleVersionRepository,
        CanonicalStrategyVersionRepository,
    )
    from src.db.repositories.stage2_compatibility import (
        LegacyDatasetCompatibilityAdapter,
        LegacyMarketStateCompatibilityAdapter,
        LegacyStrategyVersionCompatibilityAdapter,
    )

    assert CanonicalPromptRunRepository.__name__ == "CanonicalPromptRunRepository"
    assert CanonicalRuleVersionRepository.__name__ == "CanonicalRuleVersionRepository"
    assert CanonicalDatasetSnapshotRepository.__name__ == "CanonicalDatasetSnapshotRepository"
    assert CanonicalStrategyVersionRepository.__name__ == "CanonicalStrategyVersionRepository"
    assert CanonicalDailyRuleSelectionRepository.__name__ == "CanonicalDailyRuleSelectionRepository"

    for adapter_cls in (
        LegacyDatasetCompatibilityAdapter,
        LegacyMarketStateCompatibilityAdapter,
        LegacyStrategyVersionCompatibilityAdapter,
    ):
        assert hasattr(adapter_cls, "list_compatibility_records")
