from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.adapters import adapt_market_regime_record_to_canonical, adapt_strategy_version_orm_to_canonical
from src.domain.contracts import DatasetSnapshotContract
from src.domain.enums import DatasetSnapshotState, FactSource, QualityStatus
from src.domain.references import DatasetSnapshotReference, MarketSnapshotReference
from src.domain.value_objects import AuditStamp, FactSourceRecord, QualityRecord, SourceProvenance
from src.models.market_data_snapshot import MarketSnapshot
from src.models.market_dataset import MarketDataset
from src.models.market_regime_record import MarketRegimeRecord
from src.models.trader_strategy_version import TraderStrategyVersion


def _compatibility_uuid(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"trade-strategy-ai:{value}")


def _dataset_quality_status(value: str | None) -> QualityStatus:
    if value == "ok":
        return QualityStatus.complete
    if value == "partial":
        return QualityStatus.partial
    if value == "ambiguous":
        return QualityStatus.ambiguous
    if value == "unresolved":
        return QualityStatus.unresolved
    return QualityStatus.legacy_only


def _adapt_market_dataset_to_canonical(dataset: MarketDataset) -> DatasetSnapshotContract:
    return DatasetSnapshotContract(
        reference=DatasetSnapshotReference(
            dataset_snapshot_id=_compatibility_uuid(f"dataset_snapshot:{dataset.dataset_id}"),
            content_fingerprint=f"legacy:{dataset.dataset_id}",
        ),
        lifecycle_state=DatasetSnapshotState.partial if dataset.quality_status == "partial" else DatasetSnapshotState.ready,
        market_state_definition_version=None,
        provenance=SourceProvenance(
            fact_sources=[FactSourceRecord(fact_source=FactSource.legacy_import, source_ref="market_datasets")],
            source_type="orm",
            source_ref=dataset.dataset_id,
        ),
        quality=QualityRecord(
            status=_dataset_quality_status(dataset.quality_status),
            reason="legacy market dataset compatibility",
        ),
        audit=AuditStamp(
            created_at=dataset.created_at or datetime.now(UTC),
            updated_at=dataset.updated_at or datetime.now(UTC),
            created_by="legacy-market-dataset-repository",
            updated_by="legacy-market-dataset-repository",
        ),
    )


class LegacyDatasetCompatibilityAdapter:
    async def list_compatibility_records(
        self,
        session: AsyncSession,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DatasetSnapshotContract]:
        stmt = select(MarketDataset).order_by(MarketDataset.created_at.desc()).offset(offset).limit(limit)
        rows = await session.scalars(stmt)
        return [_adapt_market_dataset_to_canonical(row) for row in rows.all()]


class LegacyStrategyVersionCompatibilityAdapter:
    async def list_compatibility_records(
        self,
        session: AsyncSession,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[object]:
        stmt = (
            select(TraderStrategyVersion)
            .order_by(TraderStrategyVersion.strategy_date.desc(), TraderStrategyVersion.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = await session.scalars(stmt)
        results = []
        for row in rows.all():
            strategy_id = _compatibility_uuid(f"strategy:{row.trader_id}")
            strategy_version_id = _compatibility_uuid(f"strategy_version:{row.trader_id}:{row.strategy_date}:{row.version_name}")
            results.append(
                adapt_strategy_version_orm_to_canonical(
                    row,
                    strategy_id=strategy_id,
                    strategy_version_id=strategy_version_id,
                    version_no=1,
                )
            )
        return results


class LegacyMarketStateCompatibilityAdapter:
    async def list_compatibility_records(
        self,
        session: AsyncSession,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[object]:
        regime_stmt = (
            select(MarketRegimeRecord)
            .order_by(MarketRegimeRecord.trade_date.desc(), MarketRegimeRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        regimes = await session.scalars(regime_stmt)
        snapshot_ids = sorted({row.snapshot_id for row in regimes.all()})
        if not snapshot_ids:
            return []

        snapshot_stmt = select(MarketSnapshot).where(MarketSnapshot.snapshot_id.in_(snapshot_ids))
        snapshots = await session.scalars(snapshot_stmt)
        snapshot_map = {snapshot.snapshot_id: snapshot for snapshot in snapshots.all()}

        results = []
        regime_rows = await session.scalars(regime_stmt)
        for row in regime_rows.all():
            snapshot = snapshot_map.get(row.snapshot_id)
            if snapshot is None:
                continue
            snapshot_ref = MarketSnapshotReference(
                market_snapshot_id=snapshot.id,
                legacy_snapshot_id=snapshot.snapshot_id,
                market=snapshot.market,
                trade_date=snapshot.trade_date,
                slot=snapshot.slot,
                data_version=snapshot.data_version,
            )
            results.append(
                adapt_market_regime_record_to_canonical(
                    row,
                    market_snapshot_ref=snapshot_ref,
                    definition_version=row.regime_version,
                )
            )
        return results
