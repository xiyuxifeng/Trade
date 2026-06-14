from __future__ import annotations

from datetime import date
from uuid import UUID, NAMESPACE_URL, uuid5

from src.domain.contracts import (
    ArticleContract,
    ArticleStructureContract,
    MarketSnapshotContract,
    MarketStateContract,
    QualityRecord,
    SourceProvenance,
    StrategyVersionContract,
)
from src.domain.enums import (
    ArticleStructureLifecycleState,
    FactSource,
    FormalLifecycleState,
    MarketObservationState,
    MarketSnapshotState,
    QualityStatus,
)
from src.domain.references import (
    ArticleReference,
    ArticleStructureReference,
    MarketSnapshotReference,
    MarketStateReference,
    StrategyVersionReference,
)
from src.domain.value_objects import AuditStamp, FactSourceRecord
from src.models.market_data_snapshot import MarketSnapshot as MarketSnapshotOrm
from src.models.market_regime_record import MarketRegimeRecord
from src.models.market_snapshot import MarketSnapshot as MarketSnapshotDataclass
from src.models.trader_strategy_version import TraderStrategyVersion
from src.persona.schemas import MarketState as PersonaMarketState
from src.strategy_library.schemas import StrategyVersion


def _compatibility_uuid(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"trade-strategy-ai:{value}")


def _quality_from_legacy(value: str | None, *, default: QualityStatus = QualityStatus.legacy_only) -> QualityStatus:
    mapping = {
        "verified": QualityStatus.verified,
        "complete": QualityStatus.complete,
        "ok": QualityStatus.complete,
        "ready": QualityStatus.complete,
        "partial": QualityStatus.partial,
        "ambiguous": QualityStatus.ambiguous,
        "unresolved": QualityStatus.unresolved,
        "rejected": QualityStatus.rejected,
        "legacy_only": QualityStatus.legacy_only,
    }
    if value is None:
        return default
    return mapping.get(value, default)


def _formal_state_from_legacy(value: str) -> FormalLifecycleState:
    mapping = {
        "draft": FormalLifecycleState.draft,
        "released": FormalLifecycleState.published,
        "published": FormalLifecycleState.published,
        "approved": FormalLifecycleState.approved,
        "archived": FormalLifecycleState.archived,
    }
    return mapping.get(value, FormalLifecycleState.draft)


def adapt_market_snapshot_orm_to_canonical(legacy: MarketSnapshotOrm) -> MarketSnapshotContract:
    return MarketSnapshotContract(
        reference=MarketSnapshotReference(
            market_snapshot_id=legacy.id,
            legacy_snapshot_id=legacy.snapshot_id,
            market=legacy.market,
            trade_date=legacy.trade_date,
            slot=legacy.slot,
            data_version=legacy.data_version,
        ),
        lifecycle_state=MarketSnapshotState.partial if legacy.quality_status == "partial" else MarketSnapshotState.ready,
        provenance=SourceProvenance(
            fact_sources=[FactSourceRecord(fact_source=FactSource.program_observation, source_ref="market_snapshots")],
            source_type="orm",
            source_ref=legacy.snapshot_id,
        ),
        quality=QualityRecord(status=_quality_from_legacy(legacy.quality_status)),
        audit=AuditStamp(created_by="legacy-market-storage", updated_by="legacy-market-storage"),
    )


def adapt_market_snapshot_dataclass_to_canonical(legacy: MarketSnapshotDataclass) -> MarketSnapshotContract:
    return MarketSnapshotContract(
        reference=MarketSnapshotReference(
            market_snapshot_id=_compatibility_uuid(f"market_snapshot:{legacy.snapshot_id}"),
            legacy_snapshot_id=legacy.snapshot_id,
            market=legacy.market,
            trade_date=date.fromisoformat(legacy.trade_date),
            slot=str(legacy.metadata.get("slot", "compat")),
            data_version=legacy.data_version,
        ),
        lifecycle_state=MarketSnapshotState.partial,
        provenance=SourceProvenance(
            fact_sources=[FactSourceRecord(fact_source=FactSource.legacy_import, source_ref="market_snapshot_dataclass")],
            source_type="dataclass",
            source_ref=legacy.snapshot_id,
        ),
        quality=QualityRecord(status=_quality_from_legacy(legacy.data_quality.get("quality_status"))),
        audit=AuditStamp(created_by="legacy-market-builder", updated_by="legacy-market-builder"),
    )


def adapt_market_regime_record_to_canonical(
    legacy: MarketRegimeRecord | PersonaMarketState,
    *,
    market_snapshot_ref: MarketSnapshotReference,
    definition_version: str | None = None,
) -> MarketStateContract:
    if isinstance(legacy, MarketRegimeRecord):
        return MarketStateContract(
            reference=MarketStateReference(
                market_state_id=_compatibility_uuid(f"market_state:{legacy.regime_id}"),
                market_snapshot_id=market_snapshot_ref.market_snapshot_id,
                definition_version=legacy.regime_version,
                legacy_regime_id=legacy.regime_id,
            ),
            market_snapshot=market_snapshot_ref,
            lifecycle_state=MarketObservationState.partial if legacy.quality_status == "partial" else MarketObservationState.valid,
            primary_label=legacy.primary_label,
            confidence=legacy.confidence,
            source_feature_version=legacy.source_feature_version,
            provenance=SourceProvenance(
                fact_sources=[FactSourceRecord(fact_source=FactSource.program_observation, source_ref="market_regimes")],
                source_type="orm",
                source_ref=legacy.regime_id,
            ),
            quality=QualityRecord(status=_quality_from_legacy(legacy.quality_status)),
            audit=AuditStamp(created_by="legacy-market-regime-service", updated_by="legacy-market-regime-service"),
        )

    return MarketStateContract(
        reference=MarketStateReference(
            market_state_id=_compatibility_uuid(
                f"persona_market_state:{legacy.market}:{legacy.as_of_date.isoformat()}:{definition_version or 'persona-compat-v0'}"
            ),
            market_snapshot_id=market_snapshot_ref.market_snapshot_id,
            definition_version=definition_version or "persona-compat-v0",
            legacy_regime_id=None,
        ),
        market_snapshot=market_snapshot_ref,
        lifecycle_state=MarketObservationState.partial,
        primary_label=str(legacy.regime),
        confidence=0.0,
        source_feature_version="persona-compat-v0",
        provenance=SourceProvenance(
            fact_sources=[FactSourceRecord(fact_source=FactSource.llm_inference, source_ref="persona.schemas.MarketState")],
            source_type="pydantic",
            source_ref=f"{legacy.market}:{legacy.as_of_date.isoformat()}",
        ),
        quality=QualityRecord(
            status=QualityStatus.legacy_only,
            reason="legacy persona market state lacks canonical market snapshot and review lifecycle",
        ),
        audit=AuditStamp(created_by="legacy-persona-service", updated_by="legacy-persona-service"),
    )


def adapt_strategy_version_orm_to_canonical(
    legacy: TraderStrategyVersion,
    *,
    strategy_id: UUID,
    strategy_version_id: UUID,
    version_no: int,
) -> StrategyVersionContract:
    return StrategyVersionContract(
        reference=StrategyVersionReference(
            strategy_id=strategy_id,
            strategy_version_id=strategy_version_id,
            version_no=version_no,
        ),
        lifecycle_state=_formal_state_from_legacy(legacy.status),
        provenance=SourceProvenance(
            fact_sources=[FactSourceRecord(fact_source=FactSource.legacy_import, source_ref="trader_strategy_versions")],
            source_type="orm",
            source_ref=legacy.version_name,
        ),
        quality=QualityRecord(status=QualityStatus.legacy_only, reason="legacy daily strategy version compatibility"),
        audit=AuditStamp(created_by="legacy-strategy-repository", updated_by="legacy-strategy-repository"),
    )


def adapt_strategy_version_schema_to_canonical(
    legacy: StrategyVersion,
    *,
    strategy_id: UUID,
    strategy_version_id: UUID,
    version_no: int,
) -> StrategyVersionContract:
    return StrategyVersionContract(
        reference=StrategyVersionReference(
            strategy_id=strategy_id,
            strategy_version_id=strategy_version_id,
            version_no=version_no,
        ),
        lifecycle_state=_formal_state_from_legacy(legacy.status.value),
        provenance=SourceProvenance(
            fact_sources=[FactSourceRecord(fact_source=FactSource.legacy_import, source_ref="strategy_library.schemas.StrategyVersion")],
            source_type="schema",
            source_ref=legacy.version_id,
        ),
        quality=QualityRecord(status=QualityStatus.legacy_only, reason="legacy strategy schema compatibility"),
        audit=AuditStamp(created_by="legacy-strategy-schema", updated_by="legacy-strategy-schema"),
    )


def adapt_article_metadata_to_structure(
    *,
    article_id: UUID,
    source: str,
    source_url: str,
    source_article_id: str | None,
    schema_version: str,
) -> ArticleStructureContract:
    article_ref = ArticleReference(
        article_id=article_id,
        source=source,
        source_article_id=source_article_id,
        source_url=source_url,
    )
    structure_id = _compatibility_uuid(f"article_structure:{article_id}:{schema_version}")
    return ArticleStructureContract(
        reference=ArticleStructureReference(
            article_structure_id=structure_id,
            article_id=article_id,
            prompt_run_id=_compatibility_uuid(f"prompt_run:{article_id}:{schema_version}"),
        ),
        article=article_ref,
        lifecycle_state=ArticleStructureLifecycleState.approved,
        schema_version=schema_version,
        prompt_version="legacy_article_metadata",
        provenance=SourceProvenance(
            fact_sources=[FactSourceRecord(fact_source=FactSource.legacy_import, source_ref=f"article_metadata:{schema_version}")]
        ),
        quality=QualityRecord(status=QualityStatus.partial, reason="legacy article metadata compatibility"),
        audit=AuditStamp(created_by="legacy-article-metadata", updated_by="legacy-article-metadata"),
    )
