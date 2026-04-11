from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class CrawlState(TimestampMixin, Base):
    """增量抓取状态表 - 替代原有的 state.json 文件。

    用于持久化每个 (source, author_id) 的增量抓取状态，
    包括已见 URL、已见内容哈希、最后抓取位置等信息。
    """

    __tablename__ = "crawl_state"
    __table_args__ = (
        Index("ix_crawl_state_source_author", "source", "author_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    last_seen_article_url: Mapped[str | None] = mapped_column(Text)
    last_seen_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 已见的文章 URL 集合（用于快速去重）
    seen_urls: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    # 已见的内容哈希集合（用于内容去重）
    seen_hashes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    # 最后成功抓取的文章数量
    last_success_article_count: Mapped[int] = mapped_column(default=0, nullable=False)

    @classmethod
    def make_key(cls, source: str, author_id: str) -> tuple[str, str]:
        """返回唯一键元组。"""
        return (source, author_id)

    def to_index_payload(self) -> dict:
        """转换为 ExistingArticleIndex 期望的格式。"""
        from src.agents.data_agent.skills.crawl_blog import ExistingArticleIndex
        return ExistingArticleIndex(
            seen_urls=set(self.seen_urls),
            seen_hashes=set(self.seen_hashes),
            last_seen_article_url=self.last_seen_article_url,
            last_seen_published_at=self.last_seen_published_at.isoformat() if self.last_seen_published_at else None,
        )
