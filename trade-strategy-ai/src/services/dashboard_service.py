from __future__ import annotations

import asyncio
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable

from src.common.config import load_app_config
from src.common.paths import resolve_project_path
from src.pipeline.dashboard_models import DashboardReport
from src.pipeline.dashboard_renderers import CLIRenderer, HTMLRenderer
from src.services.base import BaseService, ServiceResult


def _to_plain(value: Any) -> Any:
	"""把 dataclass / 容器值转成可序列化结构。"""
	if hasattr(value, "model_dump"):
		return _to_plain(value.model_dump())
	if is_dataclass(value):
		return {k: _to_plain(v) for k, v in asdict(value).items()}
	if isinstance(value, dict):
		return {k: _to_plain(v) for k, v in value.items()}
	if isinstance(value, (list, tuple)):
		return [_to_plain(item) for item in value]
	if isinstance(value, Enum):
		return value.value
	if isinstance(value, (date, datetime)):
		return value.isoformat()
	if isinstance(value, Path):
		return str(value)
	return value


class DashboardService(BaseService):
	"""Dashboard 对外服务包装。"""

	service_name = "dashboard"
	_ALLOWED_MODES = {"cli", "html", "both"}

	def __init__(
		self,
		*,
		report_builder: Callable[[Any], Awaitable[DashboardReport]] | None = None,
		cli_renderer_factory: Callable[[], CLIRenderer] | None = None,
		html_renderer_factory: Callable[[Path, Path], HTMLRenderer] | None = None,
	) -> None:
		self._report_builder = report_builder
		self._cli_renderer_factory = cli_renderer_factory
		self._html_renderer_factory = html_renderer_factory

	async def _build_report(self, settings: Any) -> DashboardReport:
		"""构建 dashboard 报告。"""
		if self._report_builder is not None:
			return await self._report_builder(settings)

		from src.pipeline.dashboard import build_report as build_dashboard_report

		return await build_dashboard_report(settings)

	async def build_report(
		self,
		*,
		config_path: str | Path = Path("config/app.yaml"),
		mode: str = "cli",
		output: str | Path | None = None,
	) -> ServiceResult:
		"""构建并渲染 dashboard 报告。"""
		if mode not in self._ALLOWED_MODES:
			return ServiceResult(
				status="error",
				message=f"invalid mode: {mode}",
				payload={
					"config_path": str(Path(config_path).expanduser().resolve()),
					"mode": mode,
					"allowed_modes": sorted(self._ALLOWED_MODES),
				},
			)

		loaded = load_app_config(config_path)
		settings = loaded.config
		report = await self._build_report(settings)

		rendered_path: str | None = None
		if mode in ("cli", "both"):
			renderer = self._cli_renderer_factory() if self._cli_renderer_factory is not None else CLIRenderer()
			renderer.render(report)
		if mode in ("html", "both"):
			template_path = resolve_project_path("src/reporting/templates/dashboard.html")
			dest_path = resolve_project_path(output) if output is not None else resolve_project_path("data/processed/dashboard/dashboard.html")
			html_renderer = (
				self._html_renderer_factory(template_path, dest_path)
				if self._html_renderer_factory is not None
				else HTMLRenderer(template_path, dest_path)
			)
			rendered = html_renderer.render(report)
			rendered_path = str(rendered)

		critical_alerts = [event for event in report.alerts if getattr(event, "level", None) and event.level.value == "critical"]
		status = "partial" if critical_alerts else "ok"
		return ServiceResult(
			status=status,
			message="dashboard report built",
			payload={
				"config_path": str(loaded.config_path),
				"report": _to_plain(report),
				"html_path": rendered_path,
				"critical_alerts": len(critical_alerts),
				"exit_code": 1 if critical_alerts else 0,
			},
		)
