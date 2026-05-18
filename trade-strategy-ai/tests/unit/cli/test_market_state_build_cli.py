from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app


def test_market_state_build_uses_market_data_cache(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
data:
  market_data_cache_dir: "data/processed/market_data"
""",
        encoding="utf-8",
    )

    cache_dir = tmp_path / "data" / "processed" / "market_data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "000300_SH_daily.csv"
    rows = ["date,close"]
    start = date(2026, 2, 1)
    for i in range(40):
        rows.append(f"{(start + timedelta(days=i)).isoformat()},{3.0 + i * 0.01}")
    cache_path.write_text("\n".join(rows), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "market-state-build",
            "--config",
            str(config_path),
            "--benchmark-symbol",
            "000300.SH",
            "--dest",
            str(tmp_path / "market_state.json"),
            "--as-of",
            "2026-03-15",
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "market_state.json").exists()
    assert "Wrote MarketState" in result.output
