"""盘前链路 Service（NTL-S4-010）。

职责：
- 封装 per-trader 盘前想法生成的完整编排逻辑
- ManagerAgent 只保留循环调用，不承担具体业务逻辑

被提取的逻辑（原 ManagerAgent.run_pre_market per-trader 循环体）：
- 策略版本加载
- TraderAgent.generate_trade_ideas 调用
- 定向深挖 DataRequest（NTL-S4-007）
- 信号评估（evaluate_signal）
- missing symbols 处理
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any

from src.agents.trader_agent.agent import TraderAgent
from src.agents.strategy_agent.agent import StrategyAgent
from src.agents.risk_agent.agent import RiskAgent
from src.common.config import AppConfig, Stage4Config, TraderConfig
from src.common.logger import get_logger
from src.market_universe.schemas import MarketUniverse
from src.risk.types import AccountSnapshot
from src.schemas.contracts import AgentTask, DataRequest, DataResponseStatus, TradeIdea
from src.strategy_library.schemas import StrategyVersion
from src.strategy.types import Signal
from src.trader_memory.service import TraderMemoryStore
from src.trader_profile.schemas import TraderProfile

if TYPE_CHECKING:
    from src.agents.data_agent import DataAgent

logger = get_logger(__name__)


@dataclass
class PreMarketResult:
    """Per-trader 盘前生成结果"""
    ideas: list[TradeIdea]
    strategy_version_id: str | None
    evaluated_signals: list[Signal]
    missing_symbol_tasks: list[AgentTask]


class PreMarketService:
    """Per-trader 盘前想法生成 Service。

    封装单 trader 的完整盘前编排逻辑：
    1. 策略版本加载（可选）
    2. TraderAgent 生成想法
    3. 定向深挖 DataRequest（NTL-S4-007）
    4. 信号评估
    5. Missing symbols 任务生成

    ManagerAgent 只负责循环调用，不承担具体业务逻辑。
    """

    def __init__(
        self,
        data_agent: DataAgent,
        strategy_agent: StrategyAgent,
        risk_agent: RiskAgent,
        memory_store: TraderMemoryStore,
        trader_profiles: dict[str, TraderProfile],
        config: AppConfig,
        snapshot_service,  # SnapshotService
        strategy_library_service,  # StrategyLibraryService
    ) -> None:
        self.data_agent = data_agent
        self.strategy_agent = strategy_agent
        self.risk_agent = risk_agent
        self.memory_store = memory_store
        self.trader_profiles = trader_profiles
        self.config = config
        self.snapshot_service = snapshot_service
        self.strategy_library_service = strategy_library_service

    async def run_for_trader(
        self,
        trader_cfg: TraderConfig,
        market_universe: MarketUniverse | None,
        as_of_date: date,
    ) -> PreMarketResult:
        """为单个 trader 运行盘前链路。

        Args:
            trader_cfg: trader 配置
            market_universe: 候选池快照（可选）
            as_of_date: 交易日期

        Returns:
            PreMarketResult：包含 ideas、使用的策略版本 ID、评估后的信号、missing symbols 任务
        """
        from src.db.session import session_scope

        # === 策略版本加载（Stage 4 路径）===
        strategy_version: StrategyVersion | None = None
        if self.config.stage4.enable:
            try:
                async with session_scope() as session:
                    strategy_version = await self.strategy_library_service.get_current_released_version(
                        session=session,
                        trader_id=trader_cfg.trader_id,
                        strategy_date=as_of_date,
                    )
                if strategy_version is not None:
                    logger.debug(
                        "策略版本加载成功: trader=%s, date=%s, version=%s",
                        trader_cfg.trader_id,
                        as_of_date,
                        strategy_version.version_id,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "策略版本加载异常: trader=%s, date=%s, error=%s",
                    trader_cfg.trader_id,
                    as_of_date,
                    e,
                )
                if self.config.stage4.allow_phase0_fallback:
                    pass  # 降级到 Phase 0
                else:
                    logger.info(
                        "Trader跳过（无策略版本且不允许降级）: trader=%s, date=%s",
                        trader_cfg.trader_id,
                        as_of_date,
                    )
                    return PreMarketResult(
                        ideas=[],
                        strategy_version_id=None,
                        evaluated_signals=[],
                        missing_symbol_tasks=[],
                    )
        else:
            logger.debug(
                "Stage4未启用，跳过策略版本加载: trader=%s, date=%s",
                trader_cfg.trader_id,
                as_of_date,
            )

        # === TraderAgent 生成想法 ===
        trader = TraderAgent(
            trader=trader_cfg,
            memory_store=self.memory_store,
            trader_profile=self.trader_profiles.get(trader_cfg.trader_id),
        )

        # === NTL-S4-007: 定向深挖 DataRequest ===
        deep_market_data: dict[str, Any] = {}
        if strategy_version is not None and strategy_version.rules_snapshot:
            candidate_symbols = [
                rec.symbol for rec in strategy_version.recommendations if rec.symbol
            ]
            needed_requests = self._plan_data_requests(strategy_version, candidate_symbols)
            for dataset, fields in needed_requests.items():
                req = DataRequest(
                    trader_id=trader_cfg.trader_id,
                    symbols=candidate_symbols,
                    fields=fields,
                    dataset=dataset,
                )
                resp = await self.data_agent.handle(req)
                if resp.status == DataResponseStatus.ok:
                    deep_market_data[dataset] = resp.payload

        ideas = await trader.generate_trade_ideas(
            as_of_date=as_of_date,
            data_agent=self.data_agent,
            strategy_version=strategy_version,
            market_universe=market_universe,
        )

        # === 信号评估 ===
        evaluated_signals: list[Signal] = []
        for idea in ideas:
            signal = await self._evaluate_idea(idea, deep_market_data)
            if signal:
                evaluated_signals.append(signal)

        # === Missing symbols 任务 ===
        missing_symbol_tasks: list[AgentTask] = []
        if self.config.stage4.enable:
            missing_symbols = [
                s for s in trader_cfg.watchlist
                if s not in self.config.data.mock_prices
            ]
            for s in missing_symbols:
                missing_symbol_tasks.append(
                    AgentTask(
                        type="data_missing",
                        title=f"Missing mock price for {s}",
                        trader_id=trader_cfg.trader_id,
                        details={"symbol": s, "field": "last_price"},
                    )
                )

        return PreMarketResult(
            ideas=ideas,
            strategy_version_id=strategy_version.version_id if strategy_version else None,
            evaluated_signals=evaluated_signals,
            missing_symbol_tasks=missing_symbol_tasks,
        )
        logger.info(
            "PreMarketService完成: trader=%s, date=%s, ideas=%d, evaluated=%d, missing_tasks=%d",
            trader_cfg.trader_id,
            as_of_date,
            len(ideas),
            len(evaluated_signals),
            len(missing_symbol_tasks),
        )

    async def _evaluate_idea(self, idea: TradeIdea, market_data: dict[str, Any]) -> Signal | None:
        """评估单个交易想法。"""
        raw_signal = await self.strategy_agent.generate_raw_signal(
            symbol=idea.symbol,
            trade_idea=idea,
            market_data=market_data,
            features={},
            synthesis_mode=None,
        )

        from datetime import datetime, timezone
        account = AccountSnapshot(
            account_id="default",
            timestamp=datetime.now(timezone.utc),
            net_value=100000.0,
            cash=50000.0,
            total_position_value=50000.0,
            positions=[],
            daily_pnl=0.0,
            total_pnl=0.0,
        )

        return await self.risk_agent.check(
            raw_signal=raw_signal,
            account=account,
            market_data=market_data,
            risk_config=self.config.evaluation or {},
        )

    def _plan_data_requests(
        self,
        strategy_version: StrategyVersion,
        candidate_symbols: list[str],
    ) -> dict[str, list[str]]:
        """分析 rules_snapshot 中引用的字段，决定需要发起哪些额外 DataRequest。

        NTL-S4-007 定向深挖：
        - 从 rules_snapshot 的 condition 表达式中提取字段名（如 rsi、macd、volume）
        - 将字段名映射到 DataRequest 支持的 fields（indicators、ohlcv_1d 等）
        - 返回需要发起额外取数的 fields 列表
        """
        # 规则字段 → dataset 映射
        FIELD_TO_DATASET: dict[str, str] = {
            # 技术指标
            "rsi": "indicators",
            "macd": "indicators",
            "bollinger": "indicators",
            "atr": "indicators",
            "kdj": "indicators",
            "cci": "indicators",
            "obv": "indicators",
            # 行情数据
            "close": "ohlcv_1d",
            "open": "ohlcv_1d",
            "high": "ohlcv_1d",
            "low": "ohlcv_1d",
            "volume": "ohlcv_1d",
            "turnover": "ohlcv_1d",
        }

        needed_datasets: dict[str, set[str]] = {}

        for rule in (strategy_version.rules_snapshot or []):
            condition = rule.get("condition", {})
            if isinstance(condition, dict):
                # 递归从 condition dict 中提取字段
                self._extract_fields_from_condition(condition, FIELD_TO_DATASET, needed_datasets)
            elif isinstance(condition, str):
                # 从字符串中提取字段名
                for field, dataset in FIELD_TO_DATASET.items():
                    if field in condition.lower():
                        needed_datasets.setdefault(dataset, set()).add(field)

        return {dataset: list(fields) for dataset, fields in needed_datasets.items()}

    def _extract_fields_from_condition(
        self,
        condition: dict[str, Any],
        field_map: dict[str, str],
        result: dict[str, set[str]],
    ) -> None:
        """递归从 condition dict 中提取字段名。"""
        for value in condition.values():
            if isinstance(value, dict):
                self._extract_fields_from_condition(value, field_map, result)
            elif isinstance(value, str):
                for field, dataset in field_map.items():
                    if field in value.lower():
                        result.setdefault(dataset, set()).add(field)
