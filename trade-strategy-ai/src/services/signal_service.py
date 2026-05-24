from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from src.db.session import session_scope
from src.db.repositories import SignalRepository
from src.services.base import BaseService, ServiceResult


class SignalService(BaseService):
	"""信号版本查询服务。"""

	service_name = "signal"

	def __init__(
		self,
		*,
		session_factory: Callable[[], Any] | None = None,
		signal_repository: SignalRepository | None = None,
	) -> None:
		self._session_factory = session_factory or session_scope
		self._signal_repository = signal_repository or SignalRepository()

	def _signal_context(self, signal: Any) -> dict[str, Any]:
		"""从 DB 信号记录构造 UI 需要的上下文摘要。"""
		metadata = signal.signal_metadata or {}
		if isinstance(metadata, dict):
			context = metadata.get("context")
			if isinstance(context, dict):
				return context
			if isinstance(context, list):
				return {"summary": context[:3]}

			context_summary: dict[str, Any] = {}
			for key in ("trend", "signal", "bias", "score", "summary"):
				if metadata.get(key) not in (None, ""):
					context_summary[key] = metadata[key]
			if context_summary:
				return context_summary

		return {
			"signal": signal.side,
			"score": signal.confidence,
			"summary": metadata.get("rationale") or metadata.get("summary") or metadata.get("rejection_reason") or metadata.get("degradation_reason"),
		}

	def _signal_payload(self, signal: Any) -> dict[str, Any]:
		"""把 DB 信号记录转成 UI payload。"""
		metadata = signal.signal_metadata or {}
		return {
			"signal_id": signal.signal_id,
			"symbol": signal.symbol,
			"side": signal.side,
			"confidence": signal.confidence,
			"timestamp": signal.created_at.isoformat() if signal.created_at else None,
			"trader_id": signal.trader_id or metadata.get("trader_id"),
			"strategy_version_id": signal.strategy_version_id,
			"context": self._signal_context(signal),
		}

	def _list_db_signals(
		self,
		*,
		symbol: str | None,
		since_dt: datetime | None,
		limit: int,
	) -> list[Any]:
		"""同步入口中执行 DB 查询。"""
		if self._session_factory is None:
			return []
		if hasattr(self._signal_repository, "list_signals_sync"):
			return self._signal_repository.list_signals_sync(
				self._session_factory,
				symbol=symbol,
				since=since_dt,
				limit=limit,
			)

		async def _run() -> list[Any]:
			async with self._session_factory() as session:
				return await self._signal_repository.list_signals(
					session,
					symbol=symbol,
					since=since_dt,
					limit=limit,
				)

		return asyncio.run(_run())

	def list_signals(
		self,
		*,
		config_path: str | Path,
		symbol: str | None = None,
		since: str | date | datetime | None = None,
		limit: int = 100,
	) -> ServiceResult:
		"""列出已存储的信号版本。"""
		del config_path
		since_dt: datetime | None
		if since is None:
			since_dt = None
		elif isinstance(since, datetime):
			since_dt = since
		elif isinstance(since, date):
			since_dt = datetime.combine(since, datetime.min.time())
		else:
			since_dt = datetime.fromisoformat(since)

		rows = self._list_db_signals(symbol=symbol, since_dt=since_dt, limit=limit)
		signals = [self._signal_payload(row) for row in rows]
		return ServiceResult(
			status="ok",
			message="signals listed" if signals else "no signals found",
			payload={
				"source": "database",
				"count": len(signals),
				"signals": signals,
			},
		)
