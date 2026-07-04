from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace


def test_config_service_writes_default_template(tmp_path: Path) -> None:
    """ConfigService 应能生成默认配置模板。"""
    from src.services.config_service import ConfigService

    dest = tmp_path / "config" / "app.yaml"
    service = ConfigService()

    result = service.write_default_template(dest)

    assert result.status == "ok"
    assert dest.exists()
    assert "database:" in dest.read_text(encoding="utf-8")


@dataclass
class _FakeSeedStats:
    article_jsonl_paths: list[str]
    trade_log_paths: list[str]
    articles_inserted: int = 1
    articles_updated: int = 2
    trade_logs_imported: int = 3


def test_setup_service_seed_and_init_project(tmp_path: Path) -> None:
    """SetupService 应能封装 seed-data 和 init-project。"""
    from src.common.config import AppConfig, DataConfig, RuntimeConfig
    from src.services.setup_service import SetupService

    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")

    calls: dict[str, object] = {}

    async def fake_seed_project_data(*, config, base_dir: Path, article_jsonl_paths=None, trade_log_paths=None):
        del config, article_jsonl_paths, trade_log_paths
        calls.setdefault("seed_base_dirs", []).append(base_dir)
        return _FakeSeedStats(article_jsonl_paths=["a.jsonl"], trade_log_paths=["b.csv"])

    def fake_init_db(*, project_root: Path) -> None:
        calls["init_db"] = project_root

    loaded_config = AppConfig(runtime=RuntimeConfig(output_dir="data/processed/phase0"), data=DataConfig())

    service = SetupService(
        seed_runner=fake_seed_project_data,
        init_db_runner=fake_init_db,
        load_config_runner=lambda path: SimpleNamespace(config=loaded_config, config_path=Path(path)),
    )

    seed_result = asyncio.run(service.seed_data(config_path=config_path))
    init_result = asyncio.run(service.init_project(config_path=config_path))

    assert seed_result.status == "ok"
    assert seed_result.payload["stats"]["articles_inserted"] == 1
    assert init_result.status == "ok"
    assert calls["init_db"] == tmp_path
    assert calls["seed_base_dirs"] == [tmp_path, tmp_path]


def test_setup_service_import_logs_and_migrate_crawl_state(tmp_path: Path) -> None:
    """SetupService 应能封装交易导入与爬虫状态迁移。"""
    from src.services.setup_service import SetupService

    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")
    csv_path = tmp_path / "trades.csv"
    csv_path.write_text("trader_id,symbol\n", encoding="utf-8")
    state_root = tmp_path / "data" / "processed" / "crawl" / "tgb" / "10461311"
    state_root.mkdir(parents=True, exist_ok=True)
    (state_root / "state.json").write_text(
        json.dumps(
            {
                "seen_urls": ["u1", "u2"],
                "seen_hashes": ["h1"],
                "last_seen_article_url": "https://example.com/a",
                "last_seen_published_at": "2026-04-01T10:00:00",
                "last_success_article_count": 4,
            }
        ),
        encoding="utf-8",
    )

    @dataclass
    class _FakeSource:
        source: str
        author_id: str
        enabled: bool = True

    loaded_config = SimpleNamespace(
        crawl=SimpleNamespace(sources=[_FakeSource(source="tgb", author_id="10461311")]),
    )

    calls: dict[str, object] = {}

    def fake_load_config(path):
        calls["load_config"] = Path(path)
        return SimpleNamespace(config=loaded_config, config_path=Path(path))

    def fake_csv_importer(*, csv_path: Path, source: str, trader_account_map=None):
        calls["csv_import"] = (csv_path, source, trader_account_map)
        issue = SimpleNamespace(severity=SimpleNamespace(value="warning"), code="W1", message="warn")
        return ([{"row": 1}], SimpleNamespace(rows_seen=2, invalid=0, duplicates=0, issues=[issue]))

    async def fake_store_trade_logs(records):
        calls["stored"] = len(records)
        return len(records)

    async def fake_crawl_state_writer(*, source: str, author_id: str, state_data: dict, base_dir: Path):
        calls.setdefault("crawl_state", []).append((source, author_id, state_data["seen_urls"], base_dir))
        return True

    service = SetupService(
        load_config_runner=fake_load_config,
        csv_importer=fake_csv_importer,
        store_trade_logs_runner=fake_store_trade_logs,
        crawl_state_writer=fake_crawl_state_writer,
    )

    import_result = asyncio.run(
        service.import_trade_logs(
            config_path=config_path,
            csv_path=csv_path,
            source="csv_import",
            trader_account_map={"trader_a": "acct-1"},
            dry_run=False,
        )
    )
    migrate_result = asyncio.run(service.migrate_crawl_state(config_path=config_path))

    assert import_result.status == "ok"
    assert import_result.payload["stored_count"] == 1
    assert calls["csv_import"][0] == csv_path
    assert calls["stored"] == 1
    assert migrate_result.status == "ok"
    assert migrate_result.payload["migrated"] == 1
    assert calls["crawl_state"][0][0] == "tgb"
