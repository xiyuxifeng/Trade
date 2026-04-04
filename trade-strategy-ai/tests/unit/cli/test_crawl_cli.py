from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app


def test_crawl_command_runs_for_multiple_sources(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
crawl:
  auth:
    tgb.cn:
      mode: cookie
      cookie: "cookie-value"
  sources:
    - source: tgb
      site: tgb.cn
      author_id: "10461311"
      author_name: "javxsp"
      list_url: "https://www.tgb.cn/user/blog/moreTopic?userID=10461311"
    - source: tgb
      site: tgb.cn
      author_id: "10461312"
      author_name: "javxsp2"
      list_url: "https://www.tgb.cn/user/blog/moreTopic?userID=10461312"
""",
        encoding="utf-8",
    )

    calls: list[str] = []

    def fake_run_crawl(*, config_path: Path, max_articles: int | None = None) -> list[str]:
        del max_articles
        calls.append(str(config_path))
        return ["tgb:10461311", "tgb:10461312"]

    monkeypatch.setattr("cli.main.run_crawl_command", fake_run_crawl)

    runner = CliRunner()
    result = runner.invoke(app, ["crawl", "--config", str(config_path)])

    assert result.exit_code == 0
    assert calls == [str(config_path)]
    assert "tgb:10461311" in result.output
    assert "tgb:10461312" in result.output
