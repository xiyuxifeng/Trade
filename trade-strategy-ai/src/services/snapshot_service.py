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
from src.services.base import BaseService, ServiceResult


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

    async def build_snapshot(
        self,
        *,
        config_path: str | Path,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        slot: str = "17-30",
        snapshot_type: str = "all",
        force: bool = False,
        offline: bool = False,
    ) -> ServiceResult:
        """构建候选池快照。"""
        loaded = load_app_config(config_path)
        config_file = Path(config_path).expanduser().resolve()
        base_dir = _project_base_dir(loaded.config_path)

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
        success_count = 0
        failure_count = 0

        for trade_date in trade_dates:
            for stype in types_to_build:
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
                    success_count += 1
                    results.append({"trade_date": trade_date, "type": stype, "status": "ok"})
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
