from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import select

from src.db.session import session_scope
from src.models.trader_strategy_version import TraderStrategyVersion
from src.services.base import BaseService, ServiceResult
from src.services.job_service import JobService


def _extract_backtest_trader_id(data: dict[str, Any]) -> str | None:
    """从回测结果 payload 中提取 trader_id。"""
    result = data.get("result")
    if isinstance(result, dict):
        payload = result.get("payload")
        if isinstance(payload, dict):
            request = payload.get("request")
            if isinstance(request, dict):
                trader_id = request.get("trader_id")
                if isinstance(trader_id, str) and trader_id.strip():
                    return trader_id.strip()

    payload = data.get("payload")
    if isinstance(payload, dict):
        request = payload.get("request")
        if isinstance(request, dict):
            trader_id = request.get("trader_id")
            if isinstance(trader_id, str) and trader_id.strip():
                return trader_id.strip()

    trader_id = data.get("trader_id") or data.get("request_trader_id")
    if isinstance(trader_id, str) and trader_id.strip():
        return trader_id.strip()
    return None


async def _load_backtest_trader_ids() -> list[str]:
    """从 jobs 表提取回测 trader_id。"""
    job_service = JobService()
    trader_ids: set[str] = set()
    for job_type in ("backtest-run", "rule-pool-backtest"):
        skip = 0
        page_size = 500
        total: int | None = None
        while True:
            result = await job_service.list_jobs(status="success", job_type=job_type, skip=skip, limit=page_size)
            if result.status != "ok":
                break
            items = result.payload.get("items", [])
            if total is None:
                total = int(result.payload.get("total") or len(items) or 0)
            for item in items:
                if not isinstance(item, dict):
                    continue
                trader_id = _extract_backtest_trader_id(item)
                if trader_id:
                    trader_ids.add(trader_id)
            skip += len(items)
            if not items or (total is not None and skip >= total):
                break
    return sorted(trader_ids)


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
            for trader_id in await _load_backtest_trader_ids():
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
