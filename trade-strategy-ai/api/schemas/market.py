from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
