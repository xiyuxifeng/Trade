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
      trader_id: trader_a
      author_id: "10461311"
      author_name: "javxsp"
      list_url: "https://www.tgb.cn/user/blog/moreTopic?userID=10461311"
      render_js: true
""",
        encoding="utf-8",
    )

    loaded = load_app_config(config_path)

    assert loaded.config.crawl.auth["tgb.cn"].cookie == "cookie-value"
    assert loaded.config.crawl.sources[0].trader_id == "trader_a"
    assert loaded.config.crawl.sources[0].author_name == "javxsp"
    assert loaded.config.crawl.sources[0].render_js is True
    assert loaded.config.crawl.throttling.backoff_seconds == [5, 15]


def test_load_app_config_defaults_empty_crawl_config(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")

    loaded = load_app_config(config_path)

    assert loaded.config.crawl.auth == {}
    assert loaded.config.crawl.sources == []


def test_load_app_config_supports_kaipan_runtime_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
kaipan:
  data_dir: data/kaipan
  schema_dir: src/providers/kaipan_schema
  token: test-token
  user_id: "3807176"
  default_headers:
    Content-Type: application/x-www-form-urlencoded; charset=UTF-8
    User-Agent: Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)
    Connection: Keep-Alive
    Accept-Encoding: gzip
  fetch_schedule:
    pre_market: "9:25"
    post_close: "17:30"
  trading_calendar:
    source: akshare
  min_request_interval_seconds: 0.8
  max_retries: 3
  retry_backoff_seconds: [1.0, 2.0, 4.0]
  retry_status_codes: [403, 429, 500, 502, 503, 504]
""",
        encoding="utf-8",
    )

    loaded = load_app_config(config_path)

    kaipan = loaded.config.kaipan
    assert kaipan.data_dir == "data/kaipan"
    assert kaipan.schema_dir == "src/providers/kaipan_schema"
    assert kaipan.token == "test-token"
    assert kaipan.user_id == "3807176"
    assert kaipan.default_headers["Connection"] == "Keep-Alive"
    assert kaipan.min_request_interval_seconds == 0.8
    assert kaipan.max_retries == 3
    assert kaipan.retry_backoff_seconds == [1.0, 2.0, 4.0]
    assert kaipan.retry_status_codes == [403, 429, 500, 502, 503, 504]
