from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.paths import resolve_project_path

FAILED_TASKS_PATH = resolve_project_path("data/processed/pipeline/failed_tasks.jsonl")
PROCESSING_STATE_PATH = resolve_project_path("data/processed/pipeline/article_processing_states.json")

MANUAL_PROCESSING_STATES = {"ignored", "manual_review_required"}


def load_failed_article_records(path: Path = FAILED_TASKS_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    records: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                task = json.loads(line)
            except json.JSONDecodeError:
                continue
            if task.get("type") != "article_ingested":
                continue
            details = task.get("details", {})
            article_id = details.get("article_id")
            if not isinstance(article_id, str) or not article_id.strip():
                continue
            failure = {
                "failure_message": task.get("error") or task.get("fatal_error"),
                "failure_type": task.get("error_type") or task.get("fatal_error_type"),
                "failed_at": task.get("failed_at"),
                "failed_retry_count": task.get("retry_count"),
            }
            existing = records.get(article_id)
            if existing is None or str(failure.get("failed_at") or "") >= str(existing.get("failed_at") or ""):
                records[article_id] = failure
    return records


def load_article_processing_state_records(path: Path = PROCESSING_STATE_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}

    records: dict[str, dict[str, Any]] = {}
    for article_id, record in payload.items():
        if not isinstance(article_id, str) or not isinstance(record, dict):
            continue
        status_value = record.get("processing_status")
        if status_value not in MANUAL_PROCESSING_STATES:
            continue
        records[article_id] = {
            "processing_status": status_value,
            "processing_note": record.get("processing_note"),
            "processing_updated_at": record.get("processing_updated_at"),
            "processing_updated_by": record.get("processing_updated_by"),
        }
    return records


def set_article_processing_state(
    article_id: str,
    *,
    processing_status: str,
    processing_updated_by: str,
    processing_note: str | None = None,
    path: Path = PROCESSING_STATE_PATH,
) -> dict[str, Any]:
    if processing_status not in MANUAL_PROCESSING_STATES:
        raise ValueError(f"unsupported processing status: {processing_status}")

    records = load_article_processing_state_records(path)
    updated_at = datetime.now(UTC).isoformat()
    records[article_id] = {
        "processing_status": processing_status,
        "processing_note": processing_note,
        "processing_updated_at": updated_at,
        "processing_updated_by": processing_updated_by,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return records[article_id]


def clear_article_processing_state(article_id: str, path: Path = PROCESSING_STATE_PATH) -> None:
    records = load_article_processing_state_records(path)
    if article_id not in records:
        return
    records.pop(article_id, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
