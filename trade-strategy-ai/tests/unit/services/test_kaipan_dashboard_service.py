from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.alerting.models import AlertEvent, AlertLevel
from src.pipeline.dashboard_models import DashboardReport


@dataclass
class _FakeProvider:
	calls: list[tuple[str, str, str]]

	def __getattr__(self, name: str):
		if name.startswith("fetch_"):
			def _method(*, trade_date, slot, **kwargs):
				self.calls.append((name, str(trade_date), slot))
				return {"name": name, "trade_date": str(trade_date), "slot": slot, "kwargs": kwargs}

			return _method
		raise AttributeError(name)


class _FakeNormalizer:
	DATASETS = (
		"hot_topics",
		"topic_constituents",
		"strong_symbols",
		"market_sentiment",
		"market_index",
		"sharp_withdrawal",
		"sector_ranking",
		"market_context",
		"market_stock_zd_num",
		"zhang_ting_expression",
		"daily_limit_index",
		"weight_performance",
		"get_feng_k_list",
	)

	def __init__(self) -> None:
		self.calls: list[tuple[str, tuple[str, ...]]] = []

	def normalize_date(
		self,
		trade_date: str,
		slots: tuple[str, ...] = ("09-25", "17-30"),
		progress_callback=None,
	) -> dict[str, dict[str, object]]:
		self.calls.append((trade_date, slots))
		results = {}
		for slot in slots:
			results[slot] = {}
			for dataset in self.DATASETS:
				results[slot][dataset] = {"slot": slot}
				if progress_callback is not None:
					progress_callback({"trade_date": trade_date, "slot": slot, "dataset": dataset, "status": "success"})
		return results


def _write_kaipan_config(config_path: Path) -> None:
	config_path.parent.mkdir(parents=True, exist_ok=True)
	config_path.write_text(
		"""
timezone: Asia/Shanghai
kaipan:
  data_dir: data/kaipan
  schema_dir: src/providers/kaipan_schema
  fetch_schedule:
    pre_market: "9:25"
    post_close: "17:30"
""",
		encoding="utf-8",
	)


def test_kaipan_service_fetch_normalize_status_and_run(tmp_path: Path) -> None:
	"""KaipanService 应支持 fetch / normalize / status / run。"""
	from src.services.kaipan_service import KaipanService

	config_path = tmp_path / "config" / "app.yaml"
	_write_kaipan_config(config_path)
	provider = _FakeProvider(calls=[])
	normalizer = _FakeNormalizer()
	service = KaipanService(
		provider_factory=lambda **kwargs: provider,
		normalizer_factory=lambda **kwargs: normalizer,
	)

	fetch_result = service.fetch(config_path=config_path, trade_date="2026-04-23", slot="09-25")
	normalize_result = service.normalize(config_path=config_path, trade_date="2026-04-23", slot="17-30")
	status_result = service.status(config_path=config_path)
	run_plan = service.run(config_path=config_path)

	assert fetch_result.status == "ok"
	assert "normalize_results" in fetch_result.payload
	assert len(fetch_result.payload["slot_results"]["09-25"]["success"]) == 12
	assert normalizer.calls[0] == ("2026-04-23", ("09-25",))
	assert normalize_result.payload["slots"] == ["17-30"]
	assert status_result.status == "partial"
	assert status_result.payload["scheduler_started"] is False
	assert run_plan.payload["pre_market"] == "9:25"
	assert run_plan.payload["post_close"] == "17:30"
	assert run_plan.payload["scheduler_started"] is False


def test_kaipan_service_supports_date_range_progress(tmp_path: Path) -> None:
	"""KaipanService 应按交易日期范围输出进度回调。"""
	from src.services.kaipan_service import KaipanService

	config_path = tmp_path / "config" / "app.yaml"
	_write_kaipan_config(config_path)
	provider = _FakeProvider(calls=[])
	normalizer = _FakeNormalizer()
	service = KaipanService(
		provider_factory=lambda **kwargs: provider,
		normalizer_factory=lambda **kwargs: normalizer,
	)

	fetch_progress: list[dict[str, object]] = []
	normalize_progress: list[dict[str, object]] = []
	fetch_result = service.fetch(
		config_path=config_path,
		start_date="2026-04-23",
		end_date="2026-04-24",
		slot="09-25",
		progress_callback=fetch_progress.append,
	)
	normalize_result = service.normalize(
		config_path=config_path,
		start_date="2026-04-23",
		end_date="2026-04-24",
		slot="09-25",
		progress_callback=normalize_progress.append,
	)

	assert fetch_result.status == "ok"
	assert fetch_result.payload["trade_dates"] == ["2026-04-23", "2026-04-24"]
	assert fetch_result.payload["date_results"]["2026-04-23"]["slot_results"]["09-25"]["fetchers"][0] == "market_sentiment"
	assert fetch_progress[0]["current_trade_date"] == "2026-04-23"
	assert fetch_progress[-1]["current"] == fetch_progress[-1]["total"]
	assert normalize_result.status == "ok"
	assert normalize_result.payload["trade_dates"] == ["2026-04-23", "2026-04-24"]
	assert normalize_result.payload["date_results"]["2026-04-23"]["09-25"]["hot_topics"]["slot"] == "09-25"
	assert normalize_progress[0]["stage"] == "normalize"
	assert normalize_progress[-1]["current"] == normalize_progress[-1]["total"]


def test_kaipan_service_fetch_includes_10_5_capabilities(tmp_path: Path) -> None:
	"""KaipanService 收盘抓取应包含 10.5 新接口。"""
	from src.services.kaipan_service import KaipanService

	config_path = tmp_path / "config" / "app.yaml"
	_write_kaipan_config(config_path)
	provider = _FakeProvider(calls=[])
	normalizer = _FakeNormalizer()
	service = KaipanService(
		provider_factory=lambda **kwargs: provider,
		normalizer_factory=lambda **kwargs: normalizer,
	)

	result = service.fetch(config_path=config_path, trade_date="2026-04-23", slot="17-30")

	assert result.status == "ok"
	assert len(result.payload["slot_results"]["17-30"]["success"]) == 19
	assert "market_stock_zd_num" in result.payload["slot_results"]["17-30"]["success"]
	assert "zhang_ting_expression" in result.payload["slot_results"]["17-30"]["success"]
	assert "daily_limit_index" in result.payload["slot_results"]["17-30"]["success"]
	assert "weight_performance" in result.payload["slot_results"]["17-30"]["success"]
	assert "strong_fengkou_best" in result.payload["slot_results"]["17-30"]["success"]


def test_kaipan_service_rejects_invalid_slot(tmp_path: Path) -> None:
	"""KaipanService 应拒绝非法 slot。"""
	from src.services.kaipan_service import KaipanService

	config_path = tmp_path / "config" / "app.yaml"
	_write_kaipan_config(config_path)
	service = KaipanService(
		provider_factory=lambda **kwargs: _FakeProvider(calls=[]),
		normalizer_factory=lambda **kwargs: _FakeNormalizer(),
	)

	result = service.fetch(config_path=config_path, trade_date="2026-04-23", slot="bad-slot")

	assert result.status == "error"
	assert "invalid slot" in (result.message or "")


def test_kaipan_service_status_uses_latest_trade_date_and_slot(tmp_path: Path) -> None:
	"""KaipanService.status 应按交易日与 slot 选最新记录。"""
	from src.services.kaipan_service import KaipanService

	config_path = tmp_path / "config" / "app.yaml"
	_write_kaipan_config(config_path)
	raw_base = tmp_path / "data" / "kaipan" / "raw"
	(raw_base / "hot_topics" / "2026-04-23_09-25").mkdir(parents=True, exist_ok=True)
	(raw_base / "hot_topics" / "2026-04-23_09-25" / "a.json").write_text("{}", encoding="utf-8")
	(raw_base / "strong_symbols" / "2026-04-24_17-30").mkdir(parents=True, exist_ok=True)
	(raw_base / "strong_symbols" / "2026-04-24_17-30" / "b.json").write_text("{}", encoding="utf-8")

	service = KaipanService(
		provider_factory=lambda **kwargs: _FakeProvider(calls=[]),
		normalizer_factory=lambda **kwargs: _FakeNormalizer(),
	)
	result = service.status(config_path=config_path)

	assert result.status == "ok"
	assert result.payload["latest_slot"] == "2026-04-24_17-30"


def test_kaipan_service_can_start_and_stop_scheduler(tmp_path: Path, monkeypatch) -> None:
	"""KaipanService 应能启动并停止 scheduler。"""
	from src.services import kaipan_service as kaipan_service_module

	config_path = tmp_path / "config" / "app.yaml"
	_write_kaipan_config(config_path)

	class _FakeThread:
		def join(self) -> None:
			return None

	class _FakeScheduler:
		def __init__(self) -> None:
			self.running = False
			self._thread = _FakeThread()
			self.jobs: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

		def add_job(self, *args, **kwargs) -> None:
			self.jobs.append((args, kwargs))

		def start(self) -> None:
			self.running = True

		def shutdown(self, wait: bool = False) -> None:
			del wait
			self.running = False

	service = kaipan_service_module.KaipanService(
		provider_factory=lambda **kwargs: _FakeProvider(calls=[]),
		normalizer_factory=lambda **kwargs: _FakeNormalizer(),
	)
	monkeypatch.setattr(kaipan_service_module, "BackgroundScheduler", _FakeScheduler)

	run_result = service.run(config_path=config_path, start_scheduler=True)
	status_running = service.status(config_path=config_path)
	stop_result = service.stop(config_path=config_path)
	status_stopped = service.status(config_path=config_path)

	assert run_result.status == "ok"
	assert run_result.payload["started"] is True
	assert status_running.payload["scheduler_started"] is True
	assert stop_result.status == "ok"
	assert stop_result.payload["started"] is False
	assert status_stopped.payload["scheduler_started"] is False


def test_dashboard_service_build_report(tmp_path: Path) -> None:
    """DashboardService 应支持构建与渲染报告。"""
    from src.common.paths import project_root
    from src.services.dashboard_service import DashboardService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    async def _build_report(_settings):
        return DashboardReport(
            alerts=[
                AlertEvent(level=AlertLevel.CRITICAL, title="critical", message="critical alert"),
            ],
            generated_at=datetime.now(UTC),
        )

    class _FakeCliRenderer:
        def __init__(self) -> None:
            self.rendered = False

        def render(self, report):
            self.rendered = True

    class _FakeHtmlRenderer:
        def __init__(self, template_path: Path, output: Path) -> None:
            self.template_path = template_path
            self.output = output

        def render(self, report):
            return self.output

    service = DashboardService(
        report_builder=_build_report,
        cli_renderer_factory=_FakeCliRenderer,
        html_renderer_factory=lambda template_path, output: _FakeHtmlRenderer(template_path, output),
    )
    result = __import__("asyncio").run(
        service.build_report(config_path=config_path, mode="both", output="dashboard.html")
    )

    assert result.status == "partial"
    assert result.payload["critical_alerts"] == 1
    assert result.payload["exit_code"] == 1
    assert Path(result.payload["html_path"]) == project_root() / "dashboard.html"


def test_dashboard_service_rejects_invalid_mode(tmp_path: Path) -> None:
	"""DashboardService 应拒绝非法 mode。"""
	from src.services.dashboard_service import DashboardService

	config_path = tmp_path / "config" / "app.yaml"
	config_path.parent.mkdir(parents=True, exist_ok=True)
	config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

	async def _noop_report_builder(_settings):
		return DashboardReport()

	service = DashboardService(report_builder=_noop_report_builder)
	result = __import__("asyncio").run(
		service.build_report(config_path=config_path, mode="invalid")
	)

	assert result.status == "error"
	assert result.payload["mode"] == "invalid"
