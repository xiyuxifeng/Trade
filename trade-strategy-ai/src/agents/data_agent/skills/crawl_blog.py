from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.data_agent.sites import AuthProvider, TgbCrawler
from src.common.config import AppConfig, CrawlSourceConfig
from src.common.utils import append_jsonl, ensure_dir, read_json, write_json
from src.db.session import session_scope
from src.models.raw_article import RawArticle
from src.models.crawl_state import CrawlState


LOW_VALUE_COMMENTS = {"谢谢", "感谢", "打卡", "点赞", "666", "先赞后看"}


@dataclass(frozen=True)
class ExistingArticleIndex:
    """Incremental crawl state used to stop when old content is reached."""

    seen_urls: set[str]
    seen_hashes: set[str]
    last_seen_article_url: str | None
    last_seen_published_at: str | None


@dataclass(frozen=True)
class ClassifiedComment:
    """Normalized comment record with filter metadata."""

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
    """Clean and classify a single comment before persistence."""

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
    """Stop a crawl once we hit a previously seen article or hash."""

    if source_url in index.seen_urls:
        return True
    if content_hash and content_hash in index.seen_hashes:
        return True
    if index.last_seen_article_url and source_url == index.last_seen_article_url:
        return True
    if published_at and index.last_seen_published_at:
        return published_at.isoformat() <= index.last_seen_published_at
    return False


def run_crawl(config: AppConfig, *, base_dir: Path, max_articles: int | None = None, use_db: bool = False) -> list[str]:
    """Run the configured crawl sources.

    Args:
        config: 应用配置
        base_dir: 项目根目录
        max_articles: 每个作者最多抓取文章数
        use_db: 是否直接写入数据库（raw_articles 表），默认 False（写入文件）
    """
    if use_db:
        import asyncio
        return asyncio.run(run_crawl_to_db(config, max_articles=max_articles))

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
            author_id=source_cfg.author_id,
            min_interval=throttle.min_interval_seconds,
            max_interval=throttle.max_interval_seconds,
            backoff_seconds=tuple(throttle.backoff_seconds),
            max_retries=len(throttle.backoff_seconds),
            render_js=source_cfg.render_js,
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
    """Crawl one source and persist its article records."""

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
                "crawled_at": datetime.now(UTC).isoformat(),
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


# ============ 数据库存储支持 ============


async def load_crawl_state_from_db(session: AsyncSession, source: str, author_id: str) -> dict[str, Any]:
    """从数据库加载增量抓取状态。"""
    result = await session.execute(
        select(CrawlState).where(CrawlState.source == source, CrawlState.author_id == author_id)
    )
    state = result.scalar_one_or_none()
    if state is None:
        return {}
    return {
        "seen_urls": state.seen_urls or [],
        "seen_hashes": state.seen_hashes or [],
        "last_seen_article_url": state.last_seen_article_url,
        "last_seen_published_at": state.last_seen_published_at.isoformat() if state.last_seen_published_at else None,
    }


async def save_crawl_state_to_db(
    session: AsyncSession,
    source: str,
    author_id: str,
    seen_urls: set[str],
    seen_hashes: set[str],
    latest_url: str | None,
    latest_published_at: str | None,
    article_count: int,
) -> None:
    """保存增量抓取状态到数据库。"""
    result = await session.execute(
        select(CrawlState).where(CrawlState.source == source, CrawlState.author_id == author_id)
    )
    state = result.scalar_one_or_none()

    if state is None:
        state = CrawlState(
            source=source,
            author_id=author_id,
            seen_urls=sorted(seen_urls),
            seen_hashes=sorted(seen_hashes),
            last_seen_article_url=latest_url,
            last_seen_published_at=datetime.fromisoformat(latest_published_at) if latest_published_at else None,
            last_success_article_count=article_count,
        )
        session.add(state)
    else:
        state.seen_urls = sorted(seen_urls)
        state.seen_hashes = sorted(seen_hashes)
        state.last_seen_article_url = latest_url
        state.last_seen_published_at = datetime.fromisoformat(latest_published_at) if latest_published_at else None
        state.last_success_article_count = article_count
    await session.flush()


async def upsert_raw_article(
    session: AsyncSession,
    source: str,
    site: str,
    trader_id: str | None,
    author_id: str,
    author_name: str | None,
    source_url: str,
    source_article_id: str | None,
    title: str,
    published_at: str | None,
    crawled_at: str,
    content_text: str,
    content_html: str | None,
    content_hash: str | None,
    comment_count: int,
    comments: list[dict[str, Any]],
    raw_payload: dict[str, Any],
) -> bool:
    """写入或更新 RawArticle，返回是否是新插入。"""
    # 检查是否已存在
    result = await session.execute(
        select(RawArticle).where(RawArticle.source_url == source_url)
    )
    existing = result.scalar_one_or_none()

    parsed_crawled_at = datetime.fromisoformat(crawled_at) if crawled_at else datetime.now(UTC)
    if parsed_crawled_at.tzinfo is None:
        parsed_crawled_at = parsed_crawled_at.replace(tzinfo=UTC)

    parsed_published_at = None
    if published_at:
        try:
            parsed_published_at = datetime.fromisoformat(published_at)
            if parsed_published_at.tzinfo is None:
                parsed_published_at = parsed_published_at.replace(tzinfo=UTC)
        except ValueError:
            parsed_published_at = None

    if existing is None:
        article = RawArticle(
            source=source,
            site=site,
            trader_id=trader_id,
            author_id=author_id,
            author_name=author_name,
            source_url=source_url,
            source_article_id=source_article_id,
            title=title,
            published_at=parsed_published_at,
            crawled_at=parsed_crawled_at,
            content_text=content_text,
            content_html=content_html,
            content_hash=content_hash,
            comment_count=comment_count,
            comments=comments,
            raw_payload=raw_payload,
        )
        session.add(article)
        await session.flush()
        return True
    else:
        # 更新已存在的记录（评论可能新增）
        existing.title = title
        existing.published_at = parsed_published_at
        existing.crawled_at = parsed_crawled_at
        existing.content_text = content_text
        existing.content_html = content_html
        existing.content_hash = content_hash
        existing.comment_count = comment_count
        existing.comments = comments
        existing.raw_payload = raw_payload
        await session.flush()
        return False


async def crawl_source_to_db(
    *,
    source_cfg: CrawlSourceConfig,
    crawler: TgbCrawler,
    index: ExistingArticleIndex,
    max_articles: int | None,
) -> int:
    """爬取并直接写入数据库。"""
    written = 0
    seen_urls = set(index.seen_urls)
    seen_hashes = set(index.seen_hashes)
    latest_url = index.last_seen_article_url
    latest_published_at = index.last_seen_published_at

    async with session_scope() as session:
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

            await upsert_raw_article(
                session=session,
                source=source_cfg.source,
                site=source_cfg.site,
                trader_id=source_cfg.trader_id,
                author_id=source_cfg.author_id,
                author_name=source_cfg.author_name,
                source_url=item["source_url"],
                source_article_id=item.get("source_article_id"),
                title=detail.get("title") or item.get("title", ""),
                published_at=item.get("published_at"),
                crawled_at=datetime.now(UTC).isoformat(),
                content_text=content_text,
                content_html=detail.get("content_html"),
                content_hash=content_hash,
                comment_count=len(comments),
                comments=comments,
                raw_payload={"list_item": item, "detail": detail},
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

        # 保存状态到数据库
        await save_crawl_state_to_db(
            session=session,
            source=source_cfg.source,
            author_id=source_cfg.author_id,
            seen_urls=seen_urls,
            seen_hashes=seen_hashes,
            latest_url=latest_url,
            latest_published_at=latest_published_at,
            article_count=written,
        )

    return written


async def run_crawl_to_db(config: AppConfig, *, max_articles: int | None = None) -> list[str]:
    """Run the configured crawl sources and write directly to database."""
    results: list[str] = []
    for source_cfg in config.crawl.sources:
        if not source_cfg.enabled:
            continue

        if source_cfg.source != "tgb":
            raise ValueError(f"Unsupported source: {source_cfg.source}")

        # 从数据库加载状态
        async with session_scope() as session:
            state_dict = await load_crawl_state_from_db(session, source_cfg.source, source_cfg.author_id)

        index = ExistingArticleIndex(
            seen_urls=set(state_dict.get("seen_urls", [])),
            seen_hashes=set(state_dict.get("seen_hashes", [])),
            last_seen_article_url=state_dict.get("last_seen_article_url"),
            last_seen_published_at=state_dict.get("last_seen_published_at"),
        )

        auth = config.crawl.auth.get(source_cfg.site)
        throttle = config.crawl.throttling
        crawler = TgbCrawler(
            auth_provider=AuthProvider(site=source_cfg.site, cookie=auth.cookie if auth else None),
            list_url=source_cfg.list_url,
            author_id=source_cfg.author_id,
            min_interval=throttle.min_interval_seconds,
            max_interval=throttle.max_interval_seconds,
            backoff_seconds=tuple(throttle.backoff_seconds),
            max_retries=len(throttle.backoff_seconds),
            render_js=source_cfg.render_js,
        )

        count = await crawl_source_to_db(
            source_cfg=source_cfg,
            crawler=crawler,
            index=index,
            max_articles=max_articles,
        )
        results.append(f"{source_cfg.source}:{source_cfg.author_id}:{count}")
    return results


def _clean_comment_text(raw_text: str) -> str:
    no_emoji_markers = re.sub(r"\[.*?\]", "", raw_text)
    no_special = re.sub(r"[^\w\u4e00-\u9fff]+", " ", no_emoji_markers, flags=re.UNICODE)
    return re.sub(r"\s+", " ", no_special).strip()
