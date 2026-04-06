from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app


def test_import_trade_logs_cli_parses_and_stores(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")
    csv_path = tmp_path / "trades.csv"
    csv_path.write_text(
        "trader_id,symbol,side,executed_at,quantity,price,account_id\n"
        "trader_a,000001.SZ,buy,2026-04-06T09:35:00+08:00,100,10.5,acct-1\n",
        encoding="utf-8",
    )

    calls: dict[str, object] = {}

    def fake_import_trade_logs_from_csv(*, csv_path: Path, source: str, trader_account_map=None):
        calls["csv_path"] = csv_path
        calls["source"] = source
        calls["trader_account_map"] = trader_account_map
        return [], type("Stats", (), {"rows_seen": 1, "invalid": 0, "duplicates": 0, "issues": []})()

    async def fake_store_trade_logs(records):
        calls["stored"] = len(records)
        return len(records)

    monkeypatch.setattr("cli.main.import_trade_logs_from_csv", fake_import_trade_logs_from_csv)
    monkeypatch.setattr("cli.main.store_trade_logs", fake_store_trade_logs)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import-trade-logs",
            "--config",
            str(config_path),
            "--csv-path",
            str(csv_path),
            "--trader-account-map",
            '{"trader_a":"acct-1"}',
        ],
    )

    assert result.exit_code == 0
    assert calls["csv_path"] == csv_path
    assert calls["source"] == "csv_import"
    assert calls["trader_account_map"] == {"trader_a": "acct-1"}
    assert calls["stored"] == 0
    assert "Parsed trade logs" in result.output

