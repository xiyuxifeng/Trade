from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest

from src.domain.adapters import (
    adapt_market_regime_record_to_canonical,
    adapt_market_snapshot_dataclass_to_canonical,
    adapt_market_snapshot_orm_to_canonical,
    adapt_strategy_version_orm_to_canonical,
    adapt_strategy_version_schema_to_canonical,
)
from src.domain.contracts import CORE_OBJECT_TYPES, WRITER_OWNERSHIP, CoreDomainContractBundle
from src.domain.enums import (
    AuthorProfileKind,
    FactSource,
    FormalLifecycleState,
    MarketObservationState,
    ProposalLifecycleState,
    QualityStatus,
)
from src.domain.lifecycle import DomainLifecycleTransitionError, LifecycleTransitionValidator
from src.domain.mappings import LegacyCanonicalMapping
from src.domain.references import (
    MarketSnapshotReference,
    RuleVersionReference,
    StrategyVersionReference,
)
from src.models.market_data_snapshot import MarketSnapshot as MarketSnapshotOrm
from src.models.market_regime_record import MarketRegimeRecord
from src.models.market_snapshot import MarketSnapshot as MarketSnapshotDataclass
from src.persona.schemas import MarketState as PersonaMarketState
from src.strategy_library.schemas import StrategyVersion, StrategyVersionStatus, StrategyVersionType
from src.models.trader_strategy_version import TraderStrategyVersion


def test_core_object_type_registry_matches_frozen_task_card() -> None:
    assert CORE_OBJECT_TYPES == (
        "Article",
        "ArticleStructure",
        "RuleCandidate",
        "RuleVersion",
        "RuleFamily",
        "DatasetSnapshot",
        "MarketSnapshot",
        "MarketState",
        "RuleApplicabilityProfile",
        "AuthorMethodProfile",
        "AuthorRuleProfile",
        "AuthorValidatedProfile",
        "StrategyVersion",
        "DailyRuleSelection",
        "DailyStrategyInstance",
        "TradingDayPlan",
        "Signal",
        "PostMarketReview",
        "OptimizationProposal",
    )
    assert set(WRITER_OWNERSHIP) == set(CORE_OBJECT_TYPES)
    assert all(owner.endswith("application service") for owner in WRITER_OWNERSHIP.values())


def test_typed_references_keep_asset_and_version_ids_distinct() -> None:
    strategy_ref = StrategyVersionReference(strategy_id=uuid4(), strategy_version_id=uuid4(), version_no=3)
    rule_ref = RuleVersionReference(rule_id=uuid4(), rule_version_id=uuid4(), version_no=2)

    assert strategy_ref.strategy_id != strategy_ref.strategy_version_id
    assert rule_ref.rule_id != rule_ref.rule_version_id


def test_lifecycle_validator_enforces_frozen_formal_and_proposal_transitions() -> None:
    validator = LifecycleTransitionValidator()

    assert validator.can_transition(FormalLifecycleState.draft, FormalLifecycleState.in_review)
    assert validator.can_transition(FormalLifecycleState.in_review, FormalLifecycleState.approved)
    assert validator.can_transition(FormalLifecycleState.approved, FormalLifecycleState.published)
    assert validator.can_transition(FormalLifecycleState.published, FormalLifecycleState.superseded)
    assert validator.can_transition(FormalLifecycleState.superseded, FormalLifecycleState.archived)
    assert validator.can_transition(ProposalLifecycleState.in_review, ProposalLifecycleState.accepted)

    with pytest.raises(DomainLifecycleTransitionError):
        validator.validate(FormalLifecycleState.rejected, FormalLifecycleState.approved)

    with pytest.raises(DomainLifecycleTransitionError):
        validator.validate_proposal_acceptance_target(FormalLifecycleState.published)


def test_market_snapshot_and_market_state_adapters_converge_on_canonical_references() -> None:
    snapshot_uuid = uuid4()
    orm_snapshot = MarketSnapshotOrm(
        id=snapshot_uuid,
        snapshot_id="snapshot-cn-2026-06-14-am",
        trade_date=date(2026, 6, 14),
        market="CN",
        data_version="v1",
        slot="09-25",
        quality_status="partial",
        provider_sources=["kaipan"],
        section_count=0,
        available_section_count=0,
        partial_section_count=0,
        missing_section_count=0,
        storage_ref={},
        data_quality={},
    )
    dataclass_snapshot = MarketSnapshotDataclass(
        snapshot_id="snapshot-cn-2026-06-14-am",
        trade_date="2026-06-14",
        market="CN",
        data_version="v1",
        provider_sources=["kaipan"],
        created_at=datetime(2026, 6, 14, 9, 25),
        data_quality={"quality_status": "partial"},
        sections={},
    )

    canonical_from_orm = adapt_market_snapshot_orm_to_canonical(orm_snapshot)
    canonical_from_dataclass = adapt_market_snapshot_dataclass_to_canonical(dataclass_snapshot)

    assert canonical_from_orm.reference == MarketSnapshotReference(
        market_snapshot_id=snapshot_uuid,
        legacy_snapshot_id="snapshot-cn-2026-06-14-am",
        market="CN",
        trade_date=date(2026, 6, 14),
        slot="09-25",
        data_version="v1",
    )
    assert canonical_from_dataclass.reference.legacy_snapshot_id == canonical_from_orm.reference.legacy_snapshot_id
    assert canonical_from_dataclass.quality.status == QualityStatus.partial

    regime = MarketRegimeRecord(
        regime_id="regime-cn-2026-06-14-am",
        snapshot_id="snapshot-cn-2026-06-14-am",
        trade_date=date(2026, 6, 14),
        market="CN",
        regime_version="market-state-v1",
        source_feature_version="feature-v1",
        primary_label="range",
        labels=[],
        features=[],
        confidence=0.61,
        quality_status="partial",
    )
    persona_state = PersonaMarketState(
        as_of_date=date(2026, 6, 14),
        market="CN",
        regime="range",
        volatility="mid",
        liquidity="good",
        breadth="weak",
    )

    canonical_regime = adapt_market_regime_record_to_canonical(
        regime,
        market_snapshot_ref=canonical_from_orm.reference,
    )
    inferred_persona = adapt_market_regime_record_to_canonical(
        persona_state,
        market_snapshot_ref=canonical_from_dataclass.reference,
        definition_version="persona-compat-v0",
    )

    assert canonical_regime.lifecycle_state == MarketObservationState.partial
    assert canonical_regime.reference.legacy_regime_id == "regime-cn-2026-06-14-am"
    assert inferred_persona.provenance.fact_sources[0].fact_source == FactSource.llm_inference
    assert inferred_persona.reference.market_snapshot_id == canonical_from_dataclass.reference.market_snapshot_id


def test_strategy_version_adapters_preserve_runtime_and_formal_boundaries() -> None:
    strategy_uuid = uuid4()
    version_uuid = uuid4()
    orm_version = TraderStrategyVersion(
        id=version_uuid,
        trader_id="trader_a",
        strategy_date=date(2026, 6, 14),
        version_name="legacy-v1",
        status="released",
        version_type="manual",
        source_article_ids=["article-1"],
        evidence_refs=["evidence:1"],
        strategy_payload={"recommendations": []},
    )
    schema_version = StrategyVersion(
        version_id="legacy-v1",
        trader_id="trader_a",
        strategy_date=date(2026, 6, 14),
        status=StrategyVersionStatus.released,
        version_type=StrategyVersionType.manual,
        source_article_ids=["article-1"],
        evidence_refs=["evidence:1"],
    )

    canonical_from_orm = adapt_strategy_version_orm_to_canonical(
        orm_version,
        strategy_id=strategy_uuid,
        strategy_version_id=version_uuid,
        version_no=1,
    )
    canonical_from_schema = adapt_strategy_version_schema_to_canonical(
        schema_version,
        strategy_id=strategy_uuid,
        strategy_version_id=version_uuid,
        version_no=1,
    )

    assert canonical_from_orm.reference == StrategyVersionReference(
        strategy_id=strategy_uuid,
        strategy_version_id=version_uuid,
        version_no=1,
    )
    assert canonical_from_schema.lifecycle_state == FormalLifecycleState.published
    assert canonical_from_orm.provenance.fact_sources[0].fact_source == FactSource.legacy_import
    assert canonical_from_schema.provenance.fact_sources[0].fact_source == FactSource.legacy_import


def test_legacy_mapping_keeps_missing_and_ambiguous_information_explicit() -> None:
    mapping = LegacyCanonicalMapping(
        legacy_system="rule_pool",
        legacy_object_type="rule_pool_item",
        legacy_id="legacy-rule-001",
        canonical_object_type="RuleVersion",
        canonical_id=None,
        canonical_version_id=None,
        mapping_status=QualityStatus.ambiguous,
        mapping_reason="legacy item mixes candidate and formal version semantics",
        source_snapshot={"review_status": "approved", "mapping_status": "unmapped"},
    )

    assert mapping.mapping_status == QualityStatus.ambiguous
    assert mapping.canonical_id is None
    assert "mixes candidate and formal version semantics" in mapping.mapping_reason


def test_domain_bundle_json_schema_has_no_unresolved_refs() -> None:
    schema = CoreDomainContractBundle.model_json_schema()
    defs = schema.get("$defs", {})

    def walk(value: object) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                assert ref.removeprefix("#/$defs/") in defs
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)
    assert "StrategyVersionContract" in defs
    assert "OptimizationProposalContract" in defs
    assert defs["AuthorProfileKind"]["enum"] == [kind.value for kind in AuthorProfileKind]
