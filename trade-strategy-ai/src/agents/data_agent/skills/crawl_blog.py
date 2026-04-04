from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
from pathlib import Path
import re
from typing import Any

from src.agents.data_agent.sites import AuthProvider, TgbCrawler
from src.common.config import AppConfig, CrawlSourceConfig
from src.common.utils import append_jsonl, ensure_dir, read_json, write_json


LOW_VALUE_COMMENTS = {"谢谢", "感谢", "打卡", "点赞", "666"}


@dataclass(frozen=True)
class ExistingArticleIndex:
    seen_urls: set[str]
    seen_hashes: set[str]
    last_seen_article_url: str | None
    last_seen_published_at: str | None


@dataclass(frozen=True)
class ClassifiedComment:
    raw_text: str
    clean_text: str
    is_author: bool
    is_filtered: bool
    filter_reasons: list[str]
    parent_comment_id: str | None
    root_comment_id: str | None
    reply_to_user: str | None


def classify_comment(
    *,
    raw_text: str,
    comment_author: str,
    article_author: str,
    parent_comment_id: str | None,
    root_comment_id: str | None,
    reply_to_user: str | None,
) -> ClassifiedComment:
    clean_text = _clean_comment_text(raw_text)
    filter_reasons: list[str] = []
    if clean_text in LOW_VALUE_COMMENTS or len(clean_text) <= 2:
        filter_reasons.append("low_value")

    return ClassifiedComment(
        raw_text=raw_text,
        clean_text=clean_text,
        is_author=comment_author.strip() == article_author.strip(),
        is_filtered=bool(filter_reasons),
        filter_reasons=filter_reasons,
        parent_comment_id=parent_comment_id,
        root_comment_id=root_comment_id,
        reply_to_user=reply_to_user,
    )


def should_stop_incremental_scan(
    *,
    source_url: str,
    content_hash: str | None,
    published_at: datetime | None,
    index: ExistingArticleIndex,
) -> bool:
    if source_url in index.seen_urls:
        return True
    if content_hash and content_hash in index.seen_hashes:
        return True
    if index.last_seen_article_url and source_url == index.last_seen_article_url:
        return True
    if published_at and index.last_seen_published_at:
        return published_at.isoformat() <= index.last_seen_published_at
    return False


def run_crawl(config: AppConfig, *, base_dir: Path, max_articles: int | None = None) -> list[str]:
    results: list[str] = []
    for source_cfg in config.crawl.sources:
        if not source_cfg.enabled:
            continue
        state_dir = base_dir / "data" / "processed" / "crawl" / source_cfg.source / source_cfg.author_id
        ensure_dir(state_dir)
        state_path = state_dir / "state.json"
        articles_path = state_dir / "articles.jsonl"
        state = load_state(state_path)
        index = ExistingArticleIndex(
            seen_urls=set(state.get("seen_urls", [])),
            seen_hashes=set(state.get("seen_hashes", [])),
            last_seen_article_url=state.get("last_seen_article_url"),
            last_seen_published_at=state.get("last_seen_published_at"),
        )

        if source_cfg.source != "tgb":
            raise ValueError(f"Unsupported source: {source_cfg.source}")

        auth = config.crawl.auth.get(source_cfg.site)
        throttle = config.crawl.throttling
        crawler = TgbCrawler(
            auth_provider=AuthProvider(site=source_cfg.site, cookie=auth.cookie if auth else None),
            list_url=source_cfg.list_url,
            min_interval=throttle.min_interval_seconds,
            max_interval=throttle.max_interval_seconds,
            backoff_seconds=tuple(throttle.backoff_seconds),
            max_retries=len(throttle.backoff_seconds),
        )
        count = crawl_source(
            source_cfg=source_cfg,
            crawler=crawler,
            index=index,
            articles_path=articles_path,
            state_path=state_path,
            max_articles=max_articles,
        )
        results.append(f"{source_cfg.source}:{source_cfg.author_id}:{count}")
    return results


def crawl_source(
    *,
    source_cfg: CrawlSourceConfig,
    crawler: TgbCrawler,
    index: ExistingArticleIndex,
    articles_path: Path,
    state_path: Path,
    max_articles: int | None,
) -> int:
    written = 0
    seen_urls = set(index.seen_urls)
    seen_hashes = set(index.seen_hashes)
    latest_url = index.last_seen_article_url
    latest_published_at = index.last_seen_published_at

    for item in crawler.fetch_article_list():
        detail = crawler.fetch_article_detail(item["source_url"])
        content_text = detail.get("content_text", "")
        content_hash = compute_content_hash(content_text) if content_text else None
        should_stop = should_stop_incremental_scan(
            source_url=item["source_url"],
            content_hash=content_hash,
            published_at=None,
            index=ExistingArticleIndex(
                seen_urls=seen_urls,
                seen_hashes=seen_hashes,
                last_seen_article_url=latest_url,
                last_seen_published_at=latest_published_at,
            ),
        )
        if should_stop:
            break

        comments = [
            asdict(
                classify_comment(
                    raw_text=comment.get("raw_text", ""),
                    comment_author=comment.get("author_name", ""),
                    article_author=source_cfg.author_name,
                    parent_comment_id=comment.get("parent_comment_id"),
                    root_comment_id=comment.get("root_comment_id"),
                    reply_to_user=comment.get("reply_to_user"),
                )
            )
            for comment in crawler.fetch_comments(item["source_url"])
        ]
        append_jsonl(
            articles_path,
            {
                "source": source_cfg.source,
                "site": source_cfg.site,
                "trader_id": source_cfg.trader_id,
                "author_id": source_cfg.author_id,
                "author_name": source_cfg.author_name,
                "source_url": item["source_url"],
                "source_article_id": item.get("source_article_id"),
                "title": detail.get("title") or item.get("title"),
                "published_at": item.get("published_at"),
                "crawled_at": datetime.utcnow().isoformat(),
                "content_text": content_text,
                "content_html": detail.get("content_html"),
                "content_hash": content_hash,
                "comment_count": len(comments),
                "comments": comments,
                "raw_payload": {"list_item": item, "detail": detail},
            },
        )
        written += 1
        seen_urls.add(item["source_url"])
        if content_hash:
            seen_hashes.add(content_hash)
        if latest_url is None:
            latest_url = item["source_url"]
        if latest_published_at is None:
            latest_published_at = item.get("published_at")
        if max_articles is not None and written >= max_articles:
            break

    write_json(
        state_path,
        {
            "last_seen_article_url": latest_url,
            "last_seen_published_at": latest_published_at,
            "last_success_article_count": written,
            "seen_urls": sorted(seen_urls),
            "seen_hashes": sorted(seen_hashes),
        },
    )
    return written


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def compute_content_hash(content_text: str) -> str:
    return hashlib.sha256(content_text.encode("utf-8")).hexdigest()


def _clean_comment_text(raw_text: str) -> str:
    no_emoji_markers = re.sub(r"\[.*?\]", "", raw_text)
    no_special = re.sub(r"[^\w\u4e00-\u9fff]+", " ", no_emoji_markers, flags=re.UNICODE)
    return re.sub(r"\s+", " ", no_special).strip()
