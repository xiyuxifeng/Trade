from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

def test_run_backtest_passes_config_path_to_service(monkeypatch, capsys):
    """CLI 回测命令应把 config 路径传给 BacktestService。"""
    import cli.backtest as backtest_cli

    captured: dict[str, object] = {}

    class FakeService:
        def run_backtest(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                payload={
                    "result": {"records": []},
                }
            )

        def render_backtest_report(self, result, *, format: str):
            assert result == {"records": []}
            assert format == "markdown"
            return SimpleNamespace(payload={"content": "report"})

    monkeypatch.setattr(backtest_cli, "BacktestService", FakeService)

    backtest_cli.run_backtest(
        trader="trader_a",
        from_date="2026-04-01",
        to_date="2026-04-03",
        strategy_version_id=None,
        mode="full",
        output=None,
        config=Path("config/app.yaml"),
        format="markdown",
    )

    assert captured["config_path"] == Path("config/app.yaml")
    out = capsys.readouterr().out
    assert "report" in out
