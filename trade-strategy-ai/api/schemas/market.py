from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.contracts import MarketStateContract


class MarketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    market: str
    timeframe: str
    traded_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    turnover: Decimal
    source: str


class MarketFilter(BaseModel):
    symbol: str
    timeframe: str = "1d"
    market: str | None = None


class MarketQueryPage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    limit: int
    offset: int
    count: int


class MarketQueryError(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    message: str
    detail: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketSnapshotListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    trade_date: str | None = None
    market: str
    data_version: str
    quality_status: str
    created_at: str | None = None
    section_count: int
    available_section_count: int
    partial_section_count: int
    missing_section_count: int
    profile_id: str | None = None


class MarketSnapshotSectionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    snapshot_id: str
    section_id: str
    provider: str | None = None
    source_time: str | None = None
    record_count: int
    missing_reason: str | None = None
    quality_status: str
    section_version: str | None = None
    storage_ref: dict[str, Any] = Field(default_factory=dict)


class MarketSnapshotItemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    snapshot_id: str
    section_id: str
    dataset_id: str | None = None
    symbol: str | None = None
    item_key: str
    item_type: str | None = None
    source_time: str | None = None
    quality_status: str
    payload_json: dict[str, Any] = Field(default_factory=dict)


class MarketSnapshotDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot: MarketSnapshotListItem
    sections: list[MarketSnapshotSectionSummary] = Field(default_factory=list)
    item_count: int = 0
    quality_report: dict[str, Any] | None = None
    dataset: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class MarketSnapshotListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filters: dict[str, Any] = Field(default_factory=dict)
    page: MarketQueryPage
    items: list[MarketSnapshotListItem] = Field(default_factory=list)


class MarketSnapshotSectionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    page: MarketQueryPage
    items: list[MarketSnapshotSectionSummary] = Field(default_factory=list)


class MarketSnapshotSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    section: MarketSnapshotSectionSummary
    page: MarketQueryPage
    items: list[MarketSnapshotItemSummary] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)


class MarketDatasetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    dataset_type: str
    trade_date: str
    market: str
    source: str | None = None
    storage_ref: dict[str, Any] = Field(default_factory=dict)
    snapshot_id: str | None = None
    profile_id: str | None = None
    quality_status: str
    created_at: str | None = None
    updated_at: str | None = None


class MarketDatasetListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filters: dict[str, Any] = Field(default_factory=dict)
    page: MarketQueryPage
    items: list[MarketDatasetSummary] = Field(default_factory=list)


class MarketDatasetDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset: MarketDatasetSummary
    snapshot: MarketSnapshotListItem | None = None
    page: MarketQueryPage
    items: list[MarketSnapshotItemSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MarketSnapshotQualityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quality_report: dict[str, Any]


class MarketRegimeFeatureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    snapshot_id: str
    trade_date: str
    market: str
    feature_version: str
    quality_status: str
    available_feature_count: int
    partial_feature_count: int
    missing_feature_count: int
    feature_payload_json: dict[str, Any] = Field(default_factory=dict)
    summary_json: dict[str, Any] = Field(default_factory=dict)
    storage_ref: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class MarketRegimeFeatureListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filters: dict[str, Any] = Field(default_factory=dict)
    page: MarketQueryPage
    items: list[MarketRegimeFeatureSummary] = Field(default_factory=list)


class MarketRegimeFeatureDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature: MarketRegimeFeatureSummary
    feature_payload_json: dict[str, Any] = Field(default_factory=dict)
    summary_json: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class MarketRegimeEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_key: str
    feature_value: Any
    source_section: str
    source_field: str | None = None
    contribution: float = 0.0
    note: str | None = None


class MarketRegimeLabel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    label_type: str
    score: float
    confidence: float
    status: str
    evidence: list[MarketRegimeEvidence] = Field(default_factory=list)
    reason: str = ""


class MarketRegimeFeature(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_key: str
    raw_value: Any
    normalized_value: Any | None = None
    source_section: str
    source_field: str | None = None
    source_version: str
    confidence: float
    weight: float = 1.0
    missing_reason: str | None = None


class MarketRegimeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    regime_id: str
    snapshot_id: str
    trade_date: str
    market: str
    regime_version: str
    source_feature_version: str
    primary_label: str
    labels: list[MarketRegimeLabel] = Field(default_factory=list)
    confidence: float
    quality_status: str
    missing_reason: str | None = None
    storage_ref: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class MarketRegimeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    regime: MarketRegimeSummary
    features: list[MarketRegimeFeature] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MarketRegimeListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filters: dict[str, Any] = Field(default_factory=dict)
    page: MarketQueryPage
    items: list[MarketRegimeSummary] = Field(default_factory=list)


class MarketBenchmarkOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    code: str
    market: str
    name: str
    security_type: str = "index"


class MarketBenchmarkOptionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    count: int
    items: list[MarketBenchmarkOption] = Field(default_factory=list)


class StockInfoStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    stock_count: int
    index_count: int
    benchmark_count: int
    expected_benchmark_count: int
    missing_benchmark_symbols: list[str] = Field(default_factory=list)
    latest_updated_at: str | None = None
    is_fresh: bool = False
    needs_refresh: bool = False
    message: str
    max_age_days: int


class StockInfoRefreshResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stock_stats: dict[str, int] = Field(default_factory=dict)
    index_stats: dict[str, int] = Field(default_factory=dict)
    status: StockInfoStatusResponse


class OhlcvSchedulerStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_id: str | None = None
    base_dir: str
    latest_trade_date: str | None = None
    latest_record_count: int = 0
    scheduler_started: bool = False
    scheduler_pre_market: str | None = None
    scheduler_post_close: str | None = None


class OhlcvSchedulerRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_id: str | None = None
    base_dir: str
    pre_market: str
    post_close: str
    started: bool = False
    scheduler_started: bool = False


def build_market_regime_summary(contract: MarketStateContract) -> MarketRegimeSummary:
    """将 canonical MarketState 兼容转换为旧 UI DTO。"""
    return MarketRegimeSummary(
        regime_id=contract.reference.legacy_regime_id or str(contract.reference.market_state_id),
        snapshot_id=contract.market_snapshot.legacy_snapshot_id,
        trade_date=contract.market_snapshot.trade_date.isoformat(),
        market=contract.market_snapshot.market,
        regime_version=contract.reference.definition_version,
        source_feature_version=contract.source_feature_version,
        primary_label=contract.primary_label,
        labels=[],
        confidence=contract.confidence,
        quality_status=contract.quality.status.value,
        missing_reason=contract.quality.reason,
        storage_ref={},
        created_at=contract.audit.created_at.isoformat(),
        updated_at=contract.audit.updated_at.isoformat(),
    )


class OhlcvSchedulerStopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_id: str | None = None
    base_dir: str
    started: bool = False
    pre_market: str | None = None
    post_close: str | None = None
