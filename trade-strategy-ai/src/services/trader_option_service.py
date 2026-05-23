from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select

from src.db.session import session_scope
from src.models.trader_strategy_version import TraderStrategyVersion
from src.services.base import BaseService, ServiceResult


def _get_backtest_result_dirs() -> list[Path]:
    """获取回测结果目录。"""
    from src.common.paths import resolve_project_path

    return [
        resolve_project_path("data/backtest/results"),
        resolve_project_path("data/processed/backtest"),
        resolve_project_path("data/jobs"),
    ]


def _extract_backtest_trader_id(data: dict[str, Any]) -> str | None:
    """从回测结果 payload 中提取 trader_id。"""
    trader_id = data.get("trader_id") or data.get("request_trader_id")
    if isinstance(trader_id, str) and trader_id.strip():
        return trader_id.strip()
    return None


def _iter_backtest_result_files() -> list[Path]:
    """列出所有可用的回测结果文件。"""
    files: list[Path] = []
    for results_dir in _get_backtest_result_dirs():
        if not results_dir.exists():
            continue
        if results_dir.name == "jobs":
            for job_dir in results_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                result_file = job_dir / "result.json"
                report_file = job_dir / "backtest_report.md"
                csv_file = job_dir / "backtest_records.csv"
                if result_file.exists() and (report_file.exists() or csv_file.exists()):
                    files.append(result_file)
            continue
        files.extend(sorted(results_dir.glob("*.json")))
    return files


class TraderOptionService(BaseService):
    """Trader 选项汇总服务。"""

    service_name = "trader-options"

    def __init__(self, *, session_scope_factory: Callable[[], Any] = session_scope) -> None:
        self._session_scope_factory = session_scope_factory

    async def list_trader_options(self, *, source: str = "all") -> ServiceResult:
        """列出 trader_id 选项。"""
        if source not in {"all", "strategy", "backtest"}:
            return ServiceResult(status="error", message="invalid trader options source", payload={"source": source})

        trader_ids: set[str] = set()
        if source in {"all", "strategy"}:
            async with self._session_scope_factory() as session:
                result = await session.execute(select(TraderStrategyVersion.trader_id).distinct())
                for trader_id in result.scalars().all():
                    if isinstance(trader_id, str) and trader_id.strip():
                        trader_ids.add(trader_id.strip())

        if source in {"all", "backtest"}:
            for result_file in _iter_backtest_result_files():
                try:
                    data = json.loads(result_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                trader_id = _extract_backtest_trader_id(data)
                if trader_id:
                    trader_ids.add(trader_id)

        items = sorted(trader_ids)
        return ServiceResult(
            status="ok",
            message="trader options listed",
            payload={
                "count": len(items),
                "items": items,
                "source": source,
            },
        )


def make_trader_option_service(session_scope_factory: Callable[[], Any] | None = None) -> TraderOptionService:
    """构造 TraderOptionService。"""
    return TraderOptionService(session_scope_factory=session_scope_factory or session_scope)
