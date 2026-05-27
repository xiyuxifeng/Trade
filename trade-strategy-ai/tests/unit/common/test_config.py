from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from cli.main import _DEFAULT_CONFIG_YAML
from src.common.config import ConfigError
from src.common.config import load_app_config
from src.common.paths import project_root


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


def test_load_app_config_rejects_deprecated_config_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
stage4:
  enable: true
  allow_phase0_fallback: true
traders:
  - trader_id: trader_a
    display_name: Trader A
    watchlist: ["000001.SZ"]
        """,
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="Deprecated config keys found"):
        load_app_config(config_path)


def test_load_app_config_resolves_project_relative_config_path() -> None:
    """相对 config/app.yaml 应解析到 trade-strategy-ai 项目根目录。"""
    loaded = load_app_config("config/app.yaml")

    assert loaded.config_path == project_root() / "config" / "app.yaml"


def test_init_config_template_exposes_required_top_level_sections() -> None:
    template = yaml.safe_load(_DEFAULT_CONFIG_YAML.replace("\t", "  "))

    assert sorted(template.keys()) == [
        "api",
        "crawl",
        "data",
        "database",
        "evaluation",
        "kaipan",
        "llm",
        "run_mode",
        "schedule",
        "storage",
        "timezone",
        "traders",
    ]
    assert sorted(template["data"].keys()) == ["market_universe_snapshot_dir", "providers"]
    assert sorted(template["crawl"].keys()) == ["auth", "sources", "throttling"]
    assert sorted(template["api"].keys()) == ["auth", "host", "port", "timeout_seconds"]
    assert template["api"]["auth"]["api_keys"][0]["key"] == "trade-strategy-ai-local-viewer"
    assert template["api"]["auth"]["api_keys"][0]["role"] == "viewer"
    assert template["api"]["auth"]["api_keys"][-1]["role"] == "admin"
    assert "token" in template["kaipan"]
    assert "user_id" in template["kaipan"]
    assert "market_state_benchmark_symbol" not in template
