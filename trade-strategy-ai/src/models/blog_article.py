from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class BlogArticle(TimestampMixin, Base):
    __tablename__ = "blog_articles"
    __table_args__ = (
        Index("ix_blog_articles_source_published_at", "source", "published_at"),
        Index("ix_blog_articles_author_published_at", "author_id", "published_at"),
        Index("ix_blog_articles_content_hash", "content_hash"),
        CheckConstraint("char_length(title) > 0", name="title_not_empty"),
        CheckConstraint("char_length(content_text) > 0", name="content_text_not_empty"),
        CheckConstraint("view_count >= 0", name="view_count_non_negative"),
        CheckConstraint("like_count >= 0", name="like_count_non_negative"),
        CheckConstraint("bookmark_count >= 0", name="bookmark_count_non_negative"),
        CheckConstraint("comment_count >= 0", name="comment_count_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_article_id: Mapped[str | None] = mapped_column(String(128))
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(100))
    author_id: Mapped[str | None] = mapped_column(String(128))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONVariant, default=list, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bookmark_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments_payload: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    metadata_record = relationship(
        "ArticleMetadata",
        back_populates="article",
        cascade="all, delete-orphan",
        uselist=False,
    )
