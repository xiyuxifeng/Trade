from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.utils import append_jsonl, ensure_dir
from src.db.session import session_scope
from src.domain.enums import QualityStatus
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.models.raw_article import RawArticle
from src.models.stage2_canonical import ArticleRevision
from src.schemas.contracts import AgentTask


ProgressCallback = Callable[[dict[str, Any]], None]


def _emit_progress(
	progress_callback: ProgressCallback | None,
	*,
	status: str,
	current: int,
	total: int,
	current_step: str,
	current_dataset: str | None = None,
) -> None:
	if progress_callback is None:
		return
	percent = round((current / total) * 100, 2) if total else 0.0
	progress_callback(
		{
			"job_type": "store",
			"stage": "store",
			"status": status,
			"current": current,
			"total": total,
			"percent": percent,
			"remaining": max(total - current, 0),
			"current_step": current_step,
			"current_dataset": current_dataset,
		}
	)


@dataclass(slots=True)
class StoreStats:
	read_records: int = 0
	inserted_articles: int = 0
	updated_articles: int = 0
	skipped_duplicates: int = 0
	ensured_metadata: int = 0
	generated_tasks: int = 0
	processed_raw_articles: int = 0


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
	with path.open("r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			yield json.loads(line)


def _parse_dt(value: str | None) -> datetime | None:
	if not value:
		return None
	try:
		dt = datetime.fromisoformat(value)
	except ValueError:
		return None
	# 统一为 aware datetime（无 tz 时补 UTC，避免后续比较/入库歧义）
	if dt.tzinfo is None:
		return dt.replace(tzinfo=UTC)
	return dt


def _now_utc() -> datetime:
	return datetime.now(UTC)


async def _get_article_by_source_url(session: AsyncSession, source_url: str) -> BlogArticle | None:
	return await session.scalar(select(BlogArticle).where(BlogArticle.source_url == source_url))


async def _get_article_by_content_hash(session: AsyncSession, content_hash: str) -> BlogArticle | None:
	return await session.scalar(select(BlogArticle).where(BlogArticle.content_hash == content_hash))


def _normalize_article_payload(payload: dict[str, Any]) -> dict[str, Any]:
	raw_payload = payload.get("raw_payload")
	if not isinstance(raw_payload, dict):
		raw_payload = {}

	# 将关键归属信息补入 raw_payload，方便后续聚类/回放
	raw_payload = {
		**raw_payload,
		"site": payload.get("site"),
		"trader_id": payload.get("trader_id"),
		"author_id": payload.get("author_id"),
		"author_name": payload.get("author_name"),
	}

	comments = payload.get("comments") or payload.get("comments_payload") or []
	if not isinstance(comments, list):
		comments = []

	return {
		"source": str(payload.get("source") or ""),
		"source_article_id": payload.get("source_article_id"),
		"source_url": str(payload.get("source_url") or ""),
		"title": str(payload.get("title") or "").strip(),
		"author_name": payload.get("author_name"),
		"author_id": payload.get("author_id"),
		"published_at": _parse_dt(payload.get("published_at")),
		"crawled_at": _parse_dt(payload.get("crawled_at")) or _now_utc(),
		"content_text": str(payload.get("content_text") or ""),
		"content_html": payload.get("content_html"),
		"summary": payload.get("summary"),
		"tags": payload.get("tags") or [],
		"content_hash": payload.get("content_hash"),
		"view_count": int(payload.get("view_count") or 0),
		"like_count": int(payload.get("like_count") or 0),
		"bookmark_count": int(payload.get("bookmark_count") or 0),
		"comment_count": int(payload.get("comment_count") or len(comments)),
		"comments_payload": comments,
		"raw_payload": raw_payload,
	}


async def upsert_article_from_payload(
	session: AsyncSession,
	payload: dict[str, Any],
) -> tuple[UUID, bool, bool]:
	"""Upsert BlogArticle.

	Returns: (article_id, inserted, updated)
	- inserted: 新建
	- updated: 已存在但内容/关键字段发生变化
	"""

	normalized = _normalize_article_payload(payload)
	source_url = normalized["source_url"]
	if not source_url:
		raise ValueError("source_url is required")

	content_hash = normalized.get("content_hash")
	if isinstance(content_hash, str) and content_hash:
		dup = await _get_article_by_content_hash(session, content_hash)
		if dup is not None and dup.source_url != source_url:
			# content_hash 冲突，视为重复内容：跳过入库，交由上层统计
			return dup.id, False, False

	existing = await _get_article_by_source_url(session, source_url)
	if existing is None:
		article = BlogArticle(**normalized)
		session.add(article)
		await session.flush()
		return article.id, True, False

	# Update in-place (minimal fields)
	updated = False
	for field_name, value in normalized.items():
		if field_name == "source_url":
			continue
		current = getattr(existing, field_name)
		if current != value:
			setattr(existing, field_name, value)
			updated = True
	await session.flush()
	return existing.id, False, updated


async def ensure_article_metadata(session: AsyncSession, article_id: UUID) -> bool:
	existing = await session.scalar(select(ArticleMetadata).where(ArticleMetadata.article_id == article_id))
	if existing is not None:
		return False
	session.add(ArticleMetadata(article_id=article_id))
	await session.flush()
	return True


def _build_article_revision_source_payload(article: BlogArticle) -> dict[str, Any]:
	raw_payload = article.raw_payload if isinstance(article.raw_payload, dict) else {}
	return {
		"summary": article.summary,
		"blog_article": {
			"source": article.source,
			"source_article_id": article.source_article_id,
			"source_url": article.source_url,
			"title": article.title,
			"author_name": article.author_name,
			"author_id": article.author_id,
			"published_at": article.published_at.isoformat() if article.published_at else None,
			"crawled_at": article.crawled_at.isoformat(),
			"summary": article.summary,
			"tags": article.tags,
			"content_hash": article.content_hash,
		},
		"raw_article": raw_payload,
	}


async def ensure_article_revision(session: AsyncSession, article_id: UUID) -> bool:
	article = await session.get(BlogArticle, article_id)
	if article is None or not article.content_hash:
		return False

	existing = await session.scalar(
		select(ArticleRevision).where(
			ArticleRevision.article_id == article_id,
			ArticleRevision.content_hash == article.content_hash,
		)
	)
	if existing is not None:
		return False

	latest_revision = await session.scalar(
		select(ArticleRevision)
		.where(ArticleRevision.article_id == article_id)
		.order_by(desc(ArticleRevision.revision_no))
		.limit(1)
	)
	revision_no = 1 if latest_revision is None else latest_revision.revision_no + 1
	session.add(
		ArticleRevision(
			article_id=article_id,
			revision_no=revision_no,
			content_hash=article.content_hash,
			content_text=article.content_text,
			content_html=article.content_html,
			source_payload=_build_article_revision_source_payload(article),
			captured_at=article.crawled_at,
			quality_status=QualityStatus.complete,
		)
	)
	await session.flush()
	return True


async def mark_raw_article_processed(session: AsyncSession, payload: dict[str, Any]) -> bool:
	"""Mark only the exact raw source record consumed by a successful store."""
	raw_article_id = payload.get("raw_article_id")
	if not isinstance(raw_article_id, str) or not raw_article_id:
		return False
	try:
		raw_id = UUID(raw_article_id)
	except ValueError:
		return False
	raw = await session.get(RawArticle, raw_id)
	if raw is None or raw.source_url != str(payload.get("source_url") or ""):
		return False
	if raw.is_processed:
		return False
	raw.is_processed = True
	raw.processed_at = _now_utc()
	await session.flush()
	return True


def default_pending_tasks_path(*, base_dir: Path) -> Path:
	return base_dir / "data" / "processed" / "pipeline" / "pending_tasks.jsonl"


async def store_articles_jsonl_to_db(
	*,
	base_dir: Path,
	jsonl_paths: Iterable[Path],
	pending_tasks_path: Path | None = None,
	limit: int | None = None,
	force: bool = False,
	progress_callback: ProgressCallback | None = None,
) -> StoreStats:
	stats = StoreStats()
	pending_path = pending_tasks_path or default_pending_tasks_path(base_dir=base_dir)
	ensure_dir(pending_path.parent)
	if force and pending_path.exists():
		pending_path.unlink()

	async with session_scope() as session:
		paths = [path for path in jsonl_paths if path.exists()]
		for file_index, path in enumerate(paths, start=1):
			if not path.exists():
				continue
			payloads = list(iter_jsonl(path))
			for record_index, payload in enumerate(payloads, start=1):
				stats.read_records += 1
				if limit is not None and stats.read_records > limit:
					return stats
				_emit_progress(
					progress_callback,
					status="running",
					current=record_index,
					total=len(payloads),
					current_step=str(path.name),
					current_dataset=str(pending_path.name),
				)

				article_id, inserted, updated = await upsert_article_from_payload(session, payload)
				if inserted:
					stats.inserted_articles += 1
				elif updated:
					stats.updated_articles += 1

				# content_hash duplicate skip: upsert_article_from_payload returns (id, False, False)
				# but we only count it as skip if source_url 不同且未发生更新。
				if not inserted and not updated:
					# 如果 source_url 是同一条，则可能是“完全无变化”而不是重复内容；这里不强行区分。
					# 仅当 payload 中 content_hash 命中其他 source_url 时，才视作重复跳过。
					content_hash = payload.get("content_hash")
					if isinstance(content_hash, str) and content_hash:
						dup = await _get_article_by_content_hash(session, content_hash)
						if dup is not None and dup.source_url != str(payload.get("source_url")):
							stats.skipped_duplicates += 1
							continue

				if await ensure_article_metadata(session, article_id):
					stats.ensured_metadata += 1

				await ensure_article_revision(session, article_id)
				if await mark_raw_article_processed(session, payload):
					stats.processed_raw_articles += 1

				# 增量触发：新入库或内容更新 → 生成抽取/聚类待办（先落盘，后续再异步化）
				if inserted or updated:
					task = AgentTask(
						type="article_ingested",
						title="New/updated article ingested",
						trader_id=(payload.get("trader_id") if isinstance(payload.get("trader_id"), str) else None),
						details={
							"article_id": str(article_id),
							"source": payload.get("source"),
							"site": payload.get("site"),
							"author_id": payload.get("author_id"),
							"author_name": payload.get("author_name"),
							"source_url": payload.get("source_url"),
							"content_hash": payload.get("content_hash"),
							"inserted": inserted,
							"updated": updated,
						},
					)
					append_jsonl(pending_path, task.model_dump())
					stats.generated_tasks += 1
			_emit_progress(
				progress_callback,
				status="success",
				current=file_index,
				total=len(paths),
				current_step=str(path.name),
				current_dataset=str(pending_path.name),
			)
		return stats
