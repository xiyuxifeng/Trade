from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.data_agent.skills import fetch_market
from src.agents.data_agent.skills import fetch_hot_topics
from src.agents.data_agent.skills import fetch_topic_constituents
from src.agents.data_agent.skills import fetch_strong_symbols
from src.agents.data_agent.skills import fetch_ohlcv
from src.common.config import AppConfig
from src.schemas.contracts import DataRequest, DataResponse, DataResponseStatus


class DataAgent(BaseAgent):
	"""数据能力路由层（capability router）。

	职责边界（NTL-S15-002）：
	- 长期保留为 capability router，按 DataRequest.dataset 路由到对应 skill
	- 不直接抓取数据，委托给各 skill handler
	- 不承担业务判断，仅做能力分发
	- 接收 DataRequest，返回 DataResponse

	支持的 dataset / fields（NTL-S2-018）：
	- dataset="last_price" / fields=["last_price"]：fetch_market
	- dataset="hot_topics" / fields=["hot_topics"]：fetch_hot_topics
	- dataset="topic_constituents" / fields=["topic_constituents"]：fetch_topic_constituents
	- dataset="strong_symbols" / fields=["strong_symbols"]：fetch_strong_symbols
	- dataset="ohlcv_1d" / fields=["ohlcv_1d"]：fetch_ohlcv
	- dataset="indicators" / fields=["indicators"]：fetch_indicators（NTL-S2-017 待实现）

	降级策略（NTL-S2-024）：
	- capability_missing：返回 DataResponse.status=capability_missing，missing_capabilities 列出缺失数据集
	  调用方（如 ManagerAgent）应为 capability_missing 创建 AgentTask(type="capability_missing")
	- error：skill 执行异常时返回 DataResponse.status=error，errors 包含异常详情
	- partial：保留给 builder 层部分成功场景（当前尚未实现，预期在 NTL-S2-012 后引入）
	- ok：所有请求的数据集均成功返回

	禁止：
	- 在 DataAgent 中硬编码具体抓取逻辑
	- 为单个 capability 单独写死处理路径
	"""

	_PROVIDER_KEY = "kaipan_provider"  # kaipan 相关 skill 共享的 provider key

	def __init__(self, *, config: AppConfig) -> None:
		super().__init__("data")
		self.config = config

		# 注册所有 skills
		self.register_skill("fetch_market", fetch_market.to_payload)
		self.register_skill("fetch_hot_topics", fetch_hot_topics.to_payload)
		self.register_skill("fetch_topic_constituents", fetch_topic_constituents.to_payload)
		self.register_skill("fetch_strong_symbols", fetch_strong_symbols.to_payload)
		self.register_skill("fetch_ohlcv", fetch_ohlcv.to_payload)

		# 共享 provider 实例（懒加载，首次使用时初始化）
		self._providers: dict[str, object] = {}

	def _get_provider(self, key: str) -> object | None:
		"""获取共享 provider 实例。"""
		if key not in self._providers:
			if key == self._PROVIDER_KEY:
				self._providers[key] = self._build_kaipan_provider()
		return self._providers.get(key)

	def _build_kaipan_provider(self):
		"""构建 KaipanProvider 实例（懒加载）。"""
		kaipan_cfg = getattr(self.config, "kaipan", None)
		if kaipan_cfg is None:
			return None

		from pathlib import Path
		from src.providers.kaipan_provider import KaipanAuth, KaipanProvider

		data_root = Path("data/kaipan")
		auth = KaipanAuth()
		try:
			return KaipanProvider(
				auth=auth,
				raw_dir=data_root / "raw",
				normalized_dir=data_root / "snapshots",
				snapshots_dir=data_root / "snapshots",
				kaipan_config=kaipan_cfg,
			)
		except Exception:  # noqa: BLE001
			return None

	def _all_supported_fields(self) -> set[str]:
		"""收集所有 registered skills 支持的字段（静态定义）。"""
		# skills 支持的字段（与 _skill_name_for_dataset 保持一致）
		return {
			"last_price",       # fetch_market
			"hot_topics",       # fetch_hot_topics
			"topic_constituents",  # fetch_topic_constituents
			"strong_symbols",   # fetch_strong_symbols
			"ohlcv_1d",        # fetch_ohlcv
			"indicators",       # fetch_indicators
		}

	def _skill_name_for_dataset(self, dataset: str) -> str | None:
		"""根据 dataset 返回对应的 skill 名称。"""
		mapping = {
			"last_price": "fetch_market",
			"hot_topics": "fetch_hot_topics",
			"topic_constituents": "fetch_topic_constituents",
			"strong_symbols": "fetch_strong_symbols",
			"ohlcv_1d": "fetch_ohlcv",
			"indicators": "fetch_indicators",
		}
		return mapping.get(dataset)

	async def handle(self, request: DataRequest) -> DataResponse:
		"""处理 DataRequest，按 dataset 路由到对应 skill。"""
		dataset = request.dataset
		errors: list[str] = []
		missing: list[str] = []
		combined_payload: dict[str, object] = {}

		if not dataset:
			# 兼容旧逻辑：按 fields 路由（Phase 0 last_price）
			# 注意：无 dataset 时只支持 last_price，其他字段需要明确 dataset
			requested = set(request.fields)
			if requested - {"last_price"}:
				# 非 last_price 字段需要明确 dataset
				missing_fields = sorted(requested - {"last_price"})
				return DataResponse(
					request_id=request.request_id,
					status=DataResponseStatus.capability_missing,
					missing_capabilities=missing_fields,
					errors=["DataAgent: fields other than 'last_price' require dataset to be set"],
				)

			payload = await self.call_skill(
				"fetch_market",
				symbols=request.symbols,
				fields=request.fields,
				mock_prices=self.config.data.mock_prices,
				market_data_cache_dir=self.config.data.market_data_cache_dir,
			)
			return DataResponse(
				request_id=request.request_id,
				status=DataResponseStatus.ok,
				payload=payload,
			)

		# 按 dataset 路由
		skill_name = self._skill_name_for_dataset(dataset)
		if skill_name is None:
			return DataResponse(
				request_id=request.request_id,
				status=DataResponseStatus.capability_missing,
				missing_capabilities=[dataset],
				errors=[f"DataAgent does not support dataset: {dataset}"],
			)

		provider = self._get_provider(self._PROVIDER_KEY)

		try:
			if skill_name == "fetch_market":
				payload = await self.call_skill(
					skill_name,
					symbols=request.symbols,
					fields=request.fields,
					mock_prices=self.config.data.mock_prices,
					market_data_cache_dir=self.config.data.market_data_cache_dir,
				)
				combined_payload.update(payload)
			elif skill_name in ("fetch_hot_topics", "fetch_topic_constituents", "fetch_strong_symbols"):
				payload = await self.call_skill(
					skill_name,
					dataset=dataset,
					snapshot_date=request.snapshot_date,
					slot="17-30",
					provider=provider,
				)
				combined_payload.update(payload)
			elif skill_name == "fetch_ohlcv":
				payload = await self.call_skill(
					skill_name,
					symbols=request.symbols,
					dataset=dataset,
					start_date=request.date_range[0] if request.date_range else None,
					end_date=request.date_range[1] if request.date_range else None,
					provider=provider,
				)
				combined_payload.update(payload)
			elif skill_name == "fetch_indicators":
				payload = await self.call_skill(
					skill_name,
					symbols=request.symbols,
					dataset=dataset,
					start_date=request.date_range[0] if request.date_range else None,
					end_date=request.date_range[1] if request.date_range else None,
					provider=provider,
				)
				combined_payload.update(payload)
		except Exception as exc:  # noqa: BLE001
			errors.append(f"{skill_name} error: {exc}")
			return DataResponse(
				request_id=request.request_id,
				status=DataResponseStatus.error,
				errors=errors,
			)

		return DataResponse(
			request_id=request.request_id,
			status=DataResponseStatus.ok,
			dataset=dataset,
			payload=combined_payload,
		)