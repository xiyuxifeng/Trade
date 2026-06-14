"""ManagerAgent - 编排层。

职责边界（NTL-S15-001）：
- 长期保留为编排层，负责协调 DataAgent、TraderAgent、StrategyAgent、RiskAgent
- 不承担具体业务逻辑（数据抓取、策略评估、风控判断）
- 不直接操作数据库或文件系统（委托给对应 service）
- 决策流向：编排 -> 委托 -> 汇总，不做深层业务推理

当前 Phase 0 职责：
- pre-market: 协调 TraderAgent 生成交易想法，输出 DailyReport
- after-close: 协调 DataAgent 获取最新价，输出 EvaluationResult
- 信号: 由数据库统一持久化，不再走文件版本链
- AgentTask: 仅做记录，不做任务消化

后续演进方向：
- 接入策略版本库后，ManagerAgent 负责按版本拉取快照、编排生成
- 接入 Evaluation/Postmortem 后，ManagerAgent 负责协调 ranking 与记忆写回
- 禁止在 ManagerAgent 中继续堆叠业务判断逻辑，业务逻辑应下沉到对应 module/service
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.agents.data_agent.agent import DataAgent
from src.agents.trader_agent.agent import TraderAgent
from src.agents.strategy_agent.agent import StrategyAgent
from src.agents.risk_agent.agent import RiskAgent
from src.common.config import AppConfig
from src.common.logger import get_logger
from src.common.utils import append_jsonl, ensure_dir, read_json, write_json
from src.reporting.html_reports import write_daily_report_html, write_evaluation_html
from src.market_data.stock_info_service import COMMON_MARKET_INDICES
from src.persona.router import PersonaRouter
from src.persona.market_state import DailySeriesSource, classify_market_state, load_daily_close_series
from src.persona.schemas import InstrumentFocus, MarketState
from src.persona.storage import load_persona_clusters_file
from src.schemas.contracts import (
	AgentTask,
	DailyReport,
	DataRequest,
	DataResponseStatus,
	EvaluationResult,
	IdeaEvaluation,
	TradeIdea,
)
from src.schemas.review_task import (
	ReviewEvaluationSnapshot,
	ReviewTaskDetails,
	ReviewTriggerReason,
	ReviewWritebackStatus,
)
from src.trader_profile.schemas import TraderProfile
from src.trader_profile.service import default_profiles_path, load_trader_profiles_file
from src.trader_memory.schemas import TraderMemoryItem, TraderMemoryType
from src.trader_memory.service import TraderMemoryStore
from src.market_data.service import MarketDataCache
from src.market_data.ohlcv_service import OHLCVService
from src.db.session import get_session_factory
from src.market_universe import build_topic_tags
from src.market_universe.schemas import MarketUniverse
from src.market_universe.snapshot_service import SnapshotService
from src.services.market_snapshot_service import MarketSnapshotService
from src.pipeline.completion import run_incremental_data_completion
from src.db.repositories import SignalRepository
from src.services.signal_service import SignalService
from src.evaluation.evaluation_context_service import EvaluationContextService
from src.strategy_library.service import StrategyLibraryService
from src.strategy.types import (
    PriceSpec,
    PositionSize,
    PositionSizeType,
    Signal,
    SignalContext,
    SignalSide,
    SynthesisMode,
)
from src.db.session import session_scope
from src.evaluation.evidence_pack import EvidencePack, MarketDataSnapshot
from src.evaluation.ranking_service import RankingService
from src.evaluation.metrics_calculator import compute_mfe_mae_return, compute_return_pct

if TYPE_CHECKING:
    from src.market_universe.schemas import MarketUniverse


class ManagerAgent:
    """编排层，协调各子 Agent协作。

    职责（NTL-S15-001）：
    - 委托 DataAgent 执行数据拉取
    - 委托 TraderAgent 生成交易想法
    - 委托 StrategyAgent/RiskAgent 评估信号
    - 委托 TraderMemoryStore 写记忆
    - 委托数据库仓储记录信号
    - 仅做流程编排，不承担具体业务判断
    """

    def __init__(self, *, config: AppConfig, base_dir: Path) -> None:
        """初始化 ManagerAgent，加载配置、profile、创建子 Agent。"""
        self.config = config
        self.base_dir = base_dir
        self.logger = get_logger("agent.manager")

        self.output_dir = ensure_dir(self.base_dir / self.config.storage.output_dir)
        self.tasks_path = self.output_dir / "agent_tasks.jsonl"
        self.memory_store = TraderMemoryStore()
        self.trader_profiles = self._load_trader_profiles()

        self.data_agent = DataAgent(config=config)
        self.strategy_agent = StrategyAgent()
        self.risk_agent = RiskAgent()

        self.signal_repository = SignalRepository()
        self.signal_service = SignalService(signal_repository=self.signal_repository)

        # Stage 4 新增 service（NTL-S4-006）
        self.strategy_library_service = StrategyLibraryService()
        self.snapshot_service = SnapshotService()
        self.market_snapshot_service = MarketSnapshotService()
        self.evaluation_context_service = EvaluationContextService(
            data_agent=self.data_agent,
            strategy_library_service=self.strategy_library_service,
            signal_repository=self.signal_repository,
        )

        self._persona_router: PersonaRouter | None = None
        if getattr(self.config, "persona", None) is not None and self.config.persona.enable:
            self._persona_router = PersonaRouter(top_k=max(1, int(self.config.persona.top_k)))

    def _trader_profiles_path(self) -> Path:
        """获取 trader profiles 文件路径。"""
        return default_profiles_path(base_dir=self.base_dir, config=self.config)

    def _load_trader_profiles(self) -> dict[str, TraderProfile]:
        """Load trader profiles if the profile file already exists."""

        path = self._trader_profiles_path()
        if not path.exists():
            return {}
        try:
            return load_trader_profiles_file(path).profiles_by_trader
        except Exception:  # noqa: BLE001
            self.logger.exception("failed to load trader profiles: path=%s", path)
            return {}

    def _resolve_path(self, value: str | None) -> Path | None:
        """解析路径：绝对路径直接返回，相对路径相对于 base_dir。"""
        if not value:
            return None
        p = Path(value)
        if p.is_absolute():
            return p
        return self.base_dir / p

    def _load_market_context_snapshot(
        self,
        *,
        as_of_date: date,
    ) -> tuple[dict[str, Any] | None, MarketUniverse | None]:
        """加载统一市场上下文快照与候选池快照。"""
        market_context_snapshot: dict[str, Any] | None = None
        market_universe_snapshot: MarketUniverse | None = None

        config_path = self._resolve_path("config/app.yaml")
        slot = self.config.stage4.market_universe_slot

        if config_path is not None and config_path.exists():
            try:
                loaded_snapshot = self.market_snapshot_service.load_market_snapshot(
                    config_path=config_path,
                    trade_date=as_of_date.isoformat(),
                    slot=slot,
                )
            except Exception as e:  # noqa: BLE001
                self.logger.exception(
                    "failed to load market context snapshot: date=%s, slot=%s, error=%s",
                    as_of_date,
                    slot,
                    e,
                )
                loaded_snapshot = None

            if loaded_snapshot is not None:
                market_context_snapshot = loaded_snapshot.to_dict()

        if market_universe_snapshot is None and self.config.stage4.enable:
            try:
                candidate_pool = self.snapshot_service.load(as_of_date.isoformat(), slot)
                if candidate_pool is not None:
                    market_universe_snapshot = candidate_pool
            except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
                self.logger.exception("failed to load market universe snapshot fallback: %s", e)

        if market_context_snapshot is None and market_universe_snapshot is not None:
            market_context_snapshot = asdict(market_universe_snapshot)

        return market_context_snapshot, market_universe_snapshot

    def _guess_instrument_focus(self, symbol: str) -> InstrumentFocus:
        """根据股票代码判断 instrument 类型（保守估算）。"""
        code = symbol.split(".")[0]
        if code.startswith(("110", "111", "112", "113", "118", "123", "127", "128")):
            return InstrumentFocus.cb
        if code.startswith(("51", "58", "56", "15")):
            return InstrumentFocus.etf
        return InstrumentFocus.stock

    def _load_market_state(self, *, as_of_date: date) -> MarketState:
        """Resolve MarketState from file, benchmark CSV, or cached market data.

        优先从 JSON 文件加载，其次从 benchmark CSV 加载，最后从 CSV 缓存加载。
        如需从数据库加载，请使用 _load_market_state_from_db。
        """
        p = self._resolve_path(getattr(self.config.persona, "market_state_path", None))
        if p and p.exists():
            try:
                return MarketState.model_validate(read_json(p))
            except Exception:  # noqa: BLE001
                self.logger.exception("persona.market_state_path invalid, using default: path=%s", p)

        # Phase 0.5: build from benchmark daily CSV (index/ETF)
        bench_symbol = COMMON_MARKET_INDICES[0]["symbol"]
        cache_dir = self._resolve_path(getattr(self.config.data, "market_data_cache_dir", None))
        if cache_dir:
            cache = MarketDataCache(cache_dir)
            cached_csv = cache.path_for_symbol(bench_symbol)
            if cached_csv.exists():
                try:
                    src = DailySeriesSource(symbol=bench_symbol, csv_path=cached_csv)
                    df = load_daily_close_series(src)
                    return classify_market_state(as_of_date=as_of_date, daily_df=df, symbol=bench_symbol)
                except Exception as exc:  # noqa: BLE001
                    self.logger.exception("failed to build MarketState from market data cache: error=%s", exc)
        return MarketState(as_of_date=as_of_date, benchmark_symbol=bench_symbol)

    async def _load_market_state_from_db(self, *, as_of_date: date) -> MarketState:
        """从 ohlcv_bars 数据库加载 MarketState（异步）。

        优先尝试从数据库获取 benchmark symbol 的历史数据，
        失败后 fallback 到 CSV 缓存（_load_market_state 逻辑）。

        Returns:
            MarketState 实例
        """
        bench_symbol = COMMON_MARKET_INDICES[0]["symbol"]

        try:
            factory = get_session_factory()
            service = OHLCVService(session_factory=factory)
            # 取足够长的历史（252 交易日约一年），供 classify_market_state 计算 ma20/ma60
            lookback_start = as_of_date - timedelta(days=400)
            df = await service.get_bars_as_df(bench_symbol, lookback_start, as_of_date)
            if df is not None and len(df) >= 30:
                return classify_market_state(as_of_date=as_of_date, daily_df=df, symbol=bench_symbol)
            else:
                self.logger.warning(
                        "insufficient DB bars for market state benchmark symbol, count: %s, fallback to CSV cache",
                        len(df) if df is not None else 0,
                )
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("failed to build MarketState from DB, fallback to CSV: error=%s", exc)

        # fallback 到 CSV 缓存
        return self._load_market_state(as_of_date=as_of_date)

    def _templates_dir(self) -> Path:
        # Keep template lookup relative to project root for both CLI and service runs.
        return self.base_dir / "src" / "reporting" / "templates"

    def _daily_report_path(self, as_of_date: date) -> Path:
        return self.output_dir / f"daily_report_{as_of_date.isoformat()}.json"

    def _daily_report_html_path(self, as_of_date: date) -> Path:
        return self.output_dir / f"daily_report_{as_of_date.isoformat()}.html"

    def _evaluation_path(self, as_of_date: date) -> Path:
        return self.output_dir / f"evaluation_{as_of_date.isoformat()}.json"

    def _evaluation_html_path(self, as_of_date: date) -> Path:
        return self.output_dir / f"evaluation_{as_of_date.isoformat()}.html"

    def export_daily_report_html(self, *, report: DailyReport) -> Path:
        path = self._daily_report_html_path(report.as_of_date)
        write_daily_report_html(
            report=report,
            templates_dir=self._templates_dir(),
            dest_path=path,
        )
        return path

    def export_evaluation_html(self, *, result: EvaluationResult) -> Path:
        path = self._evaluation_html_path(result.as_of_date)
        write_evaluation_html(
            result=result,
            templates_dir=self._templates_dir(),
            dest_path=path,
        )
        return path

    def _append_task(self, task: AgentTask) -> None:
        append_jsonl(self.tasks_path, task.model_dump())

    async def _fetch_full_market_data(
        self,
        symbols: list[str],
        config: AppConfig,
    ) -> dict[str, Any]:
        """从 DataAgent 获取完整行情（ohlcv_1d + indicators）。"""
        return await self.evaluation_context_service._fetch_full_market_data(symbols)

    async def _load_strategy_version_snapshot(
        self,
        strategy_version_id: str | None,
        config: AppConfig,
    ) -> list[dict]:
        """从 StrategyLibraryService 加载 rules_snapshot。"""
        strategy_version = await self.evaluation_context_service._load_strategy_version(strategy_version_id)
        return strategy_version.rules_snapshot if strategy_version else []

    def _save_evidence_pack(self, pack: EvidencePack) -> Path:
        """将 EvidencePack 写入 JSON 文件，并更新 idea_id -> pack_id 索引。

        路径：{output_dir}/evidence_packs/{pack_id}.json
        索引：{output_dir}/evidence_packs/evidence_pack_index.json

        Args:
            pack: EvidencePack 实例

        Returns:
            文件路径
        """
        pack_dir = self.output_dir / "evidence_packs"
        pack_dir.mkdir(parents=True, exist_ok=True)
        path = pack_dir / f"{pack.pack_id}.json"
        write_json(path, pack.to_dict())

        # 更新 idea_id -> pack_id 索引，供 postmortem_tasks O(1) 查询
        if pack.idea_id is not None:
            index_path = pack_dir / "evidence_pack_index.json"
            index: dict[str, str] = {}
            if index_path.exists():
                try:
                    index = read_json(index_path) or {}
                except Exception:
                    index = {}
            index[str(pack.idea_id)] = str(pack.pack_id)
            write_json(index_path, index)

        return path

    async def _persist_signal(
        self,
        *,
        signal: Signal,
        context: SignalContext,
    ) -> None:
        """将信号持久化到数据库。"""
        async with session_scope() as session:
            await self.signal_service.persist_signal(session, signal, context=context)

    async def _generate_evidence_pack(
        self,
        idea: "TradeIdea",
        daily_report: DailyReport,
        last_prices: dict[str, float],
        config: AppConfig,
    ) -> EvidencePack:
        """为单条 TradeIdea 生成完整 EvidencePack。"""
        return await self.evaluation_context_service.generate_evidence_pack(
            idea=idea,
            last_prices=last_prices,
        )

    async def _append_review_memory(
        self,
        *,
        as_of_date: date,
        idea: "TradeIdea",
        entry_price: float,
        current_price: float,
        return_pct: float,
        threshold: float,
        trigger_reason: ReviewTriggerReason,
        market_universe_snapshot: dict[str, Any] | None = None,
    ) -> TraderMemoryItem:
        """Write a short review note back into trader memory.

        Returns the created memory item so callers can record the memory_id
        in the review task details (P2-109A close-loop tracking).
        """
        canonical_tags, topic_source, raw_topic_ids = build_topic_tags(
            idea.source_topic_ids, market_universe_snapshot
        )
        memory = TraderMemoryItem(
            trader_id=idea.trader_id,
            memory_type=TraderMemoryType.review_note,
            as_of_date=as_of_date,
            symbol=idea.symbol,
            title=f"{idea.symbol} {trigger_reason.value} review note",
            content=(
                f"reason={trigger_reason.value}; entry={entry_price:.4f}; current={current_price:.4f}; "
                f"return_pct={return_pct:.6f}; threshold={threshold:.6f}"
            ),
            source="manager.run_after_close",
            source_ref=str(idea.idea_id),
            tags=["review", "evaluation"] + canonical_tags,
            topic_source=topic_source,
            raw_topic_ids=raw_topic_ids,
            importance=0.75,
        )
        await self.memory_store.append(memory)
        return memory

    def _build_review_task(
        self,
        *,
        idea: "TradeIdea",
        as_of_date: date,
        entry_price: float,
        current_price: float,
        return_pct: float,
        threshold: float,
        memory_id: str | None = None,
    ) -> AgentTask:
        """Convert an underperforming idea into a structured review task.

        P2-109A 闭环: EvaluationResult → ReviewTask created → Trader writes back review note
        """
        trigger_reason = ReviewTriggerReason.loss if return_pct < 0 else ReviewTriggerReason.below_expected
        writeback_status = ReviewWritebackStatus.written if memory_id else ReviewWritebackStatus.pending

        review_details = ReviewTaskDetails(
            review_type="trader_review",
            trigger_reason=trigger_reason,
            source_idea_id=idea.idea_id,
            symbol=idea.symbol,
            trader_id=idea.trader_id,
            evaluation_snapshot=ReviewEvaluationSnapshot(
                idea_id=idea.idea_id,
                symbol=idea.symbol,
                entry_price=round(entry_price, 6),
                current_price=round(current_price, 6),
                return_pct=round(return_pct, 6),
                threshold=round(threshold, 6),
                as_of_date=as_of_date,
            ),
            writeback_status=writeback_status,
            memory_id=memory_id,
        )

        return AgentTask(
            type="trader_review",
            title=f"Trader review required: {idea.symbol}",
            trader_id=idea.trader_id,
            idea_id=idea.idea_id,
            details=review_details.model_dump(),
        )

    async def _record_ideas_as_signals(
        self,
        ideas: list["TradeIdea"],
        as_of_date: date,
        market_universe: "MarketUniverse | None" = None,
    ) -> None:
        """将交易想法记录为信号版本，用于持久化存储和回放。

        P4-025: 信号输出持久化存储
        """
        for idea in ideas:
            # 构建信号 ID：直接使用 TradeIdea.idea_id，保证与 signals 表 UUID 主键对齐
            signal_id = str(idea.idea_id)

            # 构建上下文（NTL-S4-004: 扩展版本/快照/主题追溯字段）
            # NTL-S4-TD003: market_universe 已透传到此处，进行序列化
            universe_dict: dict[str, object] | None = asdict(market_universe) if market_universe else None
            context = SignalContext(
                features_snapshot={},
                market_state={},
                rules_snapshot=[],
                timestamp=datetime.combine(as_of_date, datetime.min.time()),
                strategy_version_id=idea.strategy_version_id,
                market_universe_snapshot=universe_dict,
                topic_source_ids=idea.source_topic_ids,
            )

            # 将 TradeIdea 映射为 Signal
            # side 字段：使用 idea.side（buy/hold/sell），映射到 SignalSide 枚举
            side_map = {"buy": SignalSide.BUY, "sell": SignalSide.SELL, "hold": SignalSide.HOLD}
            signal_side = side_map.get(str(idea.side).lower(), SignalSide.HOLD)

            signal = Signal(
                signal_id=signal_id,
                symbol=idea.symbol,
                side=signal_side,
                confidence=idea.confidence or 0.0,
                timestamp=datetime.combine(as_of_date, datetime.min.time()),
                triggered_rules=[idea.trader_id],  # 交易员 ID 作为触发规则标记
                synthesis_mode=SynthesisMode.PRIORITY,
                entry_price=PriceSpec(
                    type=idea.entry.type if idea.entry else "limit",
                    value=float(idea.entry.price) if idea.entry and idea.entry.price else 0.0,
                ) if idea.entry else None,
                position_size=None,
                stop_loss=None,
                take_profit=None,
                version="v1",
                strategy_version_id=idea.strategy_version_id,  # NTL-S4-004: 策略版本追溯
                metadata={
                    "idea_id": str(idea.idea_id),
                    "trader_id": idea.trader_id,
                    "target_price": idea.target_price,
                    "stop_loss_price": idea.stop_loss_price,
                    "rationale": idea.rationale,
                    "invalidation": idea.invalidation,
                    "style_cluster_id": idea.style_cluster_id,
                    "style_cluster_label": idea.style_cluster_label,
                    "style_score": idea.style_score,
                    "style_reasons": idea.style_reasons or [],
                    "as_of_date": as_of_date.isoformat(),
                    "source_topic_ids": idea.source_topic_ids,
                    "evidence_refs": idea.evidence_refs,
                    "context": context,
                },
            )

            await self._persist_signal(signal=signal, context=context)

        self.logger.info(f"Recorded {len(ideas)} ideas as signal versions")

    async def run_pre_market(self, *, as_of_date: date, force: bool = False) -> DailyReport:
        """收集交易想法并持久化盘前日报。

        流程：
        1. 检查是否已有 report（存在且非 force 则直接返回）
        2. 加载 market_universe 快照（Stage 4 路径）
        3. 对每个 trader 调用 PreMarketService 生成 ideas
        4. 保存 DailyReport（包含 market_universe_snapshot）
        5. 可选：persona style routing

        Args:
            as_of_date: 交易日期
            force: 是否强制重新生成（跳过缓存）

        Returns:
            DailyReport 实例
        """

        report_path = self._daily_report_path(as_of_date)
        if report_path.exists() and not force:
            payload = read_json(report_path)
            return DailyReport.model_validate(payload)

        # === Stage 4 路径：尝试加载统一市场上下文快照（所有 trader 共享同一快照）===
        # NTL-S4-009: stage4.enable 控制是否使用新版盘前链路
        market_context_snapshot, market_universe = self._load_market_context_snapshot(as_of_date=as_of_date)
        if self.config.stage4.enable and market_context_snapshot is None and market_universe is None:
            self._append_task(
                AgentTask(
                    type="data_missing",
                    title="Market context snapshot load failed",
                    details={"date": as_of_date.isoformat(), "slot": self.config.stage4.market_universe_slot},
                )
            )

        ideas = []
        used_strategy_version_ids: list[str] = []  # NTL-S4-008: 追踪本次使用的策略版本

        # === NTL-S4-010: 委托 PreMarketService 处理 per-trader 编排逻辑 ===
        from src.agents.manager_agent.premarket_service import PreMarketService
        premarket_svc = PreMarketService(
            data_agent=self.data_agent,
            strategy_agent=self.strategy_agent,
            risk_agent=self.risk_agent,
            memory_store=self.memory_store,
            trader_profiles=self.trader_profiles,
            config=self.config,
            snapshot_service=self.snapshot_service,
            strategy_library_service=self.strategy_library_service,
        )

        for trader_cfg in self.config.traders:
            result = await premarket_svc.run_for_trader(
                trader_cfg=trader_cfg,
                market_universe=market_universe,
                as_of_date=as_of_date,
            )
            ideas.extend(result.ideas)
            if result.strategy_version_id:
                used_strategy_version_ids.append(result.strategy_version_id)
            # 记录 missing symbols 任务
            for task in result.missing_symbol_tasks:
                self._append_task(task)

        # === NTL-S7-007: 规则池预测集成 ===
        # 从规则池加载高置信度规则预测，作为盘前辅助信号
        rule_prediction_count = 0
        rule_predictions = []
        if self.config.stage4.enable:
            try:
                async with session_scope() as session:
                    from src.rule_pool.prediction import RulePoolPredictionService
                    prediction_svc = RulePoolPredictionService(session)
                    rule_predictions = await prediction_svc.predict_high_confidence_rules(
                        threshold=0.8, limit=20
                    )
                    rule_prediction_count = len(rule_predictions)
                    if rule_predictions:
                        self.logger.info(
                            "规则池预测已加载: %d 条高置信度规则（rule_types=%s）",
                            len(rule_predictions),
                            [p.rule_type for p in rule_predictions[:5]],
                        )
            except Exception as e:
                self.logger.exception("规则池预测加载失败: %s", e)

        if rule_predictions and ideas:
            self._apply_rule_pool_predictions_to_ideas(ideas, rule_predictions)

        # 构建 highlights
        highlights = [f"Generated {len(ideas)} trade ideas"]
        if rule_prediction_count:
            highlights.append(f"规则池预测: {rule_prediction_count} 条高置信度规则已集成")

        report = DailyReport(
            as_of_date=as_of_date,
            ideas=ideas,
            highlights=highlights,
            strategy_version_ids=list(dict.fromkeys(used_strategy_version_ids)),  # NTL-S4-008: 去重后保留顺序
            market_universe_snapshot=asdict(market_universe) if market_universe is not None else None,
            market_context_snapshot=market_context_snapshot,
        )

        # Optional: persona style routing (Phase 1 MVP)
        if self._persona_router and self.config.persona.clusters_path:
            clusters_path = self._resolve_path(self.config.persona.clusters_path)
            if clusters_path and clusters_path.exists():
                clusters_file = load_persona_clusters_file(clusters_path)
                market_state = await self._load_market_state_from_db(as_of_date=as_of_date)
                decisions = []
                for idea in ideas:
                    clusters = clusters_file.clusters_by_trader.get(idea.trader_id, [])
                    if not clusters:
                        continue
                    decision = self._persona_router.route_symbol(
                        trader_id=idea.trader_id,
                        symbol=idea.symbol,
                        as_of_date=as_of_date,
                        instrument_focus=self._guess_instrument_focus(idea.symbol),
                        market_state=market_state,
                        clusters=clusters,
                    )
                    idea.style_cluster_id = decision.selected_cluster_id
                    idea.style_cluster_label = decision.selected_cluster_label
                    idea.style_score = decision.score
                    idea.style_reasons = list(decision.explanation.reasons or [])
                    decisions.append(decision.model_dump())

                route_path = self.output_dir / f"persona_route_{as_of_date.isoformat()}.json"
                write_json(
                    route_path,
                    {
                        "as_of_date": as_of_date.isoformat(),
                        "clusters_path": str(clusters_path),
                        "decisions": decisions,
                    },
                )
                report.highlights.append(
                    f"Persona router enabled: decisions={len(decisions)} clusters={clusters_path}"
                )
            else:
                report.risks.append("persona.enable=true but clusters_path missing or not found")

        # P4-025: 记录信号版本到持久化存储
        # NTL-S4-TD003: 透传 market_universe 以便填充 SignalContext.market_universe_snapshot
        await self._record_ideas_as_signals(ideas=ideas, as_of_date=as_of_date, market_universe=market_universe)

        write_json(report_path, report.model_dump())
        return report

    def _apply_rule_pool_predictions_to_ideas(
        self,
        ideas: list[TradeIdea],
        predictions: list[object],
    ) -> None:
        """将高置信度规则池预测注入 TradeIdea，使规则池真实影响盘前推荐。"""
        if not ideas or not predictions:
            return

        top_predictions = predictions[:3]
        rule_ids = [
            str(getattr(prediction, "rule_id", ""))
            for prediction in top_predictions
            if getattr(prediction, "rule_id", None)
        ]
        if not rule_ids:
            return

        confidence_boost = min(0.08, 0.05 + 0.01 * max(0, len(rule_ids) - 1))
        rule_hint = "规则池预测: " + ", ".join(rule_ids)

        for idea in ideas:
            current_confidence = float(idea.confidence or 0.0)
            idea.confidence = round(min(0.95, current_confidence + confidence_boost), 3)
            for rule_id in rule_ids:
                ref = f"rule_pool:{rule_id}"
                if ref not in idea.evidence_refs:
                    idea.evidence_refs.append(ref)
            idea.rationale = (
                f"{idea.rationale or ''} | {rule_hint}"
                if idea.rationale
                else rule_hint
            )

    async def _get_account_snapshot(
        self,
        *,
        trade_idea: "TradeIdea" = None,
        account_id: str = "default",
    ) -> "AccountSnapshot":
        """从真实 TradeLog 构建 AccountSnapshot。"""
        snapshot = await self.evaluation_context_service.get_account_snapshot(
            trade_idea=trade_idea,
            account_id=account_id,
        )
        return snapshot

    async def evaluate_signal(
        self,
        trade_idea: "TradeIdea",
        market_data: dict[str, Any]
    ) -> Signal | None:
        """
        评估交易想法：StrategyAgent 合成 + RiskAgent 风控

        Args:
            trade_idea: 交易想法
            market_data: 市场数据

        Returns:
            最终 Signal 或 None（拒绝）
        """
        # 1. StrategyAgent 生成 RawSignal
        raw_signal = await self.strategy_agent.generate_raw_signal(
            symbol=trade_idea.symbol,
            trade_idea=trade_idea,
            market_data=market_data,
            features={},  # 可预计算
            rules=[],      # 可从配置获取
            synthesis_mode=SynthesisMode.PRIORITY
        )

        # 2. 获取 AccountSnapshot（优先从真实交易记录构建，失败时 fallback 模拟账户）
        account = await self._get_account_snapshot(
            trade_idea=trade_idea,
        )

        # 3. RiskAgent 风控检查
        final_signal = await self.risk_agent.check(
            raw_signal=raw_signal,
            account=account,
            market_data=market_data,
            risk_config=self.config.evaluation or {}
        )

        # 4. 存储
        if not final_signal.side == SignalSide.HOLD and final_signal.side != "HOLD":
            context = SignalContext(
                features_snapshot={},
                market_state=market_data,
                rules_snapshot=[],
                timestamp=datetime.now(timezone.utc)
            )
            await self._persist_signal(signal=final_signal, context=context)

        return final_signal

    async def run_after_close(self, *, as_of_date: date, force: bool = False) -> EvaluationResult:
        """评估盘前生成的 ideas 并写入 TraderMemory。

        流程：
        1. 检查是否已有 evaluation（存在且非 force 则直接返回）
        2. 加载 DailyReport 获取盘前 ideas 和 market_context_snapshot
        3. 获取最新价格（通过 DataAgent）
        4. 对每个 idea 计算 return_pct，判断是否达到 min_expected_return
        5. 根据 return_pct 创建 success_case/failure_case memory
        6. 触发 review 条件时创建 review_note memory
        7. 存储 EvaluationResult

        Args:
            as_of_date: 交易日期
            force: 是否强制重新评估（跳过缓存）

        Returns:
            EvaluationResult 实例
        """

        evaluation_path = self._evaluation_path(as_of_date)
        if evaluation_path.exists() and not force:
            payload = read_json(evaluation_path)
            return EvaluationResult.model_validate(payload)

        # 盘后自动补全增量数据（行情、快照等），确保评估/归因/优化链路数据完整
        self.logger.info("开始盘后增量数据自动补全...")
        await run_incremental_data_completion(config=self.config, as_of_date=as_of_date, force=force)
        self.logger.info("盘后增量数据补全完成。")

        report_path = self._daily_report_path(as_of_date)
        if not report_path.exists():
            raise FileNotFoundError(
                f"Daily report not found for {as_of_date}. Run pre-market first: {report_path}"
            )

        daily_report = DailyReport.model_validate(read_json(report_path))
        market_context_snapshot = daily_report.market_context_snapshot or daily_report.market_universe_snapshot

        symbols = sorted({i.symbol for i in daily_report.ideas})
        req = DataRequest(trader_id="manager", symbols=symbols, fields=["last_price"])
        resp = await self.data_agent.handle(req)

        last_prices: dict[str, float] = {}
        if resp.status == DataResponseStatus.ok:
            last_prices = resp.payload.get("last_price", {})
        elif resp.status == DataResponseStatus.capability_missing:
            self._append_task(
                AgentTask(
                    type="capability_missing",
                    title="DataAgent capability missing for evaluation",
                    details={"missing": resp.missing_capabilities},
                )
            )

        evaluations: list[IdeaEvaluation] = []
        # NTL-S5-011: 收集待写入 ranking 的数据
        pending_rankings: list[tuple[EvidencePack, float, float, float]] = []

        for idea in daily_report.ideas:
            entry_price = idea.entry.price
            current_price = last_prices.get(idea.symbol)

            if entry_price is None:
                evaluations.append(
                    IdeaEvaluation(
                        idea_id=idea.idea_id,
                        symbol=idea.symbol,
                        entry_price=None,
                        current_price=current_price,
                        status="not_evaluated",
                        partial_data=False,
                        fallback_reason="missing_entry_price",
                        notes=["Missing entry price"],
                    )
                )
                continue

            # NTL-S5-009: 先生成 EvidencePack 获取 bars 数据
            evidence_pack = await self._generate_evidence_pack(
                idea=idea,
                daily_report=daily_report,
                last_prices=last_prices,
                config=self.config,
            )
            self._save_evidence_pack(evidence_pack)

            # NTL-S5-013: 使用 compute_mfe_mae_return 计算
            bars = evidence_pack.market_data.bars
            entry_price_val = float(entry_price)
            target_price = evidence_pack.market_data.target_price
            stop_loss_price = evidence_pack.market_data.stop_loss_price

            mfe_val, mae_val, return_pct, exit_triggered, exit_date, halted_dates, limit_locked_dates, eval_date = compute_mfe_mae_return(
                bars=bars,
                entry_price=entry_price_val,
                entry_date=str(as_of_date),
                target_price=target_price,
                stop_loss_price=stop_loss_price,
                symbol=idea.symbol,
            )

            # 判断数据情况并决定 status / 结构化扩展字段
            partial_data = False
            fallback_reason: str | None = None
            if not bars:
                # NTL-S5-013: fallback 到 last_prices（旧逻辑保留作为降级路径）
                if current_price is not None:
                    return_pct = compute_return_pct(entry_price_val, float(current_price))
                    eval_status = "fallback"
                    fallback_reason = "no_bars_data"
                    notes_text = (
                        f"[fallback] bars=0, return_pct={round(return_pct, 6):.6f}, "
                        f"reason={fallback_reason}, last_price={float(current_price):.4f}"
                    )
                    self.logger.warning(
                        "fallback evaluation without bars for symbol=%s trader_id=%s reason=%s last_price=%s",
                        idea.symbol,
                        idea.trader_id,
                        fallback_reason,
                        current_price,
                    )
                else:
                    eval_status = "not_evaluated"
                    fallback_reason = "missing_last_price"
                    notes_text = "[not_evaluated] reason=missing_last_price"
                    self.logger.warning(
                        "evaluation skipped because both bars and last_price are missing for symbol=%s trader_id=%s",
                        idea.symbol,
                        idea.trader_id,
                    )
                    self._append_task(
                        AgentTask(
                            type="data_missing",
                            title=f"Missing price for evaluation: {idea.symbol}",
                            trader_id=idea.trader_id,
                            idea_id=idea.idea_id,
                            details={"symbol": idea.symbol, "field": "last_price"},
                        )
                    )
            elif len(bars) < 2:
                # NTL-S5-013: partial data
                eval_status = "partial"
                partial_data = True
                notes_text = (
                    f"[partial] bars={len(bars)}, mfe={mfe_val:.4f}, mae={mae_val:.4f}, "
                    f"return_pct={round(return_pct, 6):.6f}, insufficient_bars"
                )
                self.logger.warning(
                    "partial evaluation data for symbol=%s trader_id=%s bars=%s entry_date=%s exit_date=%s",
                    idea.symbol,
                    idea.trader_id,
                    len(bars),
                    as_of_date,
                    exit_date,
                )
            else:
                # NTL-S5-013: 完整数据
                eval_status = "ok"
                notes_text = f"mfe={mfe_val:.4f}, mae={mae_val:.4f}, return_pct={round(return_pct, 6):.6f}, exit={exit_triggered}"

            # 记录停牌/无成交信息（如有）
            if halted_dates:
                notes_text += f", halted_dates={halted_dates}"
            if limit_locked_dates:
                notes_text += f", limit_locked_dates={limit_locked_dates}"

            # NTL-S5-013: current_price 语义变为 exit_price（bars 末bar收盘价或 last_price）
            if bars:
                exit_price = float(bars[-1]["close"])
            elif current_price is not None:
                exit_price = float(current_price)
            else:
                exit_price = None

            evaluations.append(
                IdeaEvaluation(
                    idea_id=idea.idea_id,
                    symbol=idea.symbol,
                    entry_price=entry_price_val,
                    current_price=exit_price,  # deprecated: 语义变为 exit_price
                    return_pct=round(return_pct, 6),
                    status=eval_status,
                    partial_data=partial_data,
                    fallback_reason=fallback_reason,
                    notes=[notes_text],
                )
            )

            # NTL-S5-011: pending_rankings 使用已计算的 mfe/mae/return_pct
            pending_rankings.append((evidence_pack, mfe_val, mae_val, return_pct))

            # trigger review tasks
            min_ret = float(self.config.evaluation.min_expected_return)
            memory_type = (
                TraderMemoryType.success_case
                if return_pct >= min_ret and return_pct >= 0
                else TraderMemoryType.failure_case
            )

            # NTL-S5-006 前置：构建 canonical tags
            canonical_tags, topic_source, raw_topic_ids = build_topic_tags(
                idea.source_topic_ids, market_context_snapshot
            )

            await self.memory_store.append(
                TraderMemoryItem(
                    trader_id=idea.trader_id,
                    memory_type=memory_type,
                    as_of_date=as_of_date,
                    symbol=idea.symbol,
                    title=f"{idea.symbol} {memory_type.value.replace('_', ' ')}",
                    content=(
                        f"entry={entry_price_val:.4f}, exit={exit_price:.4f}, "
                        f"return_pct={round(return_pct, 6):.6f}, threshold={min_ret:.6f}"
                    ),
                    source="manager.run_after_close",
                    source_ref=str(idea.idea_id),
                    tags=["evaluation", memory_type.value] + canonical_tags,
                    topic_source=topic_source,
                    raw_topic_ids=raw_topic_ids,
                    importance=0.8 if memory_type == TraderMemoryType.success_case else 0.9,
                )
            )
            if (self.config.evaluation.loss_trigger and return_pct < 0) or (return_pct < min_ret):
                # 1. 先计算 trigger_reason（供后续使用）
                trigger_reason = ReviewTriggerReason.loss if return_pct < 0 else ReviewTriggerReason.below_expected

                # 2. 创建 memory，获取 memory_id
                memory = await self._append_review_memory(
                    as_of_date=as_of_date,
                    idea=idea,
                    entry_price=float(entry_price),
                    current_price=float(current_price),
                    return_pct=return_pct,
                    threshold=min_ret,
                    trigger_reason=trigger_reason,
                    market_universe_snapshot=market_context_snapshot,
                )
                memory_id = str(memory.memory_id)

                # 3. 构建任务（带 memory_id，此时 writeback_status=written）
                review_task = self._build_review_task(
                    idea=idea,
                    as_of_date=as_of_date,
                    entry_price=float(entry_price),
                    current_price=float(current_price),
                    return_pct=return_pct,
                    threshold=min_ret,
                    memory_id=memory_id,
                )

                # 4. 落盘（此时 task 已包含完整信息）
                self._append_task(review_task)

                # NTL-S5-008: 创建 postmortem_analysis 任务
                # NTL-S5-012: 从 signal_context 提取 auto_attribution
                signal_ctx = evidence_pack.signal_context
                if signal_ctx:
                    auto_attribution = {
                        "reason": str(signal_ctx.triggered_rules) if hasattr(signal_ctx, "triggered_rules") else "",
                        "confidence": getattr(signal_ctx, "confidence", 0.5),
                    }
                else:
                    auto_attribution = {}
                postmortem_task = AgentTask(
                    type="postmortem_analysis",
                    title=f"Postmortem for {idea.symbol} on {as_of_date}",
                    trader_id=idea.trader_id,
                    idea_id=idea.idea_id,
                    details={
                        "idea_id": str(idea.idea_id),
                        "trade_date": str(as_of_date),
                        "trader_id": idea.trader_id,
                        "symbol": idea.symbol,
                        "auto_attribution": auto_attribution,
                    },
                )
                self._append_task(postmortem_task)

        # NTL-S5-011: 生成盘后 ranking
        if pending_rankings:
            async with session_scope() as session:
                ranking_svc = RankingService(session, output_dir=self.output_dir)
                for pack, mfe_val, mae_val, return_pct_val in pending_rankings:
                    await ranking_svc.add_entry_from_metrics(
                        evidence_pack=pack,
                        mfe=mfe_val,
                        mae=mae_val,
                        return_pct=return_pct_val,
                    )
                await ranking_svc.generate_ranking_and_save(trade_date=str(as_of_date))

        summary = [
            f"Evaluated {len(evaluations)} ideas",
            f"Output dir: {self.output_dir}",
        ]

        result = EvaluationResult(as_of_date=as_of_date, evaluations=evaluations, summary=summary)
        write_json(evaluation_path, result.model_dump())
        return result
