from __future__ import annotations

from dataclasses import dataclass
import random
import re
import time
from typing import Callable

import httpx
from bs4 import BeautifulSoup

from src.agents.data_agent.sites.base import AuthProvider


def _default_backoff(seconds: list[int]) -> Callable[[int], float]:
    def backoff(attempt: int) -> float:
        if attempt < len(seconds):
            return seconds[attempt]
        return seconds[-1]

    return backoff


@dataclass
class TgbCrawler:
    auth_provider: AuthProvider
    list_url: str
    source: str = "tgb"
    min_interval: float = 1.0
    max_interval: float = 2.0
    backoff_seconds: tuple[int, ...] = (5, 15, 30)
    max_retries: int = 3

    def _throttle(self) -> None:
        delay = random.uniform(self.min_interval, self.max_interval)
        time.sleep(delay)

    def _get_text(self, url: str) -> str:
        headers = self.auth_provider.get_session_headers()
        headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        })

        with httpx.Client(headers=headers, timeout=20.0, follow_redirects=True) as client:
            last_exc: Exception | None = None
            for attempt in range(self.max_retries):
                try:
                    response = client.get(url)
                    if response.status_code in {403, 429}:
                        backoff_secs = _default_backoff(list(self.backoff_seconds))(attempt)
                        time.sleep(backoff_secs)
                        last_exc = httpx.HTTPStatusError(
                            f"HTTP {response.status_code}, backing off {backoff_secs}s",
                            request=response.request,
                            response=response,
                        )
                        continue
                    response.raise_for_status()
                    if not self.auth_provider.is_authenticated(response.text):
                        raise httpx.HTTPStatusError(
                            "Login/verification page detected",
                            request=response.request,
                            response=response,
                        )
                    return response.text
                except httpx.HTTPStatusError:
                    raise
                except httpx.RequestError as exc:
                    last_exc = exc
                    if attempt < self.max_retries - 1:
                        backoff_secs = _default_backoff(list(self.backoff_seconds))(attempt)
                        time.sleep(backoff_secs)
            raise last_exc or RuntimeError(f"Failed to fetch {url} after {self.max_retries} attempts")

    def fetch_article_list(self) -> list[dict[str, str]]:
        articles: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        page = 1
        max_pages = 10  # safety limit
        while page <= max_pages:
            self._throttle()
            url = f"{self.list_url}&page={page}" if "?" in self.list_url else f"{self.list_url}?page={page}"
            html = self._get_text(url)
            page_articles = self.parse_article_list(html)
            if not page_articles:
                break
            # Stop if this page is identical to previous (no new articles)
            page_urls = {a["source_url"] for a in page_articles}
            if page_urls.issubset(seen_urls):
                break
            for article in page_articles:
                if article["source_url"] not in seen_urls:
                    articles.append(article)
                    seen_urls.add(article["source_url"])
            # Stop if page returned fewer than a full page (likely last page)
            if len(page_articles) < 100:
                break
            page += 1
        return articles

    def fetch_article_detail(self, article_url: str) -> dict[str, str]:
        self._throttle()
        html = self._get_text(article_url)
        return self.parse_article_detail(html, article_url)

    def fetch_comments(self, article_url: str) -> list[dict[str, str]]:
        all_comments: list[dict[str, str]] = []
        seen_ids: set[str] = set()
        page = 1
        max_pages = 20  # safety limit
        base_slug = article_url.rstrip("/").rsplit("/", 1)[-1]

        while page <= max_pages:
            self._throttle()
            page_url = f"{article_url.rstrip('/')}-{page}" if page > 1 else article_url
            html = self._get_text(page_url)
            page_comments = self.parse_comments(html)
            if not page_comments:
                break
            new_count = 0
            for comment in page_comments:
                cid = comment.get("comment_id") or comment.get("raw_text", "")[:50]
                if cid not in seen_ids:
                    all_comments.append(comment)
                    seen_ids.add(cid)
                    new_count += 1
            # Stop if no new comments on this page (reached end)
            if new_count == 0:
                break
            # Stop if fewer comments than a typical page (likely last page)
            if len(page_comments) < 20:
                break
            # Detect total pages from pagination info
            total_pages = self._detect_comment_total_pages(html)
            if total_pages and page >= total_pages:
                break
            page += 1
        return all_comments

    def _detect_comment_total_pages(self, html: str) -> int | None:
        m = re.search(r"共\s*(\d+)\s*/\s*(\d+)\s*页", html)
        if m:
            total = int(m.group(2))
            return total if total <= 100 else None  # sanity cap
        return None

    def parse_article_list(self, html: str) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        articles: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for link in soup.select("a[href]"):
            href = link.get("href")
            if not href:
                continue
            normalized_href = href.lstrip("/")
            if not normalized_href.startswith("a/"):
                continue
            article_url = href if href.startswith("http") else f"https://www.tgb.cn/{normalized_href}"
            if article_url in seen_urls:
                continue
            title = link.get_text(" ", strip=True)
            if not title:
                continue
            seen_urls.add(article_url)
            articles.append(
                {
                    "source_url": article_url,
                    "source_article_id": article_url.rstrip("/").split("/")[-1],
                    "title": title,
                }
            )
        return articles

    def parse_article_detail(self, html: str, article_url: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        title_node = soup.select_one("h1")
        content_container = soup.select_one(".p_wenz") or soup.select_one(".p_coten") or soup.body
        content_text = content_container.get_text("\n", strip=True) if content_container else ""
        content_html = str(content_container) if content_container else ""
        return {
            "source_url": article_url,
            "source_article_id": article_url.rstrip("/").split("/")[-1],
            "title": title_node.get_text(" ", strip=True) if title_node else "",
            "content_text": content_text,
            "content_html": content_html,
        }

    def parse_comments(self, html: str) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        comments = self._parse_comments_from_comment_data_blocks(soup)
        if comments:
            return comments

        comments: list[dict[str, str]] = []
        for node in soup.select(".comment"):
            author_node = node.select_one("a")
            text_node = node.select_one("div")
            time_text = self._extract_datetime_text(node.get_text(" ", strip=True))
            comments.append(
                {
                    "comment_id": node.get("id"),
                    "author_name": author_node.get_text(" ", strip=True) if author_node else "",
                    "raw_text": text_node.get_text(" ", strip=True) if text_node else "",
                    "published_at": time_text,
                    "parent_comment_id": node.get("data-parent-id"),
                    "root_comment_id": node.get("data-root-id"),
                    "reply_to_user": node.get("data-reply-user"),
                }
            )
        if comments:
            return comments
        return self._parse_comments_from_text_blocks(soup)

    def _parse_comments_from_comment_data_blocks(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        raw_nodes: list[tuple[dict[str, str], BeautifulSoup]] = []
        for node in soup.select(".comment-data"):
            comment_id = node.get("id")
            author_node = node.select_one(".user-name")
            text_node = node.select_one(".comment-data-text")
            time_node = node.select_one(".pcyclspan")
            if author_node is None:
                continue
            raw_text = self._extract_comment_text(node, text_node)
            published_at = self._extract_datetime_text(
                time_node.get_text(" ", strip=True) if time_node else raw_text
            )
            raw_nodes.append(
                (
                    {
                        "comment_id": comment_id,
                        "author_name": author_node.get_text(" ", strip=True),
                        "raw_text": raw_text,
                        "published_at": published_at,
                        "author_id": node.get("ustr") or self._extract_author_id_from_href(
                            author_node.get("href") or ""
                        ),
                        "quote_author_name": None,
                        "quote_author_id": None,
                    },
                    node,
                )
            )

        # Build author_id → comment_id mapping for reply resolution
        author_to_comment: dict[str, str] = {}
        for data, _ in raw_nodes:
            author_id = data["author_id"]
            if author_id:
                author_to_comment[author_id] = data["comment_id"]

        # Resolve quote/reply structure
        comments: list[dict[str, str]] = []
        for data, node in raw_nodes:
            quote_node = node.select_one(".comment-data-quote")
            reply_to_user: str | None = None
            parent_comment_id: str | None = None
            if quote_node:
                quote_author_el = quote_node.select_one(".user-name")
                reply_to_user = quote_author_el.get_text(" ", strip=True) if quote_author_el else None
                quote_href = quote_author_el.get("href", "") if quote_author_el else ""
                quote_author_id = self._extract_author_id_from_href(quote_href)
                if quote_author_id and quote_author_id in author_to_comment:
                    parent_comment_id = author_to_comment[quote_author_id]
            comments.append(
                {
                    "comment_id": data["comment_id"],
                    "author_name": data["author_name"],
                    "raw_text": data["raw_text"],
                    "published_at": data["published_at"],
                    "parent_comment_id": parent_comment_id,
                    "root_comment_id": parent_comment_id,  # flat; root==parent for direct replies
                    "reply_to_user": reply_to_user,
                }
            )
        return comments

    def _extract_comment_text(self, node: BeautifulSoup, text_node: BeautifulSoup | None) -> str:
        text = text_node.get_text(" ", strip=True) if text_node else ""
        if text:
            return text
        # Walk direct children of .comment-data, skipping excluded/navigation elements
        exclude_classes = {"comment-data-quote", "comment-data-button", "comment-nav", "comment-data-left", "comment-data-right", "comment-data-user", "comment-data-user"}
        skip_tags = {"a", "span"}
        skip_classes = {"user-name", "pcyclspan"}
        parts: list[str] = []

        def _walk(el: BeautifulSoup) -> None:
            for child in el.children:
                if isinstance(child, str):
                    stripped = child.strip()
                    if stripped:
                        parts.append(stripped)
                elif hasattr(child, "name") and child.name:
                    cls = set(child.get("class", []))
                    if cls & exclude_classes:
                        continue
                    if child.name == "img":
                        alt = child.get("alt", "")
                        if alt:
                            parts.append(alt)
                    elif child.name in skip_tags and cls & skip_classes:
                        continue
                    else:
                        _walk(child)

        _walk(node)
        return " ".join(parts)

    def _extract_author_id_from_href(self, href: str) -> str | None:
        m = re.search(r"/blog/(\d+)", href)
        return m.group(1) if m else None


    def _extract_datetime_text(self, text: str) -> str | None:
        match = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", text)
        if not match:
            return None
        return match.group(0)

    def _parse_comments_from_text_blocks(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        lines = [text.strip() for text in soup.stripped_strings if text.strip()]
        comments: list[dict[str, str]] = []
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            timestamp = self._extract_datetime_text(next_line)
            if timestamp is None:
                idx += 1
                continue

            author_name = line
            body_parts: list[str] = []
            idx += 2
            while idx < len(lines):
                current = lines[idx]
                if current.endswith("· 淘股吧"):
                    break
                body_parts.append(current)
                idx += 1

            reply_to_user = self._extract_reply_to_user(body_parts)
            filtered_parts = [part for part in body_parts if part not in {"只看TA", "楼主"}]
            if reply_to_user and filtered_parts:
                filtered_parts = filtered_parts[1:]
            body_text = " ".join(filtered_parts)
            comments.append(
                {
                    "comment_id": f"text_block_{len(comments)}",
                    "author_name": author_name,
                    "raw_text": body_text.strip(),
                    "published_at": timestamp,
                    "parent_comment_id": None,
                    "root_comment_id": None,
                    "reply_to_user": reply_to_user,
                }
            )
            idx += 1
        return comments

    def _extract_reply_to_user(self, body_parts: list[str]) -> str | None:
        if not body_parts:
            return None
        first = body_parts[0]
        match = re.match(r"^(?P<user>\S+)\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$", first)
        if not match:
            return None
        return match.group("user")
