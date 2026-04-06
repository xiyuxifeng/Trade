from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from scripts.seed_data import seed_project_data
from types import SimpleNamespace
from unittest.mock import AsyncMock
from src.common.config import AppConfig, CrawlConfig, CrawlSourceConfig, DataConfig, StorageConfig, TradeLogSourceConfig, TraderConfig


class _FakeArticleStats:
    read_records = 2
    inserted_articles = 1
    updated_articles = 1
    skipped_duplicates = 0
    generated_tasks = 1


class _FakeTradeStats:
    rows_seen = 3


@pytest.mark.asyncio
async def test_seed_project_data_discovers_articles_and_trade_logs(tmp_path: Path, monkeypatch) -> None:
    crawl_dir = tmp_path / "data" / "processed" / "crawl" / "tgb" / "10461311"
    crawl_dir.mkdir(parents=True, exist_ok=True)
    (crawl_dir / "articles.jsonl").write_text("{}", encoding="utf-8")

    trade_path = tmp_path / "data" / "trades.csv"
    trade_path.parent.mkdir(parents=True, exist_ok=True)
    trade_path.write_text("symbol,side,executed_at,quantity,price,account_id\n", encoding="utf-8")

    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(),
        crawl=CrawlConfig(
            sources=[
                CrawlSourceConfig(
                    source="tgb",
                    site="tgb.cn",
                    trader_id="trader_a",
                    author_id="10461311",
                    author_name="Author A",
                    list_url="https://example.com",
                )
            ]
        ),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                trade_log_sources=TradeLogSourceConfig(csv_paths=["data/trades.csv"]),
            )
        ],
    )

    calls: dict[str, object] = {}

    async def _fake_store_articles_jsonl_to_db(*, base_dir: Path, jsonl_paths: list[Path], pending_tasks_path=None, limit=None):
        del base_dir, pending_tasks_path, limit
        calls["article_paths"] = jsonl_paths
        return _FakeArticleStats()

    def _fake_import_trade_logs_from_csv(*, csv_path: Path, source: str = "csv_import", market: str = "CN", currency: str = "CNY", trader_account_map=None):
        del source, market, currency, trader_account_map
        calls.setdefault("trade_paths", []).append(csv_path)
        return ([object(), object()], _FakeTradeStats())

    async def _fake_store_trade_logs(trades):
        calls["trades_count"] = len(trades)
        return len(trades)

    audit_record = AsyncMock(return_value=SimpleNamespace(id="audit-1"))
    audit_service = SimpleNamespace(record=audit_record)

    monkeypatch.setattr("scripts.seed_data.store_articles_jsonl_to_db", _fake_store_articles_jsonl_to_db)
    monkeypatch.setattr("scripts.seed_data.import_trade_logs_from_csv", _fake_import_trade_logs_from_csv)
    monkeypatch.setattr("scripts.seed_data.store_trade_logs", _fake_store_trade_logs)

    stats = await seed_project_data(config=config, base_dir=tmp_path, audit_service=audit_service)

    assert stats.articles_inserted == 1
    assert stats.articles_updated == 1
    assert stats.article_tasks_generated == 1
    assert stats.trade_logs_imported == 2
    assert calls["article_paths"] == [crawl_dir / "articles.jsonl"]
    assert calls["trade_paths"] == [trade_path]
    assert calls["trades_count"] == 2
    audit_record.assert_awaited_once()
    assert audit_record.call_args.kwargs["event_type"] == "seed_project_data"


def test_init_project_cli_invokes_init_and_seed(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")

    calls: dict[str, object] = {}

    def _fake_init_db(*, project_root: Path) -> None:
        calls["project_root"] = project_root

    async def _fake_seed_project_data(*, config, base_dir: Path, article_jsonl_paths=None, trade_log_paths=None):
        del config, article_jsonl_paths, trade_log_paths
        calls["seed_base_dir"] = base_dir
        return type(
            "Stats",
            (),
            {
                "articles_inserted": 1,
                "articles_updated": 0,
                "trade_logs_imported": 0,
            },
        )()

    monkeypatch.setattr("cli.main.init_db", _fake_init_db)
    monkeypatch.setattr("cli.main.seed_project_data", _fake_seed_project_data)

    runner = CliRunner()
    result = runner.invoke(app, ["init-project", "--config", str(config_path)])

    assert result.exit_code == 0
    assert calls["project_root"] == tmp_path
    assert calls["seed_base_dir"] == tmp_path
    assert "Project initialization complete" in result.output
