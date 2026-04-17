from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class ArticleMetadata(TimestampMixin, Base):
    __tablename__ = "article_metadata"
    __table_args__ = (
        UniqueConstraint("article_id", "schema_version", name="uq_article_metadata_article_id_version"),
        Index("ix_article_metadata_processed_at", "processed_at"),
        CheckConstraint(
            "sentiment_score >= -1 AND sentiment_score <= 1",
            name="sentiment_score_range",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="confidence_score_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column("schema_version", String(20), nullable=False, default="v1")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_concepts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    trading_symbols: Mapped[list[str]] = mapped_column(JSONVariant, default=list, nullable=False)
    strategy_rules: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    preconditions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    comment_insights: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    raw_llm_output: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    # LLM 调用信息
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    article = relationship("BlogArticle", back_populates="metadata_record")
