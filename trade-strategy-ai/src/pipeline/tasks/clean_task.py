from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import or_, select

from src.common.utils import ensure_dir, write_json
from src.db.session import session_scope
from src.models.blog_article import BlogArticle
from src.models.raw_article import RawArticle


ProgressCallback = Callable[[dict[str, Any]], None]


def _emit_progress(
	*, progress_callback: ProgressCallback | None, status: str, current: int, total: int, current_step: str, current_dataset: str | None = None
) -> None:
	if progress_callback is None:
		return
	percent = round((current / total) * 100, 2) if total else 0.0
	progress_callback(
		{
			"job_type": "clean",
			"stage": "clean",
			"status": status,
			"current": current,
			"total": total,
			"percent": percent,
			"remaining": max(total - current, 0),
			"current_step": current_step,
			"current_dataset": current_dataset,
		}
	)


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
	*,
	input_path: Path,
	output_path: Path,
	remove_duplicates: bool = False,
	max_articles: int | None = None,
	progress_callback: ProgressCallback | None = None,
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

	# Apply max_articles limit
	if max_articles is not None:
		records = records[:max_articles]

	# Process each record
	for index, rec in enumerate(records, start=1):
		_emit_progress(
			progress_callback=progress_callback,
			status="running",
			current=index,
			total=len(records),
			current_step=str(input_path.name),
			current_dataset=str(output_path.name),
		)
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

	_emit_progress(
		progress_callback=progress_callback,
		status="success",
		current=len(records),
		total=len(records),
		current_step=str(input_path.name),
		current_dataset=str(output_path.name),
	)

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
	*,
	base_dir: Path,
	input_paths: list[Path],
	force: bool = False,
	remove_duplicates: bool = False,
	max_articles: int | None = None,
	progress_callback: ProgressCallback | None = None,
) -> CleanResult:
	out_dir = ensure_dir(base_dir / "data" / "processed" / "pipeline" / "clean")
	stats: dict[str, Any] = {"files": [], "remove_duplicates": remove_duplicates, "max_articles": max_articles}
	cleaned_paths: list[Path] = []

	for index, p in enumerate(input_paths, start=1):
		if not p.exists():
			continue
		out_path = out_dir / (p.parent.name + ".articles.cleaned.jsonl")
		if out_path.exists() and not force:
			cleaned_paths.append(out_path)
			_emit_progress(
				progress_callback=progress_callback,
				status="success",
				current=index,
				total=len(input_paths),
				current_step=str(p.name),
				current_dataset=str(out_path.name),
			)
			continue
		file_stats = clean_articles_jsonl(
			input_path=p,
			output_path=out_path,
			remove_duplicates=remove_duplicates,
			max_articles=max_articles,
			progress_callback=progress_callback,
		)
		stats["files"].append(file_stats)
		cleaned_paths.append(out_path)
		_emit_progress(
			progress_callback=progress_callback,
			status="success",
			current=index,
			total=len(input_paths),
			current_step=str(p.name),
			current_dataset=str(out_path.name),
		)

	stats_path = out_dir / "clean_stats.json"
	write_json(stats_path, stats)
	return CleanResult(cleaned_paths=cleaned_paths, stats_path=stats_path)


# ============ 数据库存储支持 ============


async def _clean_raw_articles_from_db(
	*,
	output_path: Path,
	source: str | None = None,
	author_id: str | None = None,
	remove_duplicates: bool = False,
	max_articles: int | None = None,
	progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
	"""从数据库读取 raw_articles，清洗后写入 JSONL 文件。"""
	total = 0
	total_comments = 0
	kept_comments = 0
	filtered_comments = 0
	duplicates_removed = 0

	if output_path.exists():
		output_path.unlink()

	async with session_scope() as session:
		stmt = (
			select(RawArticle)
			.outerjoin(BlogArticle, BlogArticle.source_url == RawArticle.source_url)
			.where(RawArticle.is_processed.is_(False))
			.where(
				or_(
					BlogArticle.id.is_(None),
					BlogArticle.content_hash.is_distinct_from(RawArticle.content_hash),
				)
			)
		)
		if source:
			stmt = stmt.where(RawArticle.source == source)
		if author_id:
			stmt = stmt.where(RawArticle.author_id == author_id)

		result = await session.execute(stmt)
		records = result.scalars().all()

	# 构建去重集合
	seen_hash: set[str] = set()
	seen_url: set[str] = set()
	unique_records: list[dict[str, Any]] = []

	for r in records:
		total += 1
		rec = r.to_clean_payload()
		h = rec.get("content_hash")
		u = rec.get("source_url")
		is_dup = False
		if remove_duplicates:
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
			unique_records.append(rec)

	# 应用 max_articles 限制
	if max_articles is not None:
		unique_records = unique_records[:max_articles]

	# Process each record
	total_records = len(unique_records)
	for index, rec in enumerate(unique_records, start=1):
		_emit_progress(
			progress_callback=progress_callback,
			status="running",
			current=index,
			total=total_records,
			current_step="db-clean",
			current_dataset=str(output_path.name),
		)
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

	_emit_progress(
		progress_callback=progress_callback,
		status="success",
		current=total_records,
		total=total_records,
		current_step="db-clean",
		current_dataset=str(output_path.name),
	)

	return {
		"input_source": "raw_articles_db",
		"output_path": str(output_path),
		"records": total,
		"comments_total": total_comments,
		"comments_kept": kept_comments,
		"comments_filtered": filtered_comments,
		"duplicates_removed": duplicates_removed,
	}


async def run_clean_from_db_task(
	*,
	base_dir: Path,
	source: str | None = None,
	author_id: str | None = None,
	force: bool = False,
	remove_duplicates: bool = False,
	max_articles: int | None = None,
	progress_callback: ProgressCallback | None = None,
) -> CleanResult:
	"""从数据库 raw_articles 读取并清洗，输出到 JSONL 文件。"""
	out_dir = ensure_dir(base_dir / "data" / "processed" / "pipeline" / "clean")

	# 根据 source/author_id 生成输出文件名
	if author_id:
		filename = f"{author_id}.articles.cleaned.jsonl"
	elif source:
		filename = f"{source}.articles.cleaned.jsonl"
	else:
		filename = "all.articles.cleaned.jsonl"

	out_path = out_dir / filename
	stats: dict[str, Any] = {"files": [], "source": source, "author_id": author_id, "remove_duplicates": remove_duplicates, "max_articles": max_articles}

	# DB mode is incremental: a cached file may predate newly crawled RawArticle
	# records. Rebuild from the authoritative unprocessed rows on every run.

	file_stats = await _clean_raw_articles_from_db(
		output_path=out_path,
		source=source,
		author_id=author_id,
		remove_duplicates=remove_duplicates,
		max_articles=max_articles,
		progress_callback=progress_callback,
	)
	stats["files"].append(file_stats)

	stats_path = out_dir / "clean_stats.json"
	write_json(stats_path, stats)
	return CleanResult(cleaned_paths=[out_path], stats_path=stats_path)
