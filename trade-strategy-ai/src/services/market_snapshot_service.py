from __future__ import annotations

import asyncio
import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable

from src.common.config import load_app_config
from src.models.market_snapshot import MarketSnapshot, MarketSnapshotBuildContext, MarketSnapshotSection
from src.providers.kaipan_provider import KaipanAuth, KaipanProvider
from src.market_universe.snapshot_service import SnapshotService as UniverseSnapshotService
from src.services.base import BaseService, ServiceResult
from src.services.config_service import ConfigService
from src.services.market_data_storage_service import MarketDataStorageService
from src.services.market_service import MarketService
from src.services.market_snapshot_builders import build_default_market_snapshot_registry
from src.services.market_snapshot_registry import MarketSnapshotRegistry
from src.services.persona_service import PersonaService


def _project_base_dir(config_path: Path) -> Path:
    """根据配置文件路径推导项目根目录。"""
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _relative_path_or_name(path: str | Path, base_dir: Path) -> str:
    """把绝对路径收敛为相对路径；无法相对时仅保留文件名。"""
    resolved = Path(path).expanduser().resolve()
    try:
        return str(resolved.relative_to(base_dir))
    except ValueError:
        try:
            return str(Path(path).expanduser())
        except Exception:  # noqa: BLE001
            return resolved.name


def _stable_json(data: Any) -> str:
    """生成稳定的 JSON 串。"""
    return json.dumps(_to_plain(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write_json_atomic(path: Path, payload: Any) -> Path:
    """原子写入 JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(_to_plain(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)
    return path


class MarketSnapshotService(BaseService):
    """结构化 Market Snapshot 编排服务。"""

    service_name = "market-snapshot"

    def __init__(
        self,
        *,
        provider_factory: Callable[..., KaipanProvider] | None = None,
        market_service: MarketService | None = None,
        persona_service: PersonaService | None = None,
        config_service: ConfigService | None = None,
        storage_service: MarketDataStorageService | None = None,
        snapshot_root: str | Path | None = None,
    ) -> None:
        self._provider_factory = provider_factory
        self._market_service = market_service
        self._persona_service = persona_service
        self._config_service = config_service or ConfigService()
        self._storage_service = storage_service
        self._snapshot_root = Path(snapshot_root).expanduser().resolve() if snapshot_root is not None else None

    def _load_runtime(self, config_path: str | Path) -> tuple[Any, Path]:
        """加载配置并推导项目根目录。"""
        loaded = load_app_config(config_path)
        base_dir = _project_base_dir(Path(loaded.config_path))
        return loaded, base_dir

    def _create_provider(self, *, loaded: Any, base_dir: Path) -> KaipanProvider:
        """创建 KaipanProvider。"""
        factory = self._provider_factory or KaipanProvider
        data_root = base_dir / loaded.config.kaipan.data_dir
        return factory(
            auth=KaipanAuth(),
            raw_dir=data_root / "raw",
            normalized_dir=data_root / "snapshots",
            snapshots_dir=data_root / "snapshots",
            kaipan_config=loaded.config.kaipan,
        )

    def _snapshot_root_dir(self, base_dir: Path) -> Path:
        """返回结构化 Market Snapshot 的根目录。"""
        return self._snapshot_root or (base_dir / "data/processed/market_snapshot")

    def _snapshot_dir(self, *, base_dir: Path, trade_date: str, slot: str) -> Path:
        """返回单个快照目录。"""
        return self._snapshot_root_dir(base_dir) / trade_date / slot

    def _snapshot_paths(self, *, base_dir: Path, trade_date: str, slot: str) -> dict[str, Path]:
        """返回单个快照的文件路径集合。"""
        directory = self._snapshot_dir(base_dir=base_dir, trade_date=trade_date, slot=slot)
        return {
            "snapshot": directory / "snapshot.json",
            "summary": directory / "snapshot.summary.json",
            "quality": directory / "snapshot.quality.json",
        }

    def _candidate_pool_root(self, *, base_dir: Path, loaded: Any) -> Path:
        """返回候选池快照根目录。"""
        data_cfg = getattr(loaded.config, "data", None)
        snapshot_dir = getattr(data_cfg, "market_universe_snapshot_dir", "data/market_universe/snapshots")
        snapshot_root = Path(snapshot_dir).expanduser()
        if snapshot_root.is_absolute():
            return snapshot_root.resolve()
        return (base_dir / snapshot_root).resolve()

    def _load_candidate_pool(self, *, base_dir: Path, loaded: Any, trade_date: str, slot: str) -> Any | None:
        """加载同日期/时段的候选池快照。"""
        candidate_pool_service = UniverseSnapshotService(base_dir=self._candidate_pool_root(base_dir=base_dir, loaded=loaded))
        return candidate_pool_service.load(trade_date, slot)

    def _snapshot_id(self, *, trade_date: str, slot: str, market: str, data_version: str, sections: dict[str, MarketSnapshotSection]) -> str:
        """生成稳定的 snapshot_id。"""
        seed = _stable_json(
            {
                "trade_date": trade_date,
                "slot": slot,
                "market": market,
                "data_version": data_version,
                "sections": {section_id: {"quality_status": section.quality_status, "record_count": section.record_count} for section_id, section in sections.items()},
            }
        )
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        return f"market-snapshot-{trade_date}-{slot}-{digest}"

    def _build_section_results(self, sections: dict[str, MarketSnapshotSection]) -> list[dict[str, Any]]:
        """把 section 结果整理成 summary 用结构。"""
        results: list[dict[str, Any]] = []
        for section_id, section in sections.items():
            results.append(
                {
                    "section_id": section_id,
                    "provider": section.provider,
                    "quality_status": section.quality_status,
                    "record_count": section.record_count,
                    "missing_reason": section.missing_reason,
                }
            )
        return results

    def _build_summary_payload(
        self,
        *,
        snapshot: MarketSnapshot,
        section_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """生成快照摘要。"""
        section_count = len(section_results)
        available = [item for item in section_results if item["quality_status"] == "ok"]
        partial = [item for item in section_results if item["quality_status"] == "partial"]
        missing = [item for item in section_results if item["quality_status"] == "missing"]
        return {
            "snapshot_id": snapshot.snapshot_id,
            "trade_date": snapshot.trade_date,
            "market": snapshot.market,
            "data_version": snapshot.data_version,
            "created_at": snapshot.created_at,
            "section_count": section_count,
            "available_section_count": len(available),
            "partial_section_count": len(partial),
            "missing_section_count": len(missing),
            "coverage_rate": round(len(available) / section_count, 4) if section_count else 0.0,
            "section_ids": list(snapshot.sections.keys()),
            "missing_sections": [item["section_id"] for item in missing],
            "provider_sources": snapshot.provider_sources,
            "sections": section_results,
            "metadata": snapshot.metadata,
        }

    def _build_quality_report_payload(
        self,
        *,
        snapshot: MarketSnapshot,
        section_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """生成数据质量报告。"""
        overall_status = "ok"
        if any(item["quality_status"] == "partial" for item in section_results):
            overall_status = "partial"
        if any(item["quality_status"] == "missing" for item in section_results):
            overall_status = "partial"
        if section_results and all(item["quality_status"] == "missing" for item in section_results):
            overall_status = "missing"
        return {
            "snapshot_id": snapshot.snapshot_id,
            "trade_date": snapshot.trade_date,
            "market": snapshot.market,
            "data_version": snapshot.data_version,
            "overall_status": overall_status,
            "provider_sources": snapshot.provider_sources,
            "sections": section_results,
            "summary": {
                "section_count": len(section_results),
                "ok_count": sum(1 for item in section_results if item["quality_status"] == "ok"),
                "partial_count": sum(1 for item in section_results if item["quality_status"] == "partial"),
                "missing_count": sum(1 for item in section_results if item["quality_status"] == "missing"),
            },
        }

    def _build_registry(self, *, provider: KaipanProvider, base_dir: Path, benchmark_symbol: str, config_path: str | Path) -> MarketSnapshotRegistry:
        """构建默认 section registry。"""
        market_service = self._market_service or MarketService()
        persona_service = self._persona_service or PersonaService()
        return build_default_market_snapshot_registry(
            provider=provider,
            market_service=market_service,
            persona_service=persona_service,
            base_dir=base_dir,
            benchmark_symbol=benchmark_symbol,
            config_path=config_path,
        )

    def _build_snapshot_sync(
        self,
        *,
        config_path: str | Path,
        benchmark_symbol: str,
        trade_date: str,
        slot: str = "17-30",
        profile_id: str | None = "default",
        market: str = "CN",
        offline: bool = False,
        force: bool = False,
        snapshot_type: str = "all",
    ) -> ServiceResult:
        """同步构建结构化 Market Snapshot。"""
        del force  # 保留接口语义，但第一版不做跳过缓存分支。
        del snapshot_type

        loaded, base_dir = self._load_runtime(config_path)
        provider = self._create_provider(loaded=loaded, base_dir=base_dir)
        if not benchmark_symbol:
            raise ValueError("benchmark_symbol is required")
        candidate_pool = self._load_candidate_pool(
            base_dir=base_dir,
            loaded=loaded,
            trade_date=trade_date,
            slot=slot,
        )
        registry = self._build_registry(
            provider=provider,
            base_dir=base_dir,
            benchmark_symbol=benchmark_symbol,
            config_path=loaded.config_path,
        )
        trade_date_value = date.fromisoformat(trade_date)
        context = MarketSnapshotBuildContext(
            config_path=str(loaded.config_path),
            profile_id=profile_id,
            trade_date=trade_date_value.isoformat(),
            slot=slot,
            market=market,
            offline=offline,
            metadata={"config_ref": _relative_path_or_name(loaded.config_path, base_dir), "benchmark_symbol": benchmark_symbol},
        )

        sections: dict[str, MarketSnapshotSection] = {}
        section_results: list[dict[str, Any]] = []
        warnings: list[str] = []
        for builder in registry.items():
            section = builder.build(context)
            sections[builder.section_id] = section
            section_results.append(
                {
                    "section_id": builder.section_id,
                    "provider": section.provider,
                    "quality_status": section.quality_status,
                    "record_count": section.record_count,
                    "missing_reason": section.missing_reason,
                }
            )
            if section.quality_status != "ok" and section.missing_reason:
                warnings.append(f"{builder.section_id}: {section.missing_reason}")

        snapshot_id = self._snapshot_id(
            trade_date=context.trade_date,
            slot=context.slot,
            market=context.market,
            data_version="market-snapshot-v1",
            sections=sections,
        )
        provider_sources = []
        for section in sections.values():
            if section.provider and section.provider not in provider_sources:
                provider_sources.append(section.provider)

        snapshot = MarketSnapshot(
            snapshot_id=snapshot_id,
            trade_date=context.trade_date,
            market=context.market,
            data_version="market-snapshot-v1",
            provider_sources=provider_sources,
            created_at=datetime.now(UTC),
            data_quality={
                "overall_status": "ok" if not warnings else "partial",
                "section_count": len(section_results),
                "ok_count": sum(1 for item in section_results if item["quality_status"] == "ok"),
                "partial_count": sum(1 for item in section_results if item["quality_status"] == "partial"),
                "missing_count": sum(1 for item in section_results if item["quality_status"] == "missing"),
            },
            sections=sections,
            metadata={
                "config_ref": _relative_path_or_name(loaded.config_path, base_dir),
                "slot": slot,
                "profile_id": profile_id,
                "offline": offline,
                "section_order": list(sections.keys()),
                "benchmark_symbol": benchmark_symbol,
                "candidate_pool_slot": slot,
                "candidate_pool_path": str(
                    self._candidate_pool_root(base_dir=base_dir, loaded=loaded) / trade_date / f"{slot}.json"
                ),
                # 兼容字段：仅供内部加载器 / 回测复用，不作为新的对外快照入口。
                "candidate_pool": candidate_pool,
            },
        )

        output_paths = self._snapshot_paths(base_dir=base_dir, trade_date=context.trade_date, slot=context.slot)
        summary_payload = self._build_summary_payload(snapshot=snapshot, section_results=section_results)
        quality_payload = self._build_quality_report_payload(snapshot=snapshot, section_results=section_results)

        _write_json_atomic(output_paths["snapshot"], snapshot.to_dict())
        _write_json_atomic(output_paths["summary"], summary_payload)
        _write_json_atomic(output_paths["quality"], quality_payload)

        status = "ok"
        if warnings:
            status = "partial"

        storage_result: ServiceResult | None = None
        if self._storage_service is not None:
            try:
                storage_result = asyncio.run(
                    self._storage_service.save_snapshot(
                        snapshot,
                        summary_payload=summary_payload,
                        quality_payload=quality_payload,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"db storage failed: {exc}")
                storage_result = ServiceResult(status="error", message="db storage failed", payload={"error": str(exc)})
                status = "partial" if status == "ok" else status

        return ServiceResult(
            status=status,
            message="market snapshot built" if status == "ok" else "market snapshot built with partial coverage",
            payload={
                "config_path": _relative_path_or_name(loaded.config_path, base_dir),
                "snapshot_id": snapshot_id,
                "trade_date": context.trade_date,
                "slot": context.slot,
                "market": context.market,
                "profile_id": profile_id,
                "snapshot_path": str(output_paths["snapshot"]),
                "snapshot_summary_path": str(output_paths["summary"]),
                "quality_report_path": str(output_paths["quality"]),
                "snapshot": snapshot.to_dict(),
                "snapshot_summary": summary_payload,
                "quality_report": quality_payload,
                "sections": section_results,
                "provider_sources": provider_sources,
                "db_storage": storage_result.payload if storage_result is not None else None,
            },
            warnings=warnings,
        )

    async def build_market_snapshot(
        self,
        *,
        config_path: str | Path,
        benchmark_symbol: str,
        trade_date: str,
        slot: str = "17-30",
        profile_id: str | None = "default",
        market: str = "CN",
        offline: bool = False,
        force: bool = False,
        snapshot_type: str = "all",
    ) -> ServiceResult:
        """异步构建结构化 Market Snapshot。"""
        return await asyncio.to_thread(
            self._build_snapshot_sync,
            config_path=config_path,
            benchmark_symbol=benchmark_symbol,
            trade_date=trade_date,
            slot=slot,
            profile_id=profile_id,
            market=market,
            offline=offline,
            force=force,
            snapshot_type=snapshot_type,
        )

    def load_market_snapshot(self, *, config_path: str | Path, trade_date: str, slot: str = "17-30") -> MarketSnapshot | None:
        """加载已生成的结构化 Market Snapshot。"""
        _loaded, base_dir = self._load_runtime(config_path)
        paths = self._snapshot_paths(base_dir=base_dir, trade_date=trade_date, slot=slot)
        if not paths["snapshot"].exists():
            return None
        try:
            payload = json.loads(paths["snapshot"].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        sections = {}
        from src.models.market_snapshot import MarketSnapshotSection

        raw_sections = payload.get("sections", {})
        if isinstance(raw_sections, dict):
            for section_id, section_payload in raw_sections.items():
                if not isinstance(section_payload, dict):
                    continue
                sections[section_id] = MarketSnapshotSection(
                    section_id=section_payload.get("section_id", section_id),
                    provider=section_payload.get("provider"),
                    source_time=datetime.fromisoformat(section_payload["source_time"]) if section_payload.get("source_time") else None,
                    record_count=int(section_payload.get("record_count", 0)),
                    missing_reason=section_payload.get("missing_reason"),
                    quality_status=section_payload.get("quality_status", "missing"),
                    payload=section_payload.get("payload", {}) if isinstance(section_payload.get("payload"), dict) else {},
                    metadata=section_payload.get("metadata", {}) if isinstance(section_payload.get("metadata"), dict) else {},
                )
        return MarketSnapshot(
            snapshot_id=payload.get("snapshot_id", ""),
            trade_date=payload.get("trade_date", trade_date),
            market=payload.get("market", "CN"),
            data_version=payload.get("data_version", "market-snapshot-v1"),
            provider_sources=payload.get("provider_sources", []),
            created_at=datetime.fromisoformat(payload["created_at"]) if payload.get("created_at") else datetime.now(UTC),
            data_quality=payload.get("data_quality", {}),
            sections=sections,
            metadata=payload.get("metadata", {}),
        )
