from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.data_agent.skills import fetch_market
from src.common.config import AppConfig
from src.schemas.contracts import DataRequest, DataResponse, DataResponseStatus


class DataAgent(BaseAgent):
	def __init__(self, *, config: AppConfig) -> None:
		super().__init__("data")
		self.config = config
		self.register_skill("fetch_market", fetch_market.to_payload)

	async def handle(self, request: DataRequest) -> DataResponse:
		supported = set(fetch_market.supported_fields())
		requested = set(request.fields)
		missing = sorted(requested - supported)

		if missing:
			return DataResponse(
				request_id=request.request_id,
				status=DataResponseStatus.capability_missing,
				missing_capabilities=missing,
				errors=["DataAgent does not support requested fields in Phase 0"],
			)

		payload = await self.call_skill(
			"fetch_market",
			symbols=request.symbols,
			fields=request.fields,
			mock_prices=self.config.data.mock_prices,
		)

		return DataResponse(
			request_id=request.request_id,
			status=DataResponseStatus.ok,
			payload=payload,
		)
