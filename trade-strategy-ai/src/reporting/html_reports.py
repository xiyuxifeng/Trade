from __future__ import annotations

from html import escape
from pathlib import Path

from src.schemas.contracts import DailyReport, EvaluationResult


def _fmt_float(value: float | None, *, digits: int = 4) -> str:
	if value is None:
		return "-"
	return f"{float(value):.{digits}f}"


def _fmt_pct(value: float | None, *, digits: int = 2) -> str:
	if value is None:
		return "-"
	return f"{float(value) * 100:.{digits}f}%"


def _ul(items: list[str]) -> str:
	if not items:
		return "<p>-</p>"
	return "<ul>" + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>"


def _render(template_text: str, context: dict[str, str]) -> str:
	out = template_text
	for key, value in context.items():
		out = out.replace(f"{{{{{key}}}}}", value)
	return out


def _load_template(*, templates_dir: Path, filename: str) -> str:
	path = templates_dir / filename
	return path.read_text(encoding="utf-8")


def render_daily_report_html(*, report: DailyReport, templates_dir: Path) -> str:
	ideas_rows: list[str] = []
	for idea in report.ideas:
		ideas_rows.append(
			"<tr>"
			+ f"<td>{escape(idea.trader_id)}</td>"
			+ f"<td>{escape(idea.symbol)}</td>"
			+ f"<td>{escape(idea.side)}</td>"
			+ f"<td>{escape(idea.entry.type)}</td>"
			+ f"<td>{escape(_fmt_float(idea.entry.price))}</td>"
			+ f"<td>{escape(_fmt_float(idea.target_price))}</td>"
			+ f"<td>{escape(_fmt_float(idea.stop_loss_price))}</td>"
			+ f"<td>{escape(_fmt_float(idea.position_size, digits=3))}</td>"
			+ f"<td>{escape(_fmt_float(idea.confidence, digits=3))}</td>"
			+ f"<td>{escape(idea.rationale or '-') }</td>"
			+ f"<td>{escape(idea.invalidation or '-') }</td>"
			+ "</tr>"
		)

	template_text = _load_template(templates_dir=templates_dir, filename="daily_report.html")
	return _render(
		template_text,
		{
			"as_of_date": escape(report.as_of_date.isoformat()),
			"generated_at": escape(report.generated_at.isoformat()),
			"highlights": _ul(report.highlights),
			"risks": _ul(report.risks),
			"ideas_rows": "\n".join(ideas_rows) if ideas_rows else "",
		},
	)


def render_evaluation_html(*, result: EvaluationResult, templates_dir: Path) -> str:
	rows: list[str] = []
	for ev in result.evaluations:
		notes = "<br/>".join(escape(n) for n in (ev.notes or [])) or "-"
		rows.append(
			"<tr>"
			+ f"<td>{escape(ev.symbol)}</td>"
			+ f"<td>{escape(_fmt_float(ev.entry_price))}</td>"
			+ f"<td>{escape(_fmt_float(ev.current_price))}</td>"
			+ f"<td>{escape(_fmt_pct(ev.return_pct))}</td>"
			+ f"<td>{escape(ev.status)}</td>"
			+ f"<td>{notes}</td>"
			+ "</tr>"
		)

	template_text = _load_template(templates_dir=templates_dir, filename="evaluation.html")
	return _render(
		template_text,
		{
			"as_of_date": escape(result.as_of_date.isoformat()),
			"generated_at": escape(result.generated_at.isoformat()),
			"summary": _ul(result.summary),
			"rows": "\n".join(rows) if rows else "",
		},
	)


def write_daily_report_html(*, report: DailyReport, templates_dir: Path, dest_path: Path) -> None:
	dest_path.parent.mkdir(parents=True, exist_ok=True)
	html = render_daily_report_html(report=report, templates_dir=templates_dir)
	dest_path.write_text(html, encoding="utf-8")


def write_evaluation_html(*, result: EvaluationResult, templates_dir: Path, dest_path: Path) -> None:
	dest_path.parent.mkdir(parents=True, exist_ok=True)
	html = render_evaluation_html(result=result, templates_dir=templates_dir)
	dest_path.write_text(html, encoding="utf-8")
