from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from src.strategy.signal_version import SignalVersioning
from src.strategy.types import PriceSpec, Signal, SignalContext, SignalSide, SynthesisMode


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
""",
		encoding="utf-8",
	)


def test_list_signals_cli_lists_recorded_signal(tmp_path: Path) -> None:
	config_path = tmp_path / "config" / "app.yaml"
	_write_basic_config(config_path)

	versioning = SignalVersioning(storage_path=tmp_path / "data" / "processed" / "phase0" / "signals")
	versioning.record(
		Signal(
			signal_id="idea_20260423_0001",
			symbol="000001.SZ",
			side=SignalSide.BUY,
			confidence=0.88,
			timestamp=datetime(2026, 4, 23, 9, 30, tzinfo=UTC),
			triggered_rules=["rule_a"],
			synthesis_mode=SynthesisMode.WEIGHTED_SCORE,
			entry_price=PriceSpec(type="limit", value=10.2),
			metadata={"trader_id": "trader_a"},
		),
		SignalContext(
			features_snapshot={"ma20": 10.0},
			market_state={"regime": "trend_up"},
			rules_snapshot=[{"rule_id": "rule_a"}],
			timestamp=datetime(2026, 4, 23, 9, 30, tzinfo=UTC),
		),
	)

	runner = CliRunner()
	result = runner.invoke(
		app,
		[
			"list-signals",
			"--config",
			str(config_path),
			"--symbol",
			"000001.SZ",
			"--since",
			"2026-04-22",
		],
	)

	assert result.exit_code == 0
	assert "Found 1 signal(s):" in result.output
	assert "idea_20260423_0001" in result.output


def test_persona_init_sample_cli_writes_clusters(tmp_path: Path) -> None:
	config_path = tmp_path / "config" / "app.yaml"
	_write_basic_config(config_path)

	runner = CliRunner()
	result = runner.invoke(
		app,
		[
			"persona-init-sample",
			"--config",
			str(config_path),
			"--dest",
			str(tmp_path / "clusters.sample.json"),
		],
	)

	assert result.exit_code == 0
	assert (tmp_path / "clusters.sample.json").exists()
	assert "Wrote sample clusters:" in result.output
