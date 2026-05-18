from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from src.strategy.types import PriceSpec, Signal, SignalContext, SignalSide, SynthesisMode


@dataclass
class _FakeVersionedSignal:
	signal: Signal
	context: SignalContext


class _FakeVersioning:
	def __init__(self, versions: list[_FakeVersionedSignal]) -> None:
		self.versions = versions
		self.calls: list[tuple[str | None, datetime | None, int]] = []

	def list_versions(self, symbol=None, since=None, limit=100):
		self.calls.append((symbol, since, limit))
		return self.versions


def _write_basic_config(config_path: Path) -> None:
	config_path.parent.mkdir(parents=True, exist_ok=True)
	config_path.write_text(
		"""
timezone: Asia/Shanghai
storage:
  output_dir: data/processed/phase0
persona:
  clusters_path: data/processed/persona/clusters.sample.json
traders:
  - trader_id: trader_a
    display_name: Trader A
  - trader_id: trader_b
    display_name: Trader B
""",
		encoding="utf-8",
	)


def test_signal_service_list_signals(tmp_path: Path) -> None:
	"""SignalService 应支持信号版本列表查询。"""
	from src.services.signal_service import SignalService

	config_path = tmp_path / "config" / "app.yaml"
	_write_basic_config(config_path)

	signal = Signal(
		signal_id="idea_20260423_0001",
		symbol="000001.SZ",
		side=SignalSide.BUY,
		confidence=0.88,
		timestamp=datetime(2026, 4, 23, 9, 30, tzinfo=UTC),
		triggered_rules=["rule_a"],
		synthesis_mode=SynthesisMode.WEIGHTED_SCORE,
		entry_price=PriceSpec(type="limit", value=10.2),
		metadata={"trader_id": "trader_a"},
	)
	context = SignalContext(
		features_snapshot={"ma20": 10.0},
		market_state={"regime": "trend_up"},
		rules_snapshot=[{"rule_id": "rule_a"}],
		timestamp=datetime(2026, 4, 23, 9, 30, tzinfo=UTC),
	)
	service = SignalService(versioning=_FakeVersioning([_FakeVersionedSignal(signal=signal, context=context)]))

	result = service.list_signals(config_path=config_path, symbol="000001.SZ", since=date(2026, 4, 22), limit=20)

	assert result.status == "ok"
	assert result.payload["count"] == 1
	assert result.payload["signals"][0]["signal_id"] == "idea_20260423_0001"
	assert result.payload["signals"][0]["trader_id"] == "trader_a"


def test_persona_service_build_sample_clusters(tmp_path: Path) -> None:
	"""PersonaService 应支持生成样例 clusters 文件。"""
	from src.services.persona_service import PersonaService

	config_path = tmp_path / "config" / "app.yaml"
	_write_basic_config(config_path)

	service = PersonaService()
	result = service.build_sample_clusters(config_path=config_path)

	assert result.status == "ok"
	assert Path(result.payload["clusters_path"]).exists()
	assert result.payload["trader_count"] == 2
	assert result.payload["clusters_count"] == 6


def test_persona_service_build_market_state_from_csv(tmp_path: Path) -> None:
	"""PersonaService 应支持从 benchmark CSV 构建 MarketState。"""
	from src.services.persona_service import PersonaService

	config_path = tmp_path / "config" / "app.yaml"
	_write_basic_config(config_path)
	csv_path = tmp_path / "data" / "processed" / "market_data" / "510300_SH_daily.csv"
	csv_path.parent.mkdir(parents=True, exist_ok=True)
	rows = ["date,close"]
	start = date(2026, 2, 1)
	for i in range(80):
		rows.append(f"{(start + timedelta(days=i)).isoformat()},{3.0 + i * 0.02}")
	csv_path.write_text("\n".join(rows), encoding="utf-8")

	service = PersonaService()
	result = service.build_market_state(
		config_path=config_path,
		benchmark_symbol="510300.SH",
		as_of="2026-04-15",
		dest=tmp_path / "market_state.json",
	)

	assert result.status == "ok"
	assert result.payload["source"] == "cache"
	assert result.payload["benchmark_symbol"] == "510300.SH"
	assert Path(result.payload["market_state_path"]).exists()
	assert result.payload["market_state"]["as_of_date"] == "2026-04-15"
