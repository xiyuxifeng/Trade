from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from src.common.utils import ensure_dir, write_json
from src.models.blog_article import BlogArticle
from src.pipeline.validation import DataValidator


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


def _parse_dt(value: str | None) -> Any:
	if not value:
		return None
	try:
		from datetime import datetime
		dt = datetime.fromisoformat(value)
		if dt.tzinfo is None:
			from datetime import UTC
			return dt.replace(tzinfo=UTC)
		return dt
	except (ValueError, TypeError):
		return None


def _to_blog_article(record: dict[str, Any]) -> BlogArticle:
	return BlogArticle(
		source=str(record.get("source") or ""),
		source_article_id=record.get("source_article_id"),
		source_url=str(record.get("source_url") or ""),
		title=str(record.get("title") or ""),
		author_name=record.get("author_name"),
		author_id=record.get("author_id"),
		published_at=_parse_dt(record.get("published_at")),
		crawled_at=_parse_dt(record.get("crawled_at")),
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


@dataclass(slots=True)
class CleanResult:
	cleaned_paths: list[Path]
	stats_path: Path


def clean_articles_jsonl(
	*, input_path: Path, output_path: Path, remove_duplicates: bool = False
) -> dict[str, Any]:
	total = 0
	total_comments = 0
	kept_comments = 0
	filtered_comments = 0
	duplicates_removed = 0

	if output_path.exists():
		output_path.unlink()

	# Load all records for deduplication
	records = list(_iter_jsonl(input_path))

	# Deduplicate if requested
	if remove_duplicates:
		articles = [_to_blog_article(r) for r in records]
		validator = DataValidator()
		duplicate_issues = validator.detect_article_duplicates(articles)
		# Build set of duplicate hashes
		seen_hash: set[str] = set()
		seen_url: set[str] = set()
		unique_records: list[dict[str, Any]] = []
		duplicates_removed = 0
		for r in records:
			h = r.get("content_hash")
			u = r.get("source_url")
			is_dup = False
			if h and h in seen_hash:
				is_dup = True
			if u and u in seen_url:
				is_dup = True
			if is_dup:
				duplicates_removed += 1
			else:
				if h:
					seen_hash.add(h)
				if u:
					seen_url.add(u)
				unique_records.append(r)
		records = unique_records

	# Process each record
	for rec in records:
		total += 1
		comments = rec.get("comments") or rec.get("comments_payload") or []
		if not isinstance(comments, list):
			comments = []

		total_comments += len(comments)
		kept = [c for c in comments if not bool(c.get("is_filtered"))]
		kept_comments += len(kept)
		filtered_comments += max(0, len(comments) - len(kept))

		cleaned = {
			**rec,
			"comments_payload": kept,
			"comments_filtered_count": max(0, len(comments) - len(kept)),
			"comments_total_count": len(comments),
		}
		# 兼容下游：统一字段名
		cleaned.pop("comments", None)
		_append_jsonl(output_path, cleaned)

	return {
		"input_path": str(input_path),
		"output_path": str(output_path),
		"records": total,
		"comments_total": total_comments,
		"comments_kept": kept_comments,
		"comments_filtered": filtered_comments,
		"duplicates_removed": duplicates_removed,
	}


def run_clean_task(
	*, base_dir: Path, input_paths: list[Path], force: bool = False, remove_duplicates: bool = False
) -> CleanResult:
	out_dir = ensure_dir(base_dir / "data" / "processed" / "pipeline" / "clean")
	stats: dict[str, Any] = {"files": [], "remove_duplicates": remove_duplicates}
	cleaned_paths: list[Path] = []

	for p in input_paths:
		if not p.exists():
			continue
		out_path = out_dir / (p.parent.name + ".articles.cleaned.jsonl")
		if out_path.exists() and not force:
			cleaned_paths.append(out_path)
			continue
		file_stats = clean_articles_jsonl(input_path=p, output_path=out_path, remove_duplicates=remove_duplicates)
		stats["files"].append(file_stats)
		cleaned_paths.append(out_path)

	stats_path = out_dir / "clean_stats.json"
	write_json(stats_path, stats)
	return CleanResult(cleaned_paths=cleaned_paths, stats_path=stats_path)
