from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    source_url: str
    title: str
    author_name: str | None
    author_id: str | None
    published_at: datetime | None
    crawled_at: datetime
    content_text: str
    summary: str | None
    tags: list[str]
    content_hash: str | None
    view_count: int
    like_count: int
    bookmark_count: int
    comment_count: int


class ArticleFilter(BaseModel):
    author_id: str | None = None
    source: str | None = None
    trader_id: str | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None


class ArticleFilterOptionsResponse(BaseModel):
    author_ids: list[str]
    sources: list[str]
    trader_ids: list[str]
