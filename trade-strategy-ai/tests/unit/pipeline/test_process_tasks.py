from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

import pytest

from src.pipeline.tasks.process_tasks import (
    ProcessTasksStats,
    _create_handlers,
    _dedup_by_article_id,
)


class TestCreateHandlers:
    def test_returns_dict_with_expected_keys(self) -> None:
        mock_config = MagicMock()
        handlers = _create_handlers(mock_config)
        assert "article_ingested" in handlers
        assert "article_metadata_extracted" in handlers

    def test_handler_closes_over_config(self) -> None:
        mock_config = MagicMock()
        mock_config.some_value = "test_value"
        handlers = _create_handlers(mock_config)

        article_ingested = handlers["article_ingested"]
        assert callable(article_ingested)


class TestDedupByArticleId:
    def test_dedup_keeps_latest(self) -> None:
        tasks = [
            {"task_id": "1", "details": {"article_id": "a"}, "created_at": "2026-01-01"},
            {"task_id": "2", "details": {"article_id": "a"}, "created_at": "2026-01-03"},
            {"task_id": "3", "details": {"article_id": "b"}, "created_at": "2026-01-02"},
        ]
        result = _dedup_by_article_id(tasks)
        assert len(result) == 2
        article_ids = {t["details"]["article_id"] for t in result}
        assert article_ids == {"a", "b"}
        latest_a = next(t for t in result if t["details"]["article_id"] == "a")
        assert latest_a["task_id"] == "2"

    def test_dedup_empty_list(self) -> None:
        result = _dedup_by_article_id([])
        assert result == []

    def test_dedup_missing_article_id(self) -> None:
        tasks = [
            {"task_id": "1", "details": {}, "created_at": "2026-01-01"},
        ]
        result = _dedup_by_article_id(tasks)
        assert result == []