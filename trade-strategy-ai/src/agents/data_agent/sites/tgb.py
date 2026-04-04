from __future__ import annotations

from dataclasses import dataclass
import re

import httpx
from bs4 import BeautifulSoup

from src.agents.data_agent.sites.base import AuthProvider


@dataclass
class TgbCrawler:
    auth_provider: AuthProvider
    list_url: str
    source: str = "tgb"

    def fetch_article_list(self) -> list[dict[str, str]]:
        html = self._get_text(self.list_url)
        return self.parse_article_list(html)

    def fetch_article_detail(self, article_url: str) -> dict[str, str]:
        html = self._get_text(article_url)
        return self.parse_article_detail(html, article_url)

    def fetch_comments(self, article_url: str) -> list[dict[str, str]]:
        html = self._get_text(article_url)
        return self.parse_comments(html)

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
        comments: list[dict[str, str]] = []
        for node in soup.select(".comment-data"):
            author_node = node.select_one(".user-name")
            text_node = node.select_one(".comment-data-text")
            time_node = node.select_one(".pcyclspan")
            if author_node is None or text_node is None:
                continue
            comments.append(
                {
                    "author_name": author_node.get_text(" ", strip=True),
                    "raw_text": text_node.get_text(" ", strip=True),
                    "published_at": self._extract_datetime_text(
                        time_node.get_text(" ", strip=True) if time_node else node.get_text(" ", strip=True)
                    ),
                    "parent_comment_id": None,
                    "root_comment_id": None,
                    "reply_to_user": None,
                }
            )
        return comments

    def _get_text(self, url: str) -> str:
        with httpx.Client(headers=self.auth_provider.get_session_headers(), timeout=20.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text

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
