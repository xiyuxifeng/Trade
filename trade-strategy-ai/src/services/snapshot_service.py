from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Callable

from src.common.config import load_app_config
from src.market_universe.snapshot_service import SnapshotService as UniverseSnapshotService
from src.pipeline.tasks.snapshot_tasks import (
    handle_hot_topics_snapshot,
    handle_strong_symbols_snapshot,
    handle_topic_constituents_snapshot,
)
from src.services.config_profile_service import ConfigProfileService
from src.services.base import BaseService, ServiceResult
from src.services.market_data_storage_service import MarketDataStorageService
from src.services.market_snapshot_service import MarketSnapshotService


def _project_base_dir(config_path: Path) -> Path:
    """根据配置文件推导项目根目录。"""
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


def _expand_date_range(start_date: str, end_date: str) -> list[str]:
    """将起止日期展开为 ISO 日期列表。"""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        raise ValueError(f"start_date > end_date: {start_date} > {end_date}")
    values: list[str] = []
    current = start
    while current <= end:
        values.append(current.isoformat())
        current = current.fromordinal(current.toordinal() + 1)
    return values


class SnapshotService(BaseService):
    """快照构建与文件管理的共享服务。"""

    service_name = "snapshot"

    def __init__(
        self,
        *,
        backend: UniverseSnapshotService | None = None,
        hot_topics_handler: Callable[..., Any] = handle_hot_topics_snapshot,
        topic_constituents_handler: Callable[..., Any] = handle_topic_constituents_snapshot,
        strong_symbols_handler: Callable[..., Any] = handle_strong_symbols_snapshot,
    ) -> None:
        self._backend = backend or UniverseSnapshotService()
        self._hot_topics_handler = hot_topics_handler
        self._topic_constituents_handler = topic_constituents_handler
        self._strong_symbols_handler = strong_symbols_handler

    def _snapshot_path(self, trade_date: str, slot: str) -> Path:
        """返回 MarketUniverse 快照路径。"""
        return self._backend.base_dir / trade_date / f"{slot}.json"

    @staticmethod
    def _require_benchmark_symbol(benchmark_symbol: str | None) -> str:
        """校验 benchmark_symbol 必填，避免静默兜底导致语义不一致。"""
        if isinstance(benchmark_symbol, str):
            benchmark_symbol = benchmark_symbol.strip() or None
        if not benchmark_symbol:
            raise ValueError("benchmark_symbol is required")
        return benchmark_symbol

    async def build_snapshot(
        self,
        *,
        config_path: str | Path,
        profile_id: str | None = None,
        benchmark_symbol: str | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        slot: str = "17-30",
        snapshot_type: str = "all",
        force: bool = False,
        offline: bool = False,
        runtime_state: dict[str, Any] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> ServiceResult:
        """构建候选池快照。"""
        resolved_benchmark_symbol = self._require_benchmark_symbol(benchmark_symbol)
        if profile_id is not None and str(profile_id).strip():
            runtime = await ConfigProfileService().load_profile_runtime_config(str(profile_id).strip())
            loaded_config = runtime.config
            base_dir = runtime.base_dir
            config_file = None
            resolved_profile_id = runtime.profile_id
        else:
            loaded = load_app_config(config_path)
            loaded_config = loaded.config
            config_file = Path(config_path).expanduser().resolve()
            base_dir = _project_base_dir(loaded.config_path)
            resolved_profile_id = profile_id

        if start_date is not None or end_date is not None:
            if not start_date or not end_date:
                raise ValueError("start_date and end_date must be provided together")
            trade_dates = _expand_date_range(start_date, end_date)
        elif date is not None:
            trade_dates = [date]
        else:
            raise ValueError("date or date range is required")

        if snapshot_type == "all":
            types_to_build = ["hot_topics", "topic_constituents", "strong_symbols"]
        elif snapshot_type in {"hot_topics", "topic_constituents", "strong_symbols"}:
            types_to_build = [snapshot_type]
        else:
            raise ValueError("invalid snapshot_type")

        results: list[dict[str, Any]] = []
        snapshot_paths: list[str] = []
        success_count = 0
        failure_count = 0
        total_steps = len(trade_dates) * len(types_to_build)
        current_step = 0
        runtime_state_payload = runtime_state if isinstance(runtime_state, dict) else {}
        checkpoint = runtime_state_payload.get("checkpoint") if isinstance(runtime_state_payload.get("checkpoint"), dict) else {}
        start_step = int(checkpoint.get("step_index") or 0)
        current_step = int(checkpoint.get("step_index") or 0)
        if isinstance(checkpoint.get("results"), list):
            results = list(checkpoint.get("results") or [])
        if isinstance(checkpoint.get("snapshot_paths"), list):
            snapshot_paths = list(checkpoint.get("snapshot_paths") or [])

        for trade_date in trade_dates:
            for stype in types_to_build:
                current_step += 1
                if current_step <= start_step:
                    continue
                details = {
                    "trade_date": trade_date,
                    "slot": slot,
                    "force": force,
                    "offline": offline,
                }
                try:
                    if stype == "hot_topics":
                        await self._hot_topics_handler(details, config=loaded_config)
                    elif stype == "topic_constituents":
                        await self._topic_constituents_handler(details, config=loaded_config)
                    else:
                        await self._strong_symbols_handler(details, config=loaded_config)
                    snapshot_path = str(self._snapshot_path(trade_date, slot))
                    if snapshot_path not in snapshot_paths:
                        snapshot_paths.append(snapshot_path)
                    success_count += 1
                    results.append({"trade_date": trade_date, "type": stype, "status": "ok"})
                    if progress_callback is not None:
                        progress_callback(
                            {
                                "job_type": "snapshot-build",
                                "stage": "snapshot",
                                "current": current_step,
                                "total": total_steps,
                                "percent": round((current_step / total_steps) * 100, 2) if total_steps else 0.0,
                                "remaining": max(total_steps - current_step, 0),
                                "current_step": f"snapshot:{stype}",
                                "current_trade_date": trade_date,
                                "current_dataset": stype,
                                "status": "success",
                                "updated_at": None,
                                "runtime_state": {
                                    "schema_version": 1,
                                    "checkpoint": {
                                        "step_index": current_step,
                                        "results": results,
                                        "snapshot_paths": snapshot_paths,
                                    },
                                },
                            }
                        )
                except Exception as exc:  # noqa: BLE001
                    failure_count += 1
                    results.append(
                        {
                            "trade_date": trade_date,
                            "type": stype,
                            "status": "error",
                            "error": str(exc),
                        }
                    )
                    if progress_callback is not None:
                        progress_callback(
                            {
                                "job_type": "snapshot-build",
                                "stage": "snapshot",
                                "current": current_step,
                                "total": total_steps,
                                "percent": round((current_step / total_steps) * 100, 2) if total_steps else 0.0,
                                "remaining": max(total_steps - current_step, 0),
                                "current_step": f"snapshot:{stype}",
                                "current_trade_date": trade_date,
                                "current_dataset": stype,
                                "status": "error",
                                "error": str(exc),
                                "updated_at": None,
                                "runtime_state": {
                                    "schema_version": 1,
                                    "checkpoint": {
                                        "step_index": current_step,
                                        "results": results,
                                        "snapshot_paths": snapshot_paths,
                                    },
                                },
                            }
                        )

        return ServiceResult(
            status="ok" if failure_count == 0 else "partial",
            message="snapshot build completed" if failure_count == 0 else "snapshot build partial",
            payload={
                "profile_id": resolved_profile_id,
                "config_path": str(config_file) if config_file is not None else None,
                "base_dir": str(base_dir),
                "slot": slot,
                "snapshot_type": snapshot_type,
                "success_count": success_count,
                "failure_count": failure_count,
                "snapshot_paths": snapshot_paths,
                "results": results,
            },
            warnings=[item["error"] for item in results if item.get("status") == "error"],
        )

    def load_snapshot(self, trade_date: str, slot: str):
        """加载单个快照。"""
        return self._backend.load(trade_date, slot)

    def list_snapshots(self, trade_date_start: str, trade_date_end: str):
        """列出日期区间内的快照。"""
        return self._backend.list_snapshots(trade_date_start, trade_date_end)

    def delete_snapshot(self, trade_date: str, slot: str) -> bool:
        """删除单个快照。"""
        return self._backend.delete(trade_date, slot)

    async def build_market_snapshot(
        self,
        *,
        config_path: str | Path,
        benchmark_symbol: str | None = None,
        trade_date: str,
        slot: str = "17-30",
        profile_id: str | None = "default",
        market: str = "CN",
        offline: bool = False,
        force: bool = False,
        snapshot_type: str = "all",
    ) -> ServiceResult:
        """构建结构化 Market Snapshot。"""
        resolved_benchmark_symbol = self._require_benchmark_symbol(benchmark_symbol)
        if profile_id is not None and str(profile_id).strip():
            runtime = await ConfigProfileService().load_profile_runtime_config(str(profile_id).strip())
            resolved_profile_id = runtime.profile_id
            config_file = None
        else:
            resolved_profile_id = profile_id
            config_file = Path(config_path).expanduser().resolve()
        service = MarketSnapshotService(storage_service=MarketDataStorageService())
        return await service.build_market_snapshot(
            config_path=config_file or Path("config/app.yaml"),
            benchmark_symbol=resolved_benchmark_symbol,
            trade_date=trade_date,
            slot=slot,
            profile_id=resolved_profile_id,
            market=market,
            offline=offline,
            force=force,
            snapshot_type=snapshot_type,
        )
