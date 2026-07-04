from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app


def _write_basic_config(config_path: Path) -> None:
	config_path.parent.mkdir(parents=True, exist_ok=True)
	config_path.write_text(
		"""
timezone: Asia/Shanghai
runtime:
  output_dir: data/processed/phase0
persona:
  clusters_path: data/processed/persona/clusters.sample.json
traders:
  - trader_id: trader_a
    display_name: Trader A
""",
		encoding="utf-8",
	)

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
