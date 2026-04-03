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

	def _daily_report_path(self, as_of_date: date) -> Path:
		return self.output_dir / f"daily_report_{as_of_date.isoformat()}.json"

	def _evaluation_path(self, as_of_date: date) -> Path:
		return self.output_dir / f"evaluation_{as_of_date.isoformat()}.json"

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
