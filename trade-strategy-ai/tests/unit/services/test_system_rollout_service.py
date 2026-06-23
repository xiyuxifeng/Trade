from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.job import Job
from src.models.stage2_canonical import PromptRun, PromptValidationState
from src.services.stage3_prompt_retirement import LegacyPromptRetirementItem
from src.services.system_rollout_service import SystemRolloutService


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


@pytest.fixture
async def session_factory(tmp_path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'system-rollout.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(bind=sync_conn, tables=[PromptRun.__table__, Job.__table__]))

    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@asynccontextmanager
async def _session_scope(factory: async_sessionmaker[AsyncSession]):
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _write_stage2_reports(report_dir) -> None:
    preflight = {"inventory": {"database": {"raw_articles": 2, "blog_articles": 2}}}
    apply_report = {
        "categories": {
            "articles": {
                "rejected_count": 0,
                "conflict_count": 1,
                "orphan_count": 0,
                "hash_mismatch_count": 0,
            }
        }
    }
    verify_report = {"inventory": {"database": {"raw_articles": 2, "blog_articles": 2}}}
    recovery_export = {"items": [{"kind": "legacy_mapping", "id": "a"}]}
    for name, payload in (
        ("preflight_inventory.json", preflight),
        ("apply_report.json", apply_report),
        ("verify_report.json", verify_report),
        ("recovery_export.json", recovery_export),
    ):
        (report_dir / name).write_text(json.dumps(payload), encoding="utf-8")


async def _seed_prompt_runs_and_batch_job(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as session:
        session.add_all(
            [
                PromptRun(
                    prompt_run_id=uuid4(),
                    run_id="run-1",
                    article_id=None,
                    prompt_name="article_analysis_v1",
                    prompt_version="article_analysis_v2",
                    schema_name="article_analysis",
                    schema_version="article_analysis_schema_v2",
                    provider="openai",
                    model="gpt-5.4",
                    input_object_type="article_revision",
                    input_object_id="article-1",
                    input_version_id="revision-1",
                    input_hash="hash-1",
                    request_json={"content_hash": "content-hash-1"},
                    raw_output={"value": 1},
                    raw_output_text='{"value":1}',
                    validation_state=PromptValidationState.valid,
                    validation_errors={},
                    retry_count=0,
                    token_usage={"total_tokens": 12},
                    cost_amount=None,
                    cost_currency=None,
                    started_at=datetime(2026, 6, 23, 9, 0, tzinfo=UTC),
                    completed_at=datetime(2026, 6, 23, 9, 1, tzinfo=UTC),
                ),
                PromptRun(
                    prompt_run_id=uuid4(),
                    run_id="run-0",
                    article_id=None,
                    prompt_name="article_analysis_v1",
                    prompt_version="article_analysis_v1",
                    schema_name="article_analysis",
                    schema_version="article_analysis_schema_v1",
                    provider="openai",
                    model="gpt-5.4",
                    input_object_type="article_revision",
                    input_object_id="article-1",
                    input_version_id="revision-1",
                    input_hash="hash-0",
                    request_json={"content_hash": "content-hash-0"},
                    raw_output={"value": 0},
                    raw_output_text='{"value":0}',
                    validation_state=PromptValidationState.valid,
                    validation_errors={},
                    retry_count=0,
                    token_usage={"total_tokens": 10},
                    cost_amount=None,
                    cost_currency=None,
                    started_at=datetime(2026, 6, 22, 9, 0, tzinfo=UTC),
                    completed_at=datetime(2026, 6, 22, 9, 1, tzinfo=UTC),
                ),
                Job(
                    id=uuid4(),
                    job_type="stage3-article-batch",
                    status="failed",
                    params={"limit": 2},
                    result={"rejected_or_conflicted_items": ["revision-2"]},
                    error={"message": "failed"},
                    runtime_state={
                        "checkpoint": {
                            "processed_revision_ids": ["revision-1"],
                            "processed_count": 1,
                            "processed_items": [
                                {
                                    "article_revision_id": "revision-1",
                                    "input_hash": "hash-1",
                                    "prompt_run_id": "prompt-run-1",
                                    "validation_state": "valid",
                                    "prompt_retry_count": 0,
                                    "automatic_review_statuses": ["needs_human_review"],
                                    "rejected_or_conflicted": False,
                                    "resume_point": "revision-1",
                                }
                            ],
                        },
                        "last_safe_point": "revision-1",
                    },
                    progress={"quality_stats": {"automatic_review_status_counts": {"needs_human_review": 1}}},
                    artifacts=[],
                    created_by="test",
                    idempotency_key="stage3-article-batch:test",
                    retry_count=0,
                    max_retries=1,
                    retry_backoff_seconds=0,
                    cancel_requested=False,
                    created_at=datetime(2026, 6, 23, 9, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 6, 23, 9, 2, tzinfo=UTC),
                ),
            ]
        )
        await session.commit()


def _inventory_provider() -> tuple[LegacyPromptRetirementItem, ...]:
    return (
        LegacyPromptRetirementItem(
            legacy_filename="rule_extraction.md",
            prompt_path="prompts/rule_extraction.md",
            stem="rule_extraction",
            aliases=("strategy_rules",),
            loader_registry_entry="none",
            runtime_callers=("legacy",),
            reference_classes=("historical",),
            legacy_output_format="json",
            replacement_prompt="article_analysis_v1",
            replacement_schema="article_analysis_schema_v2",
            runtime_disposition="redirected_to_v1",
            historical_read_disposition="stored_metadata_only",
            rollback_disposition="git_restore_does_not_reactivate",
            deletion_gate_status="passed",
            prompt_file_exists=False,
        ),
    )


@pytest.mark.asyncio
async def test_system_rollout_service_surfaces_database_prompt_batch_and_route_evidence(session_factory, tmp_path) -> None:
    report_dir = tmp_path / "stage2-reports"
    report_dir.mkdir()
    _write_stage2_reports(report_dir)
    await _seed_prompt_runs_and_batch_job(session_factory)

    service = SystemRolloutService(
        session_scope_factory=lambda: _session_scope(session_factory),
        stage2_report_dir=report_dir,
        prompt_inventory_provider=_inventory_provider,
    )

    result = await service.get_summary(actor_role="admin")

    assert result.status == "ok"
    assert len(result.payload["supported_rollout_states"]) == 6

    database_item = next(item for item in result.payload["items"] if item["migration_id"] == "stage2_canonical_database")
    assert database_item["current_state"] == "new_default"
    assert database_item["comparison"]["pre_counts"]["raw_articles"] == 2
    assert database_item["comparison"]["conflicted_rows"] == 1
    assert database_item["rollback_or_recovery"]["no_silent_data_loss"] is True

    prompt_item = next(item for item in result.payload["items"] if item["migration_id"] == "stage3_prompt_contracts")
    assert prompt_item["rollback_or_recovery"]["selected_previous_contract"]["prompt_version"] == "article_analysis_v1"
    assert prompt_item["rollback_or_recovery"]["raw_output_preserved"] is True
    assert prompt_item["duplicate_formal_source_detected"] is False

    batch_item = next(item for item in result.payload["items"] if item["migration_id"] == "stage3_batch_processing")
    assert batch_item["current_state"] == "limited_enablement"
    assert batch_item["rollback_or_recovery"]["idempotency_key"] == "stage3-article-batch:test"
    assert batch_item["rollback_or_recovery"]["resume_point"] == "revision-1"
    assert batch_item["rollback_or_recovery"]["processed_items"][0]["input_hash"] == "hash-1"
    assert batch_item["rollback_or_recovery"]["rejected_or_conflicted_items"] == ["revision-2"]

    route_item = next(item for item in result.payload["items"] if item["migration_id"] == "legacy_routes")
    assert route_item["current_state"] == "legacy_read_only"
    assert route_item["rollback_or_recovery"]["stage12_required_for_retirement"] is True
