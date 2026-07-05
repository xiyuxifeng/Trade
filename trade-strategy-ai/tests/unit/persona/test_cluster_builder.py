from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock

from src.common.config import AppConfig, CrawlConfig, RuntimeConfig, TraderConfig
from src.persona.cluster_builder import build_clusters_from_db


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    async def execute(self, _stmt):
        return _FakeResult(
            [
                (
                    "article-1",
                    "author-1",
                    "https://example.com/a",
                    datetime(2026, 7, 5, tzinfo=UTC),
                    {"trader_id": "trader-001"},
                )
            ]
        )


@pytest.mark.asyncio
async def test_build_clusters_uses_stage3_article_analysis(tmp_path, monkeypatch):
    @asynccontextmanager
    async def _fake_session_scope():
        yield _FakeSession()

    stage3_loader = AsyncMock(
        return_value={
            "article-1": SimpleNamespace(
                processed_at=datetime(2026, 7, 5, 10, 0, tzinfo=UTC),
                strategy_rules=[
                    {
                        "schema_version": "stage3_article_analysis_v1",
                        "claim_key": "entry.trigger",
                        "rule_type": "entry",
                        "instrument_focus": "stock",
                        "condition": {},
                        "action": {"type": "enter", "params": {}},
                        "params": {},
                        "confidence": 0.8,
                    }
                ],
                preconditions=[],
            )
        }
    )

    monkeypatch.setattr("src.persona.cluster_builder.session_scope", _fake_session_scope)
    monkeypatch.setattr(
        "src.services.article_analysis_selection_service.ArticleAnalysisSelectionService.load_effective_analysis_map",
        stage3_loader,
    )

    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
        crawl=CrawlConfig(),
        traders=[TraderConfig(trader_id="trader-001", display_name="Trader 001")],
    )

    written, stats = await build_clusters_from_db(config=config, dest=tmp_path / "clusters.json")

    assert written == tmp_path / "clusters.json"
    assert stats.used_articles == 1
    assert stats.clusters_built == 1
    stage3_loader.assert_awaited_once()
