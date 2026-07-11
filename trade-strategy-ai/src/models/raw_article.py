from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


JSONVariant = JSONB


class RawArticle(TimestampMixin, Base):
    """原始文章表 - 爬取阶段直接写入，用于支持增量抓取状态管理。

    对应原 crawl → articles.jsonl 的数据结构，保留原始爬取结果。
    后续由 clean → validate → store 流程消费并转换为 BlogArticle。
    """

    __tablename__ = "raw_articles"
    __table_args__ = (
        Index("ix_raw_articles_source_author", "source", "author_id"),
        Index("ix_raw_articles_crawled_at", "crawled_at"),
        Index("ix_raw_articles_content_hash", "content_hash"),
        Index("ix_raw_articles_is_processed", "is_processed"),
        CheckConstraint("char_length(source_url) > 0", name="raw_article_source_url_not_empty"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    site: Mapped[str] = mapped_column(String(100), nullable=False)
    trader_id: Mapped[str | None] = mapped_column(String(100))
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_article_id: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_html: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    # 增量抓取状态：标记是否已被 clean 流程处理
    is_processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def to_clean_payload(self) -> dict[str, Any]:
        """转换为 clean_task 期望的 payload 格式。"""
        return {
            "raw_article_id": str(self.id),
            "source": self.source,
            "site": self.site,
            "trader_id": self.trader_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "source_url": self.source_url,
            "source_article_id": self.source_article_id,
            "title": self.title,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "crawled_at": self.crawled_at.isoformat() if self.crawled_at else None,
            "content_text": self.content_text,
            "content_html": self.content_html,
            "content_hash": self.content_hash,
            "comment_count": self.comment_count,
            "comments": self.comments,
            "raw_payload": self.raw_payload,
        }
