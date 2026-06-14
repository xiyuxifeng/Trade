from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, date, datetime, timezone
from pathlib import Path
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
from src.models.market_data_quality_report import MarketDataQualityReport
from src.models.market_dataset import MarketDataset
from src.models.market_data_snapshot import MarketSnapshot as MarketSnapshotRecord
from src.models.market_data_snapshot_item import MarketSnapshotItem
from src.models.market_data_snapshot_section import MarketSnapshotSection
from src.models.market_snapshot import MarketSnapshot
from src.services.base import BaseService, ServiceResult
from src.common.stage2_writer_routing import (
    canonical_write_scope,
    canonical_writer_enabled,
)


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _to_plain(value.to_dict())
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


class MarketDataStorageService(BaseService):
    """市场数据 DB 持久化服务。"""

    service_name = "market-data-storage"

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

    def _dataset_id_for_snapshot(self, snapshot: MarketSnapshot) -> str:
        """生成 snapshot 级 dataset_id。"""
        return f"{snapshot.snapshot_id}:dataset"

    def _build_snapshot_record(self, snapshot: MarketSnapshot, *, summary_payload: dict[str, Any] | None, quality_payload: dict[str, Any] | None) -> MarketSnapshotRecord:
        """构建 snapshot 主表记录。"""
        summary = summary_payload or {}
        quality = quality_payload or {}
        captured_at = snapshot.created_at or datetime.now(UTC)
        manifest = {
            "sections": sorted(snapshot.sections),
            "providers": list(snapshot.provider_sources),
            "summary": summary,
        }
        return MarketSnapshotRecord(
            snapshot_id=snapshot.snapshot_id,
            trade_date=date.fromisoformat(snapshot.trade_date) if isinstance(snapshot.trade_date, str) else snapshot.trade_date,
            market=snapshot.market,
            profile_id=snapshot.metadata.get("profile_id") if isinstance(snapshot.metadata, dict) else None,
            data_version=snapshot.data_version,
            slot=snapshot.metadata.get("slot", "17-30") if isinstance(snapshot.metadata, dict) else "17-30",
            quality_status=summary.get("overall_status") or snapshot.data_quality.get("overall_status", "partial"),
            provider_sources=list(snapshot.provider_sources),
            section_count=int(summary.get("section_count", len(snapshot.sections))),
            available_section_count=int(summary.get("available_section_count", 0)),
            partial_section_count=int(summary.get("partial_section_count", 0)),
            missing_section_count=int(summary.get("missing_section_count", 0)),
            storage_ref={
                "snapshot_id": snapshot.snapshot_id,
                "trade_date": snapshot.trade_date,
                "market": snapshot.market,
            },
            summary_artifact_ref={
                "snapshot_id": snapshot.snapshot_id,
                "artifact_type": "snapshot-summary-json",
            },
            quality_artifact_ref={
                "snapshot_id": snapshot.snapshot_id,
                "artifact_type": "snapshot-quality-json",
            },
            data_quality={**snapshot.data_quality, "quality_report": quality},
            captured_at=captured_at,
            available_at=captured_at,
            effective_at=captured_at,
            content_fingerprint=hashlib.sha256(
                json.dumps(
                    {
                        "snapshot_id": snapshot.snapshot_id,
                        "data_version": snapshot.data_version,
                        "manifest": manifest,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                ).encode("utf-8")
            ).hexdigest(),
            manifest_json=manifest,
        )

    def _build_section_record(self, snapshot: MarketSnapshot, section_id: str, section) -> MarketSnapshotSection:
        """构建 section 表记录。"""
        return MarketSnapshotSection(
            snapshot_id=snapshot.snapshot_id,
            section_id=section_id,
            provider=section.provider,
            source_time=section.source_time,
            record_count=section.record_count,
            missing_reason=section.missing_reason,
            quality_status=section.quality_status,
            section_version=section.metadata.get("section_version") if isinstance(section.metadata, dict) else None,
            storage_ref={
                "snapshot_id": snapshot.snapshot_id,
                "section_id": section_id,
            },
            payload_json=_to_plain(section.payload),
        )

    def _extract_symbol_from_payload(self, payload: Any) -> str | None:
        """从 payload 中提取可用于查询的 symbol。"""
        if not isinstance(payload, dict):
            return None
        for key in ("symbol", "StockID", "ZSCode", "code", "symbol_code"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _iter_section_items(self, snapshot: MarketSnapshot, section_id: str, section) -> Iterable[MarketSnapshotItem]:
        """把 section 拆为可查询 item。"""
        section_payload = section.payload if isinstance(section.payload, dict) else {}
        dataset_id = self._dataset_id_for_snapshot(snapshot)
        yield MarketSnapshotItem(
            snapshot_id=snapshot.snapshot_id,
            section_id=section_id,
            dataset_id=dataset_id,
            symbol=self._extract_symbol_from_payload(section_payload),
            item_key=f"{section_id}:summary",
            item_type=section_id,
            source_time=section.source_time,
            quality_status=section.quality_status,
            payload_json=_to_plain(section_payload),
        )

        list_keys = ("items", "topics", "constituents", "symbols", "bars", "rows", "list")
        for list_key in list_keys:
            value = section_payload.get(list_key)
            if not isinstance(value, list):
                continue
            for index, entry in enumerate(value):
                if not isinstance(entry, dict):
                    entry = {"value": entry}
                yield MarketSnapshotItem(
                    snapshot_id=snapshot.snapshot_id,
                    section_id=section_id,
                    dataset_id=dataset_id,
                    symbol=self._extract_symbol_from_payload(entry),
                    item_key=f"{section_id}:{list_key}:{index}",
                    item_type=list_key,
                    source_time=section.source_time,
                    quality_status=section.quality_status,
                    payload_json=_to_plain(entry),
                )

    async def save_snapshot(
        self,
        snapshot: MarketSnapshot,
        *,
        summary_payload: dict[str, Any] | None = None,
        quality_payload: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """把结构化 Market Snapshot 写入数据库。"""
        if not snapshot.snapshot_id:
            raise ValueError("snapshot.snapshot_id is required")

        snapshot_record = self._build_snapshot_record(snapshot, summary_payload=summary_payload, quality_payload=quality_payload)
        dataset_id = self._dataset_id_for_snapshot(snapshot)
        dataset_record = MarketDataset(
            dataset_id=dataset_id,
            dataset_type="market_snapshot",
            trade_date=snapshot_record.trade_date,
            market=snapshot.market,
            source="snapshot-build",
            storage_ref={
                "snapshot_id": snapshot.snapshot_id,
                "dataset_id": dataset_id,
            },
            snapshot_id=snapshot.snapshot_id,
            profile_id=snapshot_record.profile_id,
            quality_status=snapshot_record.quality_status,
        )
        quality_record = MarketDataQualityReport(
            snapshot_id=snapshot.snapshot_id,
            overall_status=snapshot_record.quality_status,
            warning_count=len([section for section in snapshot.sections.values() if section.quality_status != "ok"]),
            error_count=len([section for section in snapshot.sections.values() if section.quality_status == "missing"]),
            section_summary_json={
                section_id: {
                    "provider": section.provider,
                    "quality_status": section.quality_status,
                    "record_count": section.record_count,
                    "missing_reason": section.missing_reason,
                }
                for section_id, section in snapshot.sections.items()
            },
            report_json=quality_payload or {},
            storage_ref={
                "snapshot_id": snapshot.snapshot_id,
                "dataset_id": dataset_id,
                "kind": "quality_report",
            },
        )

        async with self._session_factory() as session:
            async with session.begin():
                with canonical_write_scope("market_snapshot", self.service_name):
                    await self._snapshot_repository.upsert_snapshot(session, snapshot_record)
                    section_count = 0
                    item_count = 0
                    for section_id, section in snapshot.sections.items():
                        section_record = self._build_section_record(snapshot, section_id, section)
                        await self._section_repository.upsert_section(session, section_record)
                        section_count += 1

                        for item_record in self._iter_section_items(snapshot, section_id, section):
                            await self._item_repository.upsert_item(session, item_record)
                            item_count += 1
                    await self._quality_repository.upsert_report(session, quality_record)

                if not canonical_writer_enabled():
                    await self._dataset_repository.upsert_dataset(session, dataset_record)

        return ServiceResult(
            status="ok",
            message="market snapshot stored",
            payload={
                "snapshot_id": snapshot.snapshot_id,
                "dataset_id": dataset_id,
                "section_count": section_count,
                "item_count": item_count,
                "storage_ref": snapshot_record.storage_ref,
                "summary_artifact_ref": snapshot_record.summary_artifact_ref,
                "quality_artifact_ref": snapshot_record.quality_artifact_ref,
            },
        )

    async def load_snapshot(self, snapshot_id: str) -> ServiceResult:
        """按 snapshot_id 读取 DB 中的快照摘要。"""
        async with self._session_factory() as session:
            snapshot = await self._snapshot_repository.get_by_snapshot_id(session, snapshot_id)
            sections = await self._section_repository.list_by_snapshot_id(session, snapshot_id)
            items = await self._item_repository.list_by_snapshot_id(session, snapshot_id)
            quality = await self._quality_repository.get_by_snapshot_id(session, snapshot_id)
            dataset = await self._dataset_repository.get_by_dataset_id(session, f"{snapshot_id}:dataset")

        if snapshot is None:
            return ServiceResult(status="error", message="snapshot not found", payload={"snapshot_id": snapshot_id})

        return ServiceResult(
            status="ok",
            message="market snapshot loaded",
            payload={
                "snapshot": snapshot.to_dict(),
                "sections": [section.to_dict() for section in sections],
                "items": [item.to_dict() for item in items],
                "quality_report": quality.to_dict() if quality else None,
                "dataset": dataset.to_dict() if dataset else None,
            },
        )
