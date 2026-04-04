from __future__ import annotations

from pathlib import Path

from src.common.config import load_app_config


def test_load_app_config_supports_crawl_sources_and_auth(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TGB_COOKIE", "cookie-value")
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
crawl:
  auth:
    tgb.cn:
      mode: cookie
      cookie: "${TGB_COOKIE}"
  throttling:
    min_interval_seconds: 1.0
    max_interval_seconds: 2.0
    backoff_seconds: [5, 15]
  sources:
    - source: tgb
      site: tgb.cn
      author_id: "10461311"
      author_name: "javxsp"
      list_url: "https://www.tgb.cn/user/blog/moreTopic?userID=10461311"
""",
        encoding="utf-8",
    )

    loaded = load_app_config(config_path)

    assert loaded.config.crawl.auth["tgb.cn"].cookie == "cookie-value"
    assert loaded.config.crawl.sources[0].author_name == "javxsp"
    assert loaded.config.crawl.throttling.backoff_seconds == [5, 15]


def test_load_app_config_defaults_empty_crawl_config(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")

    loaded = load_app_config(config_path)

    assert loaded.config.crawl.auth == {}
    assert loaded.config.crawl.sources == []
