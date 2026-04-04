from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AuthProvider:
    site: str
    cookie: str | None

    def get_session_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        return headers

    def is_authenticated(self, text: str) -> bool:
        return "登录" not in text and "验证码" not in text


class SiteCrawler(Protocol):
    source: str

    def fetch_article_list(self) -> list[dict[str, str]]:
        ...

    def fetch_article_detail(self, article_url: str) -> dict[str, str]:
        ...

    def fetch_comments(self, article_url: str) -> list[dict[str, str]]:
        ...
