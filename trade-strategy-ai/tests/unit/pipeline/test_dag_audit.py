from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.config import AppConfig
from src.pipeline.dag import run_pipeline


@pytest.mark.asyncio
async def test_run_pipeline_records_audit_event(tmp_path: Path) -> None:
    config = AppConfig()
    base_dir = tmp_path / "project"
    base_dir.mkdir()

    audit_record = AsyncMock(return_value=SimpleNamespace(id="audit-1"))
    audit_cls = MagicMock(return_value=SimpleNamespace(record=audit_record))

    with (
        patch("src.pipeline.dag.AuditService", audit_cls),
        patch("src.pipeline.dag.run_crawl_task", return_value=SimpleNamespace(outputs=[])),
        patch("src.pipeline.dag.run_clean_task", return_value=SimpleNamespace(cleaned_paths=[])),
        patch("src.pipeline.dag.run_validate_task", return_value=SimpleNamespace(validated_paths=[])),
        patch("src.pipeline.dag.store_articles_jsonl_to_db", AsyncMock(return_value=SimpleNamespace(
            read_records=1,
            inserted_articles=1,
            updated_articles=0,
            skipped_duplicates=0,
            ensured_metadata=1,
            generated_tasks=1,
        ))),
        patch("src.pipeline.dag.run_process_tasks", AsyncMock(return_value=SimpleNamespace(processed=0))),
        patch("src.pipeline.dag.run_export_task", AsyncMock(return_value=SimpleNamespace(stats=SimpleNamespace(), duckdb_path=Path("x")))),
    ):
        await run_pipeline(config=config, base_dir=base_dir, max_articles=1, force=True)

    audit_record.assert_awaited_once()
    audit_kwargs = audit_record.call_args.kwargs
    assert audit_kwargs["event_type"] == "article_ingested_batch"
    assert audit_kwargs["actor"] == "pipeline.run_pipeline"
    assert audit_kwargs["source"] == "pipeline"
