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
    async def test_article_ingested_handler_targets_single_article(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        captured: dict[str, object] = {}

        async def fake_extract_and_store_metadata(**kwargs: object) -> object:
            captured.update(kwargs)
            return SimpleNamespace(
                fatal_error=None,
                failed=0,
                extracted=1,
                skipped=0,
                processed=1,
                failure_details=[],
                fatal_error_type=None,
                fatal_article_id=None,
            )

        class _Session:
            async def scalar(self, _query: object) -> object | None:
                return SimpleNamespace(processed_at=True)

        @asynccontextmanager
        async def fake_session_scope() -> object:
            yield _Session()

        monkeypatch.setattr(
            "src.agents.data_agent.skills.extract_article_metadata.extract_and_store_metadata",
            fake_extract_and_store_metadata,
        )
        monkeypatch.setattr("src.db.session.session_scope", fake_session_scope)

        handlers = _create_handlers(mock_config, version="v1")
        article_id = str(uuid4())
        await handlers["article_ingested"]({"article_id": article_id})

        assert "target_article_ids" in captured
        assert [str(item) for item in captured["target_article_ids"]] == [article_id]

    @pytest.mark.asyncio
    async def test_article_ingested_handler_fails_when_metadata_not_persisted(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_config = MagicMock()

        class _Stats:
            processed = 1
            extracted = 1
            skipped = 0
            failed = 0
            fatal_error = None
            fatal_error_type = None
            fatal_article_id = None
            failure_details: list[dict[str, object]] = []

        async def fake_extract_and_store_metadata(**kwargs: object) -> object:
            return _Stats()

        class _Session:
            async def scalar(self, _query: object) -> object | None:
                return None

        @asynccontextmanager
        async def fake_session_scope() -> object:
            yield _Session()

        monkeypatch.setattr(
            "src.agents.data_agent.skills.extract_article_metadata.extract_and_store_metadata",
            fake_extract_and_store_metadata,
        )
        monkeypatch.setattr("src.db.session.session_scope", fake_session_scope)

        handlers = _create_handlers(mock_config, version="v1")
        article_id = str(uuid4())

        with pytest.raises(ProcessFatalError, match="article metadata was not persisted"):
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
async def test_rebuild_pending_tasks_v1_only_uses_v1_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    article_v1_target = (
        uuid4(),
        "tgb",
        "author-a",
        "author A",
        "https://example.com/a",
        "hash-a",
        {"site": "tgb", "trader_id": "trader_a"},
    )
    article_other_version = (
        uuid4(),
        "tgb",
        "author-b",
        "author B",
        "https://example.com/b",
        "hash-b",
        {"site": "tgb", "trader_id": "trader_b"},
    )

    class _QueryAwareSession:
        def __init__(self) -> None:
            self._execute_calls = 0

        async def execute(self, query: object) -> object:
            self._execute_calls += 1
            if self._execute_calls > 1:
                return SimpleNamespace(all=lambda: [])

            compiled = str(query)
            if "schema_version" in compiled:
                rows = [article_v1_target]
            else:
                rows = [article_v1_target, article_other_version]
            return SimpleNamespace(all=lambda: rows)

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
    assert appended[0]["details"]["article_id"] == str(article_v1_target[0])


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
    )

    assert stats.failed == 1
    assert stats.fatal_error is None
