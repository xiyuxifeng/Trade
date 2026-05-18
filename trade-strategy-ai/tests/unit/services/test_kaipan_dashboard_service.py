from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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
	def __init__(self) -> None:
		self.calls: list[tuple[str, tuple[str, ...]]] = []

	def normalize_date(self, trade_date: str, slots: tuple[str, ...] = ("09-25", "17-30")) -> dict[str, dict[str, object]]:
		self.calls.append((trade_date, slots))
		return {slot: {"hot_topics": {"slot": slot}} for slot in slots}


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
	assert run_plan.payload["pre_market"] == "9:25"
	assert run_plan.payload["post_close"] == "17:30"


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
	assert len(result.payload["slot_results"]["17-30"]["success"]) == 15
	assert "market_stock_zd_num" in result.payload["slot_results"]["17-30"]["success"]
	assert "zhang_ting_expression" in result.payload["slot_results"]["17-30"]["success"]
	assert "daily_limit_index" in result.payload["slot_results"]["17-30"]["success"]
	assert "weight_performance" in result.payload["slot_results"]["17-30"]["success"]
	assert "get_feng_k_list" in result.payload["slot_results"]["17-30"]["success"]


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
