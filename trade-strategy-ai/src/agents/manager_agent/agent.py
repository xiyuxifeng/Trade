"""ManagerAgent.

Phase 0 responsibilities:
- pre-market: collect trade ideas and write DailyReport
- after-close: evaluate ideas using DataAgent last_price and write EvaluationResult
- create AgentTask records when data is missing or trader review is required
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from src.agents.data_agent.agent import DataAgent
from src.agents.trader_agent.agent import TraderAgent
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


class ManagerAgent:
	def __init__(self, *, config: AppConfig, base_dir: Path) -> None:
		self.config = config
		self.base_dir = base_dir
		self.logger = get_logger("agent.manager")

		self.output_dir = ensure_dir(self.base_dir / self.config.storage.output_dir)
		self.tasks_path = self.output_dir / "agent_tasks.jsonl"

		self.data_agent = DataAgent(config=config)

		self._persona_router: PersonaRouter | None = None
		if getattr(self.config, "persona", None) is not None and self.config.persona.enable:
			self._persona_router = PersonaRouter(top_k=max(1, int(self.config.persona.top_k)))

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

	async def run_pre_market(self, *, as_of_date: date, force: bool = False) -> DailyReport:
		report_path = self._daily_report_path(as_of_date)
		if report_path.exists() and not force:
			payload = read_json(report_path)
			return DailyReport.model_validate(payload)

		ideas = []
		for trader_cfg in self.config.traders:
			trader = TraderAgent(trader=trader_cfg)
			trader_ideas = await trader.generate_trade_ideas(
				as_of_date=as_of_date,
				data_agent=self.data_agent,
			)
			ideas.extend(trader_ideas)

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
		write_json(report_path, report.model_dump())
		return report

	async def run_after_close(self, *, as_of_date: date, force: bool = False) -> EvaluationResult:
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
			if (self.config.evaluation.loss_trigger and return_pct < 0) or (return_pct < min_ret):
				self._append_task(
					AgentTask(
						type="trader_review",
						title=f"Trader review required: {idea.symbol}",
						trader_id=idea.trader_id,
						idea_id=idea.idea_id,
						details={
							"symbol": idea.symbol,
							"return_pct": round(return_pct, 6),
							"min_expected_return": min_ret,
						},
					)
				)

		summary = [
			f"Evaluated {len(evaluations)} ideas",
			f"Output dir: {self.output_dir}",
		]

		result = EvaluationResult(as_of_date=as_of_date, evaluations=evaluations, summary=summary)
		write_json(evaluation_path, result.model_dump())
		return result
