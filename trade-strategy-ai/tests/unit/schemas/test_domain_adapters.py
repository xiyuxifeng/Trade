from __future__ import annotations

from datetime import date
from uuid import uuid4

from api.schemas.article_metadata import build_article_metadata_candidate_response
from api.schemas.market import build_market_regime_summary
from src.domain.contracts import (
    ArticleStructureContract,
    MarketStateContract,
    QualityRecord,
    SourceProvenance,
)
from src.domain.enums import FactSource, MarketObservationState, QualityStatus
from src.domain.references import ArticleReference, ArticleStructureReference, MarketSnapshotReference, MarketStateReference
from src.domain.value_objects import AuditStamp, FactSourceRecord


def test_article_metadata_api_response_uses_explicit_adapter() -> None:
    article_id = uuid4()
    structure = ArticleStructureContract(
        reference=ArticleStructureReference(
            article_structure_id=uuid4(),
            article_id=article_id,
            prompt_run_id=uuid4(),
        ),
        article=ArticleReference(
            article_id=article_id,
            source="tgb",
            source_article_id="10461311",
            source_url="https://www.tgb.cn/a/10461311",
        ),
        lifecycle_state="approved",
        schema_version="article-structure-v1",
        prompt_version="article_analysis_v1",
        provenance=SourceProvenance(
            fact_sources=[FactSourceRecord(fact_source=FactSource.legacy_import, source_ref="article_metadata:v2")]
        ),
        quality=QualityRecord(status=QualityStatus.partial, reason="legacy article metadata selection"),
        audit=AuditStamp(created_by="migration", updated_by="migration"),
        missing_fields=["market_state"],
        inferred_fields=["holding_period"],
    )

    response = build_article_metadata_candidate_response(structure)

    assert response.schema_version == "article-structure-v1"
    assert response.strategy_rules_count == 0
    assert response.preconditions_count == 0


def test_market_api_response_uses_explicit_adapter() -> None:
    snapshot_ref = MarketSnapshotReference(
        market_snapshot_id=uuid4(),
        legacy_snapshot_id="snapshot-cn-2026-06-14-am",
        market="CN",
        trade_date=date(2026, 6, 14),
        slot="09-25",
        data_version="v1",
    )
    contract = MarketStateContract(
        reference=MarketStateReference(
            market_state_id=uuid4(),
            market_snapshot_id=snapshot_ref.market_snapshot_id,
            definition_version="market-state-v1",
            legacy_regime_id="regime-cn-2026-06-14-am",
        ),
        market_snapshot=snapshot_ref,
        lifecycle_state=MarketObservationState.valid,
        primary_label="trend_up",
        confidence=0.83,
        provenance=SourceProvenance(
            fact_sources=[FactSourceRecord(fact_source=FactSource.program_observation, source_ref="market_regimes")]
        ),
        quality=QualityRecord(status=QualityStatus.complete),
        audit=AuditStamp(created_by="system", updated_by="system"),
    )

    response = build_market_regime_summary(contract)

    assert response.regime_id == "regime-cn-2026-06-14-am"
    assert response.snapshot_id == "snapshot-cn-2026-06-14-am"
    assert response.regime_version == "market-state-v1"
    assert response.market == "CN"
