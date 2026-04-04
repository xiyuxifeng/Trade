from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.utils import ensure_dir, write_json
from src.models.blog_article import BlogArticle
from src.pipeline.validation import DataValidator, ValidationSeverity


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
	with path.open("r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			yield json.loads(line)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
	ensure_dir(path.parent)
	with path.open("a", encoding="utf-8") as f:
		f.write(json.dumps(payload, ensure_ascii=False, default=str))
		f.write("\n")


def _parse_dt(value: str | None) -> datetime | None:
	if not value:
		return None
	try:
		dt = datetime.fromisoformat(value)
	except ValueError:
		return None
	if dt.tzinfo is None:
		return dt.replace(tzinfo=UTC)
	return dt


@dataclass(slots=True)
class ValidateResult:
	validated_paths: list[Path]
	report_path: Path


def _to_blog_article(record: dict[str, Any]) -> BlogArticle:
	# 用 ORM 模型当作普通对象来跑 validator（不入库）
	return BlogArticle(
		source=str(record.get("source") or ""),
		source_article_id=record.get("source_article_id"),
		source_url=str(record.get("source_url") or ""),
		title=str(record.get("title") or ""),
		author_name=record.get("author_name"),
		author_id=record.get("author_id"),
		published_at=_parse_dt(record.get("published_at")),
		crawled_at=_parse_dt(record.get("crawled_at")) or datetime.now(UTC),
		content_text=str(record.get("content_text") or ""),
		content_html=record.get("content_html"),
		summary=record.get("summary"),
		tags=record.get("tags") or [],
		content_hash=record.get("content_hash"),
		view_count=int(record.get("view_count") or 0),
		like_count=int(record.get("like_count") or 0),
		bookmark_count=int(record.get("bookmark_count") or 0),
		comment_count=int(record.get("comment_count") or 0),
		comments_payload=record.get("comments_payload") or [],
		raw_payload=record.get("raw_payload") or {},
	)


def run_validate_task(*, base_dir: Path, input_paths: list[Path], force: bool = False) -> ValidateResult:
	out_dir = ensure_dir(base_dir / "data" / "processed" / "pipeline" / "validate")
	report: dict[str, Any] = {
		"files": [],
		"summary": {"records": 0, "extractable": 0, "errors": 0, "warnings": 0},
	}
	validated_paths: list[Path] = []

	validator = DataValidator()

	for p in input_paths:
		if not p.exists():
			continue
		out_path = out_dir / (p.stem + ".validated.jsonl")
		if out_path.exists() and not force:
			validated_paths.append(out_path)
			continue
		if out_path.exists():
			out_path.unlink()

		file_stats: dict[str, Any] = {
			"input_path": str(p),
			"output_path": str(out_path),
			"records": 0,
			"extractable": 0,
			"issues": [],
		}

		for rec in _iter_jsonl(p):
			file_stats["records"] += 1
			report["summary"]["records"] += 1

			article = _to_blog_article(rec)
			vr = validator.validate_article(article)
			issues_dump = [
				{
					"code": i.code,
					"severity": i.severity.value,
					"message": i.message,
					"field_name": i.field_name,
					"context": i.context,
				}
				for i in vr.issues
			]

			errors = [i for i in vr.issues if i.severity == ValidationSeverity.ERROR]
			warnings = [i for i in vr.issues if i.severity == ValidationSeverity.WARNING]
			report["summary"]["errors"] += len(errors)
			report["summary"]["warnings"] += len(warnings)

			extractable = vr.is_valid and len(article.content_text.strip()) >= 80
			if extractable:
				file_stats["extractable"] += 1
				report["summary"]["extractable"] += 1

			enriched = {
				**rec,
				"validation": {"is_valid": vr.is_valid, "issues": issues_dump},
				"extractable": extractable,
			}
			_append_jsonl(out_path, enriched)

			if issues_dump:
				file_stats["issues"].append(
					{
						"source_url": rec.get("source_url"),
						"title": rec.get("title"),
						"issues": issues_dump,
					}
				)

		report["files"].append(file_stats)
		validated_paths.append(out_path)

	report_path = out_dir / "validation_report.json"
	write_json(report_path, report)
	return ValidateResult(validated_paths=validated_paths, report_path=report_path)
