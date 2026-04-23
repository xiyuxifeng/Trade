"""ManagerAgent - 编排层。

职责边界（NTL-S15-001）：
- 长期保留为编排层，负责协调 DataAgent、TraderAgent、StrategyAgent、RiskAgent
- 不承担具体业务逻辑（数据抓取、策略评估、风控判断）
- 不直接操作数据库或文件系统（委托给对应 service）
- 决策流向：编排 -> 委托 -> 汇总，不做深层业务推理

当前 Phase 0 职责：
- pre-market: 协调 TraderAgent 生成交易想法，输出 DailyReport
- after-close: 协调 DataAgent 获取最新价，输出 EvaluationResult
- 信号版本: 委托 SignalVersioning 记录，不自己管理存储格式
- AgentTask: 仅做记录，不做任务消化

后续演进方向：
- 接入策略版本库后，ManagerAgent 负责按版本拉取快照、编排生成
- 接入 Evaluation/Postmortem 后，ManagerAgent 负责协调 ranking 与记忆写回
- 禁止在 ManagerAgent 中继续堆叠业务判断逻辑，业务逻辑应下沉到对应 module/service
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from src.agents.data_agent.agent import DataAgent
from src.agents.trader_agent.agent import TraderAgent
from src.agents.strategy_agent.agent import StrategyAgent
from src.agents.risk_agent.agent import RiskAgent
from src.common.config import AppConfig
from src.common.logger import get_logger
from src.common.utils import append_jsonl, ensure_dir, read_json, write_json
from src.reporting.html_reports import write_daily_report_html, write_evaluation_html
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
from src.trader_memory.service import TraderMemoryStore, default_memory_path
from src.market_data.service import MarketDataCache
from src.strategy.signal_version import SignalVersioning
from src.strategy.types import (
    PriceSpec,
    PositionSize,
    PositionSizeType,
    Signal,
    SignalContext,
    SignalSide,
    SynthesisMode,
)


class ManagerAgent:
    """编排层，协调各子 Agent协作。

    职责（NTL-S15-001）：
    - 委托 DataAgent 执行数据拉取
    - 委托 TraderAgent 生成交易想法
    - 委托 StrategyAgent/RiskAgent 评估信号
    - 委托 TraderMemoryStore 写记忆
    - 委托 SignalVersioning 记录信号版本
    - 仅做流程编排，不承担具体业务判断
    """

    def __init__(self, *, config: AppConfig, base_dir: Path) -> None:
        self.config = config
        self.base_dir = base_dir
        self.logger = get_logger("agent.manager")

        self.output_dir = ensure_dir(self.base_dir / self.config.storage.output_dir)
        self.tasks_path = self.output_dir / "agent_tasks.jsonl"
        self.memory_store = TraderMemoryStore(path=default_memory_path(base_dir=self.base_dir, config=self.config))
        self.trader_profiles = self._load_trader_profiles()

        self.data_agent = DataAgent(config=config)
        self.strategy_agent = StrategyAgent()
        self.risk_agent = RiskAgent()

        # 信号版本控制 - 记录所有生成的交易想法
        self.signal_versioning = SignalVersioning(
            storage_path=self.output_dir / "signals"
        )

        self._persona_router: PersonaRouter | None = None
        if getattr(self.config, "persona", None) is not None and self.config.persona.enable:
            self._persona_router = PersonaRouter(top_k=max(1, int(self.config.persona.top_k)))

    def _trader_profiles_path(self) -> Path:
        return default_profiles_path(base_dir=self.base_dir, config=self.config)

    def _load_trader_profiles(self) -> dict[str, TraderProfile]:
        """Load trader profiles if the profile file already exists."""

        path = self._trader_profiles_path()
        if not path.exists():
            return {}
        try:
            return load_trader_profiles_file(path).profiles_by_trader
        except Exception:  # noqa: BLE001
            self.logger.warning("failed to load trader profiles", path=str(path))
            return {}

    def _resolve_path(self, value: str | None) -> Path | None:
        if not value:
            return None
        p = Path(value)
        if p.is_absolute():
            return p
        return self.base_dir / p

    def _guess_instrument_focus(self, symbol: str) -> InstrumentFocus:
        # Heuristic for CN market. Keep it conservative.
        code = symbol.split(".")[0]
        if code.startswith(("110", "111", "112", "113", "118", "123", "127", "128")):
            return InstrumentFocus.cb
        if code.startswith(("51", "58", "56", "15")):
            return InstrumentFocus.etf
        return InstrumentFocus.stock

    def _load_market_state(self, *, as_of_date: date) -> MarketState:
        """Resolve MarketState from file, benchmark CSV, or cached market data."""

        p = self._resolve_path(getattr(self.config.persona, "market_state_path", None))
        if p and p.exists():
            try:
                return MarketState.model_validate(read_json(p))
            except Exception:  # noqa: BLE001
                self.logger.warning("persona.market_state_path invalid, using default", path=str(p))

        # Phase 0.5: build from benchmark daily CSV (index/ETF)
        bench_csv = self._resolve_path(getattr(self.config.persona, "market_state_benchmark_csv", None))
        bench_symbol = getattr(self.config.persona, "market_state_benchmark_symbol", None)
        if bench_csv and bench_csv.exists() and bench_symbol:
            try:
                src = DailySeriesSource(symbol=bench_symbol, csv_path=bench_csv)
                df = load_daily_close_series(src)
                return classify_market_state(as_of_date=as_of_date, daily_df=df, symbol=bench_symbol)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("failed to build MarketState from benchmark CSV", error=str(exc))
        cache_dir = self._resolve_path(getattr(self.config.data, "market_data_cache_dir", None))
        if cache_dir and bench_symbol:
            cache = MarketDataCache(cache_dir)
            cached_csv = cache.path_for_symbol(bench_symbol)
            if cached_csv.exists():
                try:
                    src = DailySeriesSource(symbol=bench_symbol, csv_path=cached_csv)
                    df = load_daily_close_series(src)
                    return classify_market_state(as_of_date=as_of_date, daily_df=df, symbol=bench_symbol)
                except Exception as exc:  # noqa: BLE001
                    self.logger.warning("failed to build MarketState from market data cache", error=str(exc))
        return MarketState(as_of_date=as_of_date)

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

    def _append_review_memory(
        self,
        *,
        as_of_date: date,
        idea: "TradeIdea",
        entry_price: float,
        current_price: float,
        return_pct: float,
        threshold: float,
        trigger_reason: ReviewTriggerReason,
    ) -> TraderMemoryItem:
        """Write a short review note back into trader memory.

        Returns the created memory item so callers can record the memory_id
        in the review task details (P2-109A close-loop tracking).
        """
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
            tags=["review", "evaluation"],
            importance=0.75,
        )
        self.memory_store.append(memory)
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

    def _record_ideas_as_signals(self, ideas: list["TradeIdea"], as_of_date: date) -> None:
        """将交易想法记录为信号版本，用于持久化存储和回放。

        P4-025: 信号输出持久化存储
        """
        for idea in ideas:
            # 构建信号 ID：idea_{idea_id}
            signal_id = f"idea_{idea.idea_id}"

            # 将 TradeIdea 映射为 Signal
            signal = Signal(
                signal_id=signal_id,
                symbol=idea.symbol,
                side=SignalSide.HOLD,  # TradeIdea 不区分买卖方向，统一为 HOLD
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
                },
            )

            # 构建上下文
            context = SignalContext(
                features_snapshot={},
                market_state={},
                rules_snapshot=[],
                timestamp=datetime.combine(as_of_date, datetime.min.time()),
            )

            # 记录信号版本
            self.signal_versioning.record(signal=signal, context=context)

        self.logger.info(f"Recorded {len(ideas)} ideas as signal versions")

    async def run_pre_market(self, *, as_of_date: date, force: bool = False) -> DailyReport:
        """Collect ideas and persist the daily pre-market report."""

        report_path = self._daily_report_path(as_of_date)
        if report_path.exists() and not force:
            payload = read_json(report_path)
            return DailyReport.model_validate(payload)

        ideas = []
        for trader_cfg in self.config.traders:
            trader = TraderAgent(
                trader=trader_cfg,
                memory_store=self.memory_store,
                trader_profile=self.trader_profiles.get(trader_cfg.trader_id),
            )
            trader_ideas = await trader.generate_trade_ideas(
                as_of_date=as_of_date,
                data_agent=self.data_agent,
            )
            ideas.extend(trader_ideas)

            # P4-024: 评估每个想法
            evaluated_signals = []
            for idea in trader_ideas:
                signal = await self.evaluate_signal(idea, {})
                if signal:
                    evaluated_signals.append(signal)

            # generate tasks for missing price data in watchlist
            missing_symbols = [s for s in trader_cfg.watchlist if s not in self.config.data.mock_prices]
            for s in missing_symbols:
                self._append_task(
                    AgentTask(
                        type="data_missing",
                        title=f"Missing mock price for {s}",
                        trader_id=trader_cfg.trader_id,
                        details={"symbol": s, "field": "last_price"},
                    )
                )

        report = DailyReport(
            as_of_date=as_of_date,
            ideas=ideas,
            highlights=[f"Generated {len(ideas)} trade ideas"],
        )

        # Optional: persona style routing (Phase 1 MVP)
        if self._persona_router and self.config.persona.clusters_path:
            clusters_path = self._resolve_path(self.config.persona.clusters_path)
            if clusters_path and clusters_path.exists():
                clusters_file = load_persona_clusters_file(clusters_path)
                market_state = self._load_market_state(as_of_date=as_of_date)
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
        self._record_ideas_as_signals(ideas=ideas, as_of_date=as_of_date)

        write_json(report_path, report.model_dump())
        return report

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

        # 2. 获取 AccountSnapshot（模拟）
        from src.risk.types import AccountSnapshot
        account = AccountSnapshot(
            account_id="default",
            timestamp=datetime.now(timezone.utc),
            net_value=100000.0,
            cash=50000.0,
            total_position_value=50000.0,
            positions=[],
            daily_pnl=0.0,
            total_pnl=0.0
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
            # 记录到 SignalVersioning
            context = SignalContext(
                features_snapshot={},
                market_state=market_data,
                rules_snapshot=[],
                timestamp=datetime.now(timezone.utc)
            )
            self.signal_versioning.record(signal=final_signal, context=context)

        return final_signal

    async def run_after_close(self, *, as_of_date: date, force: bool = False) -> EvaluationResult:
        """Evaluate ideas against the latest price context and emit tasks."""

        evaluation_path = self._evaluation_path(as_of_date)
        if evaluation_path.exists() and not force:
            payload = read_json(evaluation_path)
            return EvaluationResult.model_validate(payload)

        report_path = self._daily_report_path(as_of_date)
        if not report_path.exists():
            raise FileNotFoundError(
                f"Daily report not found for {as_of_date}. Run pre-market first: {report_path}"
            )

        daily_report = DailyReport.model_validate(read_json(report_path))

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

        for idea in daily_report.ideas:
            entry_price = idea.entry.price
            current_price = last_prices.get(idea.symbol)

            if entry_price is None or current_price is None:
                evaluations.append(
                    IdeaEvaluation(
                        idea_id=idea.idea_id,
                        symbol=idea.symbol,
                        entry_price=entry_price,
                        current_price=current_price,
                        status="not_evaluated",
                        notes=["Missing entry price or current price"],
                    )
                )
                if current_price is None:
                    self._append_task(
                        AgentTask(
                            type="data_missing",
                            title=f"Missing price for evaluation: {idea.symbol}",
                            trader_id=idea.trader_id,
                            idea_id=idea.idea_id,
                            details={"symbol": idea.symbol, "field": "last_price"},
                        )
                    )
                continue

            return_pct = (float(current_price) - float(entry_price)) / float(entry_price)
            evaluations.append(
                IdeaEvaluation(
                    idea_id=idea.idea_id,
                    symbol=idea.symbol,
                    entry_price=float(entry_price),
                    current_price=float(current_price),
                    return_pct=round(return_pct, 6),
                    status="ok",
                )
            )

            # trigger review tasks
            min_ret = float(self.config.evaluation.min_expected_return)
            memory_type = (
                TraderMemoryType.success_case
                if return_pct >= min_ret and return_pct >= 0
                else TraderMemoryType.failure_case
            )
            self.memory_store.append(
                TraderMemoryItem(
                    trader_id=idea.trader_id,
                    memory_type=memory_type,
                    as_of_date=as_of_date,
                    symbol=idea.symbol,
                    title=f"{idea.symbol} {memory_type.value.replace('_', ' ')}",
                    content=(
                        f"entry={float(entry_price):.4f}, current={float(current_price):.4f}, "
                        f"return_pct={round(return_pct, 6):.6f}, threshold={min_ret:.6f}"
                    ),
                    source="manager.run_after_close",
                    source_ref=str(idea.idea_id),
                    tags=["evaluation", memory_type.value],
                    importance=0.8 if memory_type == TraderMemoryType.success_case else 0.9,
                )
            )
            if (self.config.evaluation.loss_trigger and return_pct < 0) or (return_pct < min_ret):
                # 1. 先计算 trigger_reason（供后续使用）
                trigger_reason = ReviewTriggerReason.loss if return_pct < 0 else ReviewTriggerReason.below_expected

                # 2. 创建 memory，获取 memory_id
                memory = self._append_review_memory(
                    as_of_date=as_of_date,
                    idea=idea,
                    entry_price=float(entry_price),
                    current_price=float(current_price),
                    return_pct=return_pct,
                    threshold=min_ret,
                    trigger_reason=trigger_reason,
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

        summary = [
            f"Evaluated {len(evaluations)} ideas",
            f"Output dir: {self.output_dir}",
        ]

        result = EvaluationResult(as_of_date=as_of_date, evaluations=evaluations, summary=summary)
        write_json(evaluation_path, result.model_dump())
        return result
