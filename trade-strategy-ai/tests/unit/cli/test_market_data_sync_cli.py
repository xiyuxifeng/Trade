from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app


def test_market_data_sync_cli_uses_config_benchmark_symbol(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
persona:
  market_state_benchmark_symbol: "510300.SH"
data:
  market_data_cache_dir: "data/processed/market_data"
""",
        encoding="utf-8",
    )

    calls: dict[str, object] = {}

    class _FakeResult:
        symbol = "510300.SH"
        cache_path = tmp_path / "market" / "510300_SH_daily.csv"
        rows_written = 2
        latest_close = 3.5

    class _FakeService:
        def __init__(self, *, cache_dir: Path, tool=None) -> None:
            calls["cache_dir"] = cache_dir
            calls["tool"] = tool

        def sync_symbols(self, *, symbols, start_date=None, end_date=None, adjust=""):
            del start_date, end_date, adjust
            calls["symbols"] = symbols
            return [_FakeResult()]

    monkeypatch.setattr("cli.main.MarketDataSyncService", _FakeService)

    runner = CliRunner()
    result = runner.invoke(app, ["market-data-sync", "--config", str(config_path)])

    assert result.exit_code == 0
    assert calls["symbols"] == ["510300.SH"]
    assert "510300.SH" in result.output


def test_market_data_sync_cli_accepts_index_and_board_symbols(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
data:
  market_data_cache_dir: "data/processed/market_data"
""",
        encoding="utf-8",
    )

    calls: dict[str, list[str]] = {"index": [], "industry": [], "concept": []}

    class _FakeService:
        def __init__(self, *, cache_dir: Path, tool=None) -> None:
            del cache_dir, tool

        def sync_index(self, symbol: str, start_date=None, end_date=None):
            del start_date, end_date
            calls["index"].append(symbol)
            return type("Result", (), {"symbol": symbol, "rows_written": 2, "latest_close": 3000.0, "cache_path": tmp_path / "index.csv"})()

        def sync_industry_board(self, symbol: str, start_date=None, end_date=None):
            del start_date, end_date
            calls["industry"].append(symbol)
            return type("Result", (), {"symbol": symbol, "rows_written": 2, "latest_close": 1000.0, "cache_path": tmp_path / "industry.csv"})()

        def sync_concept_board(self, symbol: str, start_date=None, end_date=None):
            del start_date, end_date
            calls["concept"].append(symbol)
            return type("Result", (), {"symbol": symbol, "rows_written": 2, "latest_close": 2000.0, "cache_path": tmp_path / "concept.csv"})()

        def sync_symbols(self, *, symbols, start_date=None, end_date=None, adjust=""):
            del symbols, start_date, end_date, adjust
            return []

    monkeypatch.setattr("cli.main.MarketDataSyncService", _FakeService)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "market-data-sync",
            "--config",
            str(config_path),
            "--index-symbol",
            "sz399001",
            "--industry-board",
            "半导体",
            "--concept-board",
            "人工智能",
        ],
    )

    assert result.exit_code == 0
    assert calls["index"] == ["sz399001"]
    assert calls["industry"] == ["半导体"]
    assert calls["concept"] == ["人工智能"]
