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

    async def _resolve_profile_benchmark_symbol(self, profile_id: str) -> str | None:
        """从 Profile 读取默认基准指数。"""
        profile = await ConfigProfileService().get_profile(profile_id)
        if profile is None:
            raise ValueError(f"profile not found: {profile_id}")

        sections = profile.sections if isinstance(profile.sections, dict) else {}
        benchmark_symbol = sections.get("market_state_benchmark_symbol")
        if isinstance(benchmark_symbol, str):
            benchmark_symbol = benchmark_symbol.strip() or None
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
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> ServiceResult:
        """构建候选池快照。"""
        loaded = load_app_config(config_path)
        config_file = Path(config_path).expanduser().resolve()
        base_dir = _project_base_dir(loaded.config_path)
        if benchmark_symbol:
            resolved_benchmark_symbol = benchmark_symbol
        elif profile_id:
            resolved_benchmark_symbol = await self._resolve_profile_benchmark_symbol(profile_id)
        else:
            resolved_benchmark_symbol = getattr(loaded.config, "market_state_benchmark_symbol", None)
        if not resolved_benchmark_symbol:
            raise ValueError("benchmark_symbol is required")

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

        for trade_date in trade_dates:
            for stype in types_to_build:
                current_step += 1
                details = {
                    "trade_date": trade_date,
                    "slot": slot,
                    "force": force,
                    "offline": offline,
                }
                try:
                    if stype == "hot_topics":
                        await self._hot_topics_handler(details, config=loaded.config)
                    elif stype == "topic_constituents":
                        await self._topic_constituents_handler(details, config=loaded.config)
                    else:
                        await self._strong_symbols_handler(details, config=loaded.config)
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
                            }
                        )

        return ServiceResult(
            status="ok" if failure_count == 0 else "partial",
            message="snapshot build completed" if failure_count == 0 else "snapshot build partial",
            payload={
                "config_path": str(config_file),
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
        loaded = load_app_config(config_path)
        if benchmark_symbol:
            resolved_benchmark_symbol = benchmark_symbol
        elif profile_id:
            resolved_benchmark_symbol = await self._resolve_profile_benchmark_symbol(profile_id)
        else:
            resolved_benchmark_symbol = getattr(loaded.config, "market_state_benchmark_symbol", None)
        if not resolved_benchmark_symbol:
            raise ValueError("benchmark_symbol is required")
        service = MarketSnapshotService(storage_service=MarketDataStorageService())
        return await service.build_market_snapshot(
            config_path=loaded.config_path,
            benchmark_symbol=resolved_benchmark_symbol,
            trade_date=trade_date,
            slot=slot,
            profile_id=profile_id,
            market=market,
            offline=offline,
            force=force,
            snapshot_type=snapshot_type,
        )
