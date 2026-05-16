from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.repositories import (
    MarketDataQualityRepository,
    MarketDatasetRepository,
    MarketSnapshotItemRepository,
    MarketSnapshotRepository,
    MarketSnapshotSectionRepository,
)
from src.db.session import get_session_factory
from src.services.base import BaseService, ServiceResult


def _normalize_date(value: Any) -> date | None:
    """把日期参数归一化为 date。"""
    if value in {None, ""}:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"invalid date value: {value}")


def _contains_text(value: Any, needle: str) -> bool:
    """递归判断 payload 中是否包含指定文本。"""
    if value is None:
        return False
    if isinstance(value, str):
        return needle.lower() in value.lower()
    if isinstance(value, dict):
        return any(_contains_text(item, needle) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_text(item, needle) for item in value)
    return needle.lower() in str(value).lower()


class MarketSnapshotQueryService(BaseService):
    """市场快照查询服务。"""

    service_name = "market-snapshot-query"

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        snapshot_repository: MarketSnapshotRepository | None = None,
        section_repository: MarketSnapshotSectionRepository | None = None,
        item_repository: MarketSnapshotItemRepository | None = None,
        dataset_repository: MarketDatasetRepository | None = None,
        quality_repository: MarketDataQualityRepository | None = None,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        self._snapshot_repository = snapshot_repository or MarketSnapshotRepository()
        self._section_repository = section_repository or MarketSnapshotSectionRepository()
        self._item_repository = item_repository or MarketSnapshotItemRepository()
        self._dataset_repository = dataset_repository or MarketDatasetRepository()
        self._quality_repository = quality_repository or MarketDataQualityRepository()

    def _error(
        self,
        *,
        status: str,
        error_type: str,
        message: str,
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """构建结构化错误结果。"""
        return ServiceResult(
            status=status,  # type: ignore[arg-type]
            message=message,
            payload={
                "error": {
                    "type": error_type,
                    "message": message,
                    "detail": detail,
                    "metadata": metadata or {},
                }
            },
        )

    def _empty_data(
        self,
        *,
        message: str,
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """构建空数据错误。"""
        return self._error(
            status="error",
            error_type="empty_data",
            message=message,
            detail=detail,
            metadata=metadata,
        )

    def _partial_data(
        self,
        *,
        message: str,
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """构建部分数据错误。"""
        return self._error(
            status="partial",
            error_type="partial_data",
            message=message,
            detail=detail,
            metadata=metadata,
        )

    def _page_payload(self, *, total: int, limit: int, offset: int, count: int) -> dict[str, int]:
        """构建分页信息。"""
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": count,
        }

    def _snapshot_summary(self, snapshot) -> dict[str, Any]:
        """构建 snapshot 列表项。"""
        return {
            "snapshot_id": snapshot.snapshot_id,
            "trade_date": snapshot.trade_date.isoformat() if snapshot.trade_date else None,
            "market": snapshot.market,
            "data_version": snapshot.data_version,
            "quality_status": snapshot.quality_status,
            "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
            "section_count": snapshot.section_count,
            "available_section_count": snapshot.available_section_count,
            "partial_section_count": snapshot.partial_section_count,
            "missing_section_count": snapshot.missing_section_count,
            "profile_id": snapshot.profile_id,
        }

    def _section_summary(self, section) -> dict[str, Any]:
        """构建 section 列表项。"""
        return {
            "id": str(section.id),
            "snapshot_id": section.snapshot_id,
            "section_id": section.section_id,
            "provider": section.provider,
            "source_time": section.source_time.isoformat() if section.source_time else None,
            "record_count": section.record_count,
            "missing_reason": section.missing_reason,
            "quality_status": section.quality_status,
            "section_version": section.section_version,
            "storage_ref": section.storage_ref,
        }

    def _item_summary(self, item) -> dict[str, Any]:
        """构建 item 列表项。"""
        return {
            "id": str(item.id),
            "snapshot_id": item.snapshot_id,
            "section_id": item.section_id,
            "dataset_id": item.dataset_id,
            "symbol": item.symbol,
            "item_key": item.item_key,
            "item_type": item.item_type,
            "source_time": item.source_time.isoformat() if item.source_time else None,
            "quality_status": item.quality_status,
            "payload_json": item.payload_json,
        }

    def _matches_filters(
        self,
        *,
        sections: list[Any],
        items: list[Any],
        section: str | None,
        symbol: str | None,
        topic: str | None,
    ) -> bool:
        """判断 snapshot 是否命中过额外过滤条件。"""
        if section and not any(section_obj.section_id == section for section_obj in sections):
            return False
        if symbol and not any(item_obj.symbol == symbol or _contains_text(item_obj.payload_json, symbol) for item_obj in items):
            return False
        if topic and not any(_contains_text(item_obj.payload_json, topic) for item_obj in items):
            return False
        return True

    async def _load_snapshot_context(self, session: AsyncSession, snapshot_id: str) -> tuple[Any, list[Any], list[Any], Any, Any]:
        """一次性加载 snapshot 的相关上下文。"""
        snapshot = await self._snapshot_repository.get_by_snapshot_id(session, snapshot_id)
        if snapshot is None:
            return None, [], [], None, None
        sections = await self._section_repository.list_by_snapshot_id(session, snapshot_id)
        items = await self._item_repository.list_by_snapshot_id(session, snapshot_id)
        quality = await self._quality_repository.get_by_snapshot_id(session, snapshot_id)
        dataset = await self._dataset_repository.get_by_dataset_id(session, f"{snapshot_id}:dataset")
        return snapshot, sections, items, quality, dataset

    async def list_snapshots(
        self,
        *,
        trade_date: date | str | None = None,
        market: str | None = None,
        section: str | None = None,
        symbol: str | None = None,
        topic: str | None = None,
        quality_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ServiceResult:
        """查询 Market Snapshot 列表。"""
        if limit < 1 or offset < 0:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="limit must be >= 1 and offset must be >= 0",
                metadata={"limit": limit, "offset": offset},
            )

        try:
            normalized_trade_date = _normalize_date(trade_date)
        except ValueError as exc:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid trade_date",
                detail=str(exc),
                metadata={"trade_date": trade_date},
            )

        async with self._session_factory() as session:
            snapshots = await self._snapshot_repository.list_snapshots(
                session,
                trade_date=normalized_trade_date,
                market=market,
                quality_status=quality_status,
            )

            filtered: list[Any] = []
            section_cache: dict[str, list[Any]] = {}
            item_cache: dict[str, list[Any]] = {}

            for snapshot in snapshots:
                if section or symbol or topic:
                    snapshot_sections = section_cache.get(snapshot.snapshot_id)
                    if snapshot_sections is None:
                        snapshot_sections = await self._section_repository.list_by_snapshot_id(session, snapshot.snapshot_id)
                        section_cache[snapshot.snapshot_id] = snapshot_sections
                    snapshot_items = item_cache.get(snapshot.snapshot_id)
                    if snapshot_items is None:
                        snapshot_items = await self._item_repository.list_by_snapshot_id(session, snapshot.snapshot_id)
                        item_cache[snapshot.snapshot_id] = snapshot_items
                    if not self._matches_filters(
                        sections=snapshot_sections,
                        items=snapshot_items,
                        section=section,
                        symbol=symbol,
                        topic=topic,
                    ):
                        continue
                filtered.append(snapshot)

            total = len(filtered)
            if total == 0:
                return self._empty_data(
                    message="market snapshot list is empty",
                    detail="no snapshots matched the query",
                    metadata={
                        "trade_date": normalized_trade_date.isoformat() if normalized_trade_date else None,
                        "market": market,
                        "section": section,
                        "symbol": symbol,
                        "topic": topic,
                        "quality_status": quality_status,
                    },
                )
            page_items = filtered[offset : offset + limit]
            return ServiceResult(
                status="ok",
                message="market snapshot list loaded",
                payload={
                    "filters": {
                        "trade_date": normalized_trade_date.isoformat() if normalized_trade_date else None,
                        "market": market,
                        "section": section,
                        "symbol": symbol,
                        "topic": topic,
                        "quality_status": quality_status,
                    },
                    "page": self._page_payload(total=total, limit=limit, offset=offset, count=len(page_items)),
                    "items": [self._snapshot_summary(snapshot) for snapshot in page_items],
                },
            )

    async def get_snapshot_detail(self, snapshot_id: str) -> ServiceResult:
        """查询单个 snapshot 的详情。"""
        async with self._session_factory() as session:
            snapshot, sections, items, quality, dataset = await self._load_snapshot_context(session, snapshot_id)

        if snapshot is None:
            return self._error(
                status="partial",
                error_type="snapshot_not_found",
                message="snapshot not found",
                detail=snapshot_id,
                metadata={"snapshot_id": snapshot_id},
            )

        warnings: list[str] = []
        if quality is None:
            warnings.append("quality report missing")
        if dataset is None:
            warnings.append("dataset missing")
        if not sections:
            warnings.append("sections missing")
        if warnings:
            return self._partial_data(
                message="market snapshot detail is partial",
                detail="; ".join(warnings),
                metadata={"snapshot_id": snapshot_id, "warnings": warnings},
            )

        return ServiceResult(
            status="ok",
            message="market snapshot detail loaded",
            payload={
                "snapshot": self._snapshot_summary(snapshot),
                "sections": [self._section_summary(section) for section in sections],
                "item_count": len(items),
                "quality_report": quality.to_dict() if quality else None,
                "dataset": dataset.to_dict() if dataset else None,
                "warnings": warnings,
            },
            warnings=warnings,
        )

    async def list_snapshot_sections(self, snapshot_id: str, *, limit: int = 200, offset: int = 0) -> ServiceResult:
        """查询 snapshot 的 section 列表。"""
        if limit < 1 or offset < 0:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="limit must be >= 1 and offset must be >= 0",
                metadata={"limit": limit, "offset": offset},
            )

        async with self._session_factory() as session:
            snapshot = await self._snapshot_repository.get_by_snapshot_id(session, snapshot_id)
            if snapshot is None:
                return self._error(
                    status="partial",
                    error_type="snapshot_not_found",
                    message="snapshot not found",
                    detail=snapshot_id,
                    metadata={"snapshot_id": snapshot_id},
                )
            sections = await self._section_repository.list_by_snapshot_id(session, snapshot_id)

        page_items = sections[offset : offset + limit]
        if not page_items:
            return self._empty_data(
                message="snapshot sections are empty",
                detail=snapshot_id,
                metadata={"snapshot_id": snapshot_id},
            )
        return ServiceResult(
            status="ok",
            message="snapshot sections loaded",
            payload={
                "snapshot_id": snapshot_id,
                "page": self._page_payload(total=len(sections), limit=limit, offset=offset, count=len(page_items)),
                "items": [self._section_summary(section) for section in page_items],
            },
        )

    async def get_snapshot_section(
        self,
        snapshot_id: str,
        section_id: str,
        *,
        symbol: str | None = None,
        topic: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ServiceResult:
        """查询 snapshot 内单个 section 的详情。"""
        if limit < 1 or offset < 0:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="limit must be >= 1 and offset must be >= 0",
                metadata={"limit": limit, "offset": offset},
            )

        async with self._session_factory() as session:
            snapshot = await self._snapshot_repository.get_by_snapshot_id(session, snapshot_id)
            if snapshot is None:
                return self._error(
                    status="partial",
                    error_type="snapshot_not_found",
                    message="snapshot not found",
                    detail=snapshot_id,
                    metadata={"snapshot_id": snapshot_id},
                )
            section = await self._section_repository.get_by_snapshot_and_section(session, snapshot_id, section_id)
            if section is None:
                return self._error(
                    status="partial",
                    error_type="section_not_found",
                    message="section not found",
                    detail=section_id,
                    metadata={"snapshot_id": snapshot_id, "section_id": section_id},
                )
            items = await self._item_repository.list_by_section(session, snapshot_id, section_id)

        filtered = []
        for item in items:
            if symbol and not (item.symbol == symbol or _contains_text(item.payload_json, symbol)):
                continue
            if topic and not _contains_text(item.payload_json, topic):
                continue
            filtered.append(item)

        if not filtered:
            return self._empty_data(
                message="snapshot section is empty",
                detail=section_id,
                metadata={"snapshot_id": snapshot_id, "section_id": section_id, "filters": {"symbol": symbol, "topic": topic}},
            )
        page_items = filtered[offset : offset + limit]
        return ServiceResult(
            status="ok",
            message="snapshot section loaded",
            payload={
                "snapshot_id": snapshot_id,
                "section": self._section_summary(section),
                "page": self._page_payload(total=len(filtered), limit=limit, offset=offset, count=len(page_items)),
                "items": [self._item_summary(item) for item in page_items],
                "filters": {"symbol": symbol, "topic": topic},
            },
        )

    async def list_datasets(
        self,
        *,
        trade_date: date | str | None = None,
        market: str | None = None,
        dataset_type: str | None = None,
        quality_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ServiceResult:
        """查询市场数据集列表。"""
        if limit < 1 or offset < 0:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="limit must be >= 1 and offset must be >= 0",
                metadata={"limit": limit, "offset": offset},
            )

        try:
            normalized_trade_date = _normalize_date(trade_date)
        except ValueError as exc:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid trade_date",
                detail=str(exc),
                metadata={"trade_date": trade_date},
            )

        async with self._session_factory() as session:
            datasets = await self._dataset_repository.list_datasets(
                session,
                trade_date=normalized_trade_date,
                market=market,
                dataset_type=dataset_type,
                quality_status=quality_status,
            )

        page_items = datasets[offset : offset + limit]
        return ServiceResult(
            status="ok",
            message="market dataset list loaded",
            payload={
                "filters": {
                    "trade_date": normalized_trade_date.isoformat() if normalized_trade_date else None,
                    "market": market,
                    "dataset_type": dataset_type,
                    "quality_status": quality_status,
                },
                "page": self._page_payload(total=len(datasets), limit=limit, offset=offset, count=len(page_items)),
                "items": [dataset.to_dict() for dataset in page_items],
            },
        )

    async def get_dataset_detail(self, dataset_id: str, *, limit: int = 100, offset: int = 0) -> ServiceResult:
        """查询单个 dataset 的详情。"""
        if limit < 1 or offset < 0:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="limit must be >= 1 and offset must be >= 0",
                metadata={"limit": limit, "offset": offset},
            )

        async with self._session_factory() as session:
            dataset = await self._dataset_repository.get_by_dataset_id(session, dataset_id)
            if dataset is None:
                return self._error(
                    status="partial",
                    error_type="dataset_not_found",
                    message="dataset not found",
                    detail=dataset_id,
                    metadata={"dataset_id": dataset_id},
                )
            items = await self._item_repository.list_by_dataset_id(session, dataset_id)
            snapshot = await self._snapshot_repository.get_by_snapshot_id(session, dataset.snapshot_id) if dataset.snapshot_id else None

        if not items:
            return self._empty_data(
                message="dataset is empty",
                detail=dataset_id,
                metadata={"dataset_id": dataset_id},
            )
        page_items = items[offset : offset + limit]
        warnings = ["source snapshot missing"] if dataset.snapshot_id and snapshot is None else []
        if warnings:
            return self._partial_data(
                message="market dataset detail is partial",
                detail="; ".join(warnings),
                metadata={"dataset_id": dataset_id, "warnings": warnings},
            )
        return ServiceResult(
            status="ok",
            message="market dataset detail loaded",
            payload={
                "dataset": dataset.to_dict(),
                "snapshot": self._snapshot_summary(snapshot) if snapshot is not None else None,
                "page": self._page_payload(total=len(items), limit=limit, offset=offset, count=len(page_items)),
                "items": [self._item_summary(item) for item in page_items],
                "warnings": warnings,
            },
            warnings=warnings,
        )

    async def get_quality_report(self, snapshot_id: str) -> ServiceResult:
        """查询质量报告。"""
        async with self._session_factory() as session:
            snapshot = await self._snapshot_repository.get_by_snapshot_id(session, snapshot_id)
            if snapshot is None:
                return self._error(
                    status="partial",
                    error_type="snapshot_not_found",
                    message="snapshot not found",
                    detail=snapshot_id,
                    metadata={"snapshot_id": snapshot_id},
                )
            quality = await self._quality_repository.get_by_snapshot_id(session, snapshot_id)

        if quality is None:
            return self._partial_data(
                message="quality report not found",
                detail=snapshot_id,
                metadata={"snapshot_id": snapshot_id},
            )

        return ServiceResult(
            status="ok",
            message="quality report loaded",
            payload={"quality_report": quality.to_dict()},
        )
