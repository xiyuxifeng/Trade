from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.common.paths import resolve_project_path
from src.db.repositories import MarketDatasetRepository, MarketRegimeRepository, MarketRegimeFeatureRepository, MarketSnapshotRepository
from src.db.session import get_session_factory
from src.models.market_dataset import MarketDataset
from src.models.market_regime_record import MarketRegimeRecord
from src.services.base import BaseService, ServiceResult
from src.services.market_regime_rules import score_market_regime
from src.common.stage2_writer_routing import (
    canonical_write_scope,
    canonical_writer_enabled,
)

DEFAULT_REGIME_VERSION = "market-regime-v3"
DEFAULT_FEATURE_VERSION = "market-regime-features-v3"
FULL_MARKET_FEATURE_VERSION = "market-regime-features-v3"


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _feature_version_for_regime_version(regime_version: str, feature_version: str) -> str:
    """根据 regime_version 推断 feature_version。"""
    if feature_version != DEFAULT_FEATURE_VERSION:
        return feature_version
    if regime_version.endswith("-v3"):
        return FULL_MARKET_FEATURE_VERSION
    return feature_version


class MarketRegimeService(BaseService):
    """Market Regime 生成与查询服务。"""

    service_name = "market-regime"

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        snapshot_repository: MarketSnapshotRepository | None = None,
        feature_repository: MarketRegimeFeatureRepository | None = None,
        regime_repository: MarketRegimeRepository | None = None,
        dataset_repository: MarketDatasetRepository | None = None,
        artifact_root: str | Path | None = None,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        self._snapshot_repository = snapshot_repository or MarketSnapshotRepository()
        self._feature_repository = feature_repository or MarketRegimeFeatureRepository()
        self._regime_repository = regime_repository or MarketRegimeRepository()
        self._dataset_repository = dataset_repository or MarketDatasetRepository()
        self._artifact_root = Path(artifact_root).expanduser().resolve() if artifact_root is not None else resolve_project_path("data/processed/market_regimes")

    def _error(
        self,
        *,
        status: str,
        error_type: str,
        message: str,
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult:
        """构造结构化错误结果。"""
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

    def _artifact_path(self, *, trade_date: date, snapshot_id: str, regime_version: str) -> Path:
        """返回 regime artifact 路径。"""
        return self._artifact_root / trade_date.isoformat() / snapshot_id / f"{regime_version}.json"

    def _artifact_ref(self, artifact_path: Path) -> dict[str, Any]:
        """返回 artifact 的安全引用。"""
        try:
            relative = artifact_path.relative_to(self._artifact_root)
        except ValueError:
            relative = artifact_path.name
        return {
            "artifact_type": "market-regime-json",
            "artifact_root": str(self._artifact_root.name or "market_regimes"),
            "relative_path": str(relative),
        }

    async def build_market_regime(
        self,
        *,
        snapshot_id: str,
        regime_version: str = DEFAULT_REGIME_VERSION,
        feature_version: str = DEFAULT_FEATURE_VERSION,
    ) -> ServiceResult:
        """基于指定 snapshot 和 feature version 生成 Market Regime。"""
        feature_version = _feature_version_for_regime_version(regime_version, feature_version)
        async with self._session_factory() as session:
            snapshot = await self._snapshot_repository.get_by_snapshot_id(session, snapshot_id)
            if snapshot is None:
                return self._error(
                    status="error",
                    error_type="snapshot_not_found",
                    message="snapshot not found",
                    detail=snapshot_id,
                    metadata={"snapshot_id": snapshot_id},
                )

            feature = await self._feature_repository.get_by_snapshot_and_version(session, snapshot_id, feature_version)
            if feature is None:
                return self._error(
                    status="error",
                    error_type="feature_not_found",
                    message="market regime feature not found",
                    detail=snapshot_id,
                    metadata={"snapshot_id": snapshot_id, "feature_version": feature_version},
                )

            evaluation = score_market_regime(
                feature.feature_payload_json or {},
                regime_version=regime_version,
                snapshot_id=snapshot.snapshot_id,
                trade_date=snapshot.trade_date,
                market=snapshot.market,
                source_feature_version=feature.feature_version,
            )
            regime = MarketRegimeRecord(
                regime_id=evaluation.regime_id or f"{snapshot.snapshot_id}:{regime_version}",
                market_snapshot_id=snapshot.id,
                snapshot_id=snapshot.snapshot_id,
                trade_date=snapshot.trade_date,
                market=snapshot.market,
                regime_version=regime_version,
                source_feature_version=evaluation.source_feature_version,
                primary_label=evaluation.primary_label,
                labels=evaluation.labels,
                features=evaluation.features,
                confidence=evaluation.confidence,
                quality_status=evaluation.quality_status,
                missing_reason=evaluation.missing_reason,
                storage_ref={"snapshot_id": snapshot.snapshot_id, "regime_version": regime_version, "feature_version": feature.feature_version},
                available_at=snapshot.available_at,
            )
            dataset_record = MarketDataset(
                dataset_id=f"{snapshot.snapshot_id}:{regime_version}",
                dataset_type="market_regimes",
                trade_date=snapshot.trade_date,
                market=snapshot.market,
                source="market-regime",
                storage_ref={
                    "snapshot_id": snapshot.snapshot_id,
                    "regime_version": regime_version,
                    "feature_version": feature.feature_version,
                    "artifact_type": "market-regime-json",
                },
                snapshot_id=snapshot.snapshot_id,
                profile_id=getattr(snapshot, "profile_id", None),
                quality_status=evaluation.quality_status,
            )

            saved = regime
            db_warning = False
            try:
                with canonical_write_scope("market_state", self.service_name):
                    saved = await self._regime_repository.upsert_regime(session, regime)
                if not canonical_writer_enabled():
                    await self._dataset_repository.upsert_dataset(session, dataset_record)
                await session.commit()
            except Exception as exc:  # noqa: BLE001
                db_warning = True
                evaluation.warnings.append(f"database persistence failed: {exc}")

        artifact_path = self._artifact_path(trade_date=snapshot.trade_date, snapshot_id=snapshot.snapshot_id, regime_version=regime_version)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_payload = {
            "regime": saved.to_dict(),
            "evaluation": evaluation.to_dict(),
            "snapshot_id": snapshot.snapshot_id,
            "trade_date": snapshot.trade_date.isoformat(),
            "market": snapshot.market,
            "regime_version": regime_version,
            "feature_version": feature.feature_version,
            "warnings": evaluation.warnings,
        }
        artifact_path.write_text(json.dumps(_to_plain(artifact_payload), ensure_ascii=False, indent=2), encoding="utf-8")

        status = "partial" if db_warning or evaluation.quality_status != "ok" else "ok"
        message = "market regime written" if not db_warning else "market regime written with database warning"
        payload = {
            "regime": saved.to_dict(),
            "evaluation": evaluation.to_dict(),
            "artifact_ref": self._artifact_ref(artifact_path),
            "artifact_path": self._artifact_ref(artifact_path)["relative_path"],
            "dataset_id": dataset_record.dataset_id,
            "warnings": evaluation.warnings,
        }
        return ServiceResult(status=status, message=message, payload=payload, warnings=evaluation.warnings)

    async def list_regimes(
        self,
        *,
        trade_date: date | str | None = None,
        snapshot_id: str | None = None,
        market: str | None = None,
        regime_version: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ServiceResult:
        """按条件查询 market regime 列表。"""
        if limit < 1 or offset < 0:
            return self._error(
                status="error",
                error_type="invalid_query",
                message="invalid pagination",
                detail="limit must be >= 1 and offset must be >= 0",
                metadata={"limit": limit, "offset": offset},
            )

        normalized_trade_date = None
        if trade_date in {None, ""}:
            normalized_trade_date = None
        elif isinstance(trade_date, date):
            normalized_trade_date = trade_date
        else:
            normalized_trade_date = date.fromisoformat(str(trade_date))

        async with self._session_factory() as session:
            total = await self._regime_repository.count_regimes(
                session,
                trade_date=normalized_trade_date,
                snapshot_id=snapshot_id,
                market=market,
                regime_version=regime_version,
            )
            regimes = await self._regime_repository.list_regimes(
                session,
                trade_date=normalized_trade_date,
                snapshot_id=snapshot_id,
                market=market,
                regime_version=regime_version,
                limit=limit,
                offset=offset,
            )

        if not regimes:
            return self._error(
                status="error",
                error_type="empty_data",
                message="market regime not found",
                detail="no regime matches query",
                metadata={
                    "trade_date": normalized_trade_date.isoformat() if normalized_trade_date else None,
                    "snapshot_id": snapshot_id,
                    "market": market,
                    "regime_version": regime_version,
                },
            )

        payload = {
            "filters": {
                "trade_date": normalized_trade_date.isoformat() if normalized_trade_date else None,
                "snapshot_id": snapshot_id,
                "market": market,
                "regime_version": regime_version,
            },
            "page": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "count": len(regimes),
            },
            "items": [regime.to_dict() for regime in regimes],
        }
        return ServiceResult(status="ok", message="market regimes found", payload=payload)

    async def get_regime_detail(self, snapshot_id: str, regime_version: str | None = None) -> ServiceResult:
        """按 snapshot_id / regime_version 查询 regime 详情。"""
        version = regime_version or DEFAULT_REGIME_VERSION
        async with self._session_factory() as session:
            snapshot = await self._snapshot_repository.get_by_snapshot_id(session, snapshot_id)
            if snapshot is None:
                return self._error(
                    status="error",
                    error_type="snapshot_not_found",
                    message="snapshot not found",
                    detail=snapshot_id,
                    metadata={"snapshot_id": snapshot_id},
                )

            regime = await self._regime_repository.get_by_snapshot_and_version(session, snapshot_id, version)

        if regime is None:
            return self._error(
                status="error",
                error_type="regime_not_found",
                message="market regime not found",
                detail=snapshot_id,
                metadata={"snapshot_id": snapshot_id, "regime_version": version},
            )

        payload = {
            "regime": regime.to_dict(),
            "features": regime.features_json,
            "warnings": [regime.missing_reason] if regime.missing_reason else [],
        }
        return ServiceResult(status=regime.quality_status, message="market regime found", payload=payload, warnings=payload["warnings"])
