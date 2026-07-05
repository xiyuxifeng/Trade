from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.pipeline.tasks.process_tasks import (
    ProcessFatalError,
    ProcessTasksStats,
    _create_handlers,
    _dedup_by_article_id,
    _rebuild_pending_tasks,
    run_process_tasks,
)
from src.services.job_control import JobControlInterrupted


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

    @pytest.mark.asyncio
    async def test_article_ingested_handler_runs_stage3_single_article_analysis(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.llm.model = ["qwen3-8b", "fallback"]
        captured: dict[str, object] = {"models": []}

        class _Service:
            def __init__(self, **kwargs: object) -> None:
                runtime = kwargs["prompt_runtime_service"]
                captured["models"].append(runtime._model)

            async def run_analysis(self, **kwargs: object) -> object:
                captured.update(kwargs)
                return SimpleNamespace(status="ready")

        class _Session:
            async def scalar(self, _query: object) -> object | None:
                return True

        @asynccontextmanager
        async def fake_session_scope() -> object:
            yield _Session()

        monkeypatch.setattr(
            "src.pipeline.tasks.process_tasks.Stage3SingleArticleService",
            _Service,
        )
        monkeypatch.setattr("src.db.session.session_scope", fake_session_scope)

        handlers = _create_handlers(mock_config, version="v1")
        article_id = str(uuid4())
        await handlers["article_ingested"]({"article_id": article_id})

        assert str(captured["article_id"]) == article_id
        assert captured["article_revision_id"] is None
        assert captured["models"] == ["qwen3-8b"]

    @pytest.mark.asyncio
    async def test_article_ingested_handler_fails_when_stage3_structure_not_persisted(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_config = MagicMock()

        class _Service:
            def __init__(self, **_kwargs: object) -> None:
                pass

            async def run_analysis(self, **_kwargs: object) -> object:
                return SimpleNamespace(status="partial")

        class _Session:
            async def scalar(self, _query: object) -> object | None:
                return None

        @asynccontextmanager
        async def fake_session_scope() -> object:
            yield _Session()

        monkeypatch.setattr(
            "src.pipeline.tasks.process_tasks.Stage3SingleArticleService",
            _Service,
        )
        monkeypatch.setattr("src.db.session.session_scope", fake_session_scope)

        handlers = _create_handlers(mock_config, version="v1")
        article_id = str(uuid4())

        with pytest.raises(ProcessFatalError, match="article analysis was not persisted"):
            await handlers["article_ingested"]({"article_id": article_id})


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


@pytest.mark.asyncio
async def test_rebuild_pending_tasks_uses_missing_stage3_article_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    article_without_structure = (
        uuid4(),
        "tgb",
        "author-a",
        "author A",
        "https://example.com/a",
        "hash-a",
        {"site": "tgb", "trader_id": "trader_a"},
    )

    class _QueryAwareSession:
        async def execute(self, query: object) -> object:
            compiled = str(query)
            assert "article_structures" in compiled
            assert "article_metadata" not in compiled
            return SimpleNamespace(all=lambda: [article_without_structure])

    appended: list[dict[str, object]] = []

    @asynccontextmanager
    async def fake_session_scope() -> object:
        yield _QueryAwareSession()

    def fake_append_jsonl(_path: Path, task: dict[str, object]) -> None:
        appended.append(task)

    monkeypatch.setattr("src.db.session.session_scope", fake_session_scope)
    monkeypatch.setattr("src.common.utils.append_jsonl", fake_append_jsonl)

    pending_path = tmp_path / "pending_tasks.jsonl"
    await _rebuild_pending_tasks(pending_path, "v1")

    assert len(appended) == 1
    assert appended[0]["details"]["article_id"] == str(article_without_structure[0])


@pytest.mark.asyncio
async def test_run_process_tasks_respects_cancel_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pending_path = tmp_path / "pending_tasks.jsonl"
    pending_path.write_text(
        '{"task_id":"1","type":"article_ingested","details":{"article_id":"a"},"created_at":"2026-01-01"}\n',
        encoding="utf-8",
    )

    async def cancel_check() -> bool:
        return True

    async def fake_handler(_details: object) -> None:
        raise AssertionError("handler should not run")

    def fake_create_handlers(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"article_ingested": fake_handler}

    monkeypatch.setattr("src.pipeline.tasks.process_tasks._create_handlers", fake_create_handlers)

    with pytest.raises(JobControlInterrupted):
        await run_process_tasks(
            config=SimpleNamespace(llm=SimpleNamespace(provider=None, model=None, url=None, api_key=None)),
            pending_path=pending_path,
            cancel_check=cancel_check,
        )


@pytest.mark.asyncio
async def test_run_process_tasks_counts_failed_tasks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pending_path = tmp_path / "pending_tasks.jsonl"
    pending_path.write_text(
        '{"task_id":"1","type":"article_ingested","details":{"article_id":"a"},"created_at":"2026-01-01"}\n',
        encoding="utf-8",
    )

    async def fake_handler(_details: object) -> None:
        raise ValueError("boom")

    def fake_create_handlers(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"article_ingested": fake_handler}

    monkeypatch.setattr("src.pipeline.tasks.process_tasks._create_handlers", fake_create_handlers)

    stats = await run_process_tasks(
        config=SimpleNamespace(llm=SimpleNamespace(provider=None, model=None, url=None, api_key=None)),
        pending_path=pending_path,
        failed_path=tmp_path / "failed_tasks.jsonl",
        dead_path=tmp_path / "dead_tasks.jsonl",
    )

    assert stats.failed == 1
    assert stats.fatal_error is None
