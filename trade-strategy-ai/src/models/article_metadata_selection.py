from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class ArticleMetadataSelection(TimestampMixin, Base):
    """文章元数据版本选择记录。

    说明：
    - 同一篇文章只保留一条当前生效记录。
    - `candidate_versions_json` 保留候选版本快照，供 UI 对比和人工确认。
    - `selected_schema_version` 记录当前回测/策略生成应使用的版本。
    """

    __tablename__ = "article_metadata_selections"
    __table_args__ = (
        UniqueConstraint("article_id", name="uq_article_metadata_selections_article_id"),
        Index("ix_article_metadata_selections_article_id", "article_id"),
        Index("ix_article_metadata_selections_selected_schema_version", "selected_schema_version"),
        Index("ix_article_metadata_selections_selected_by_created_at", "selected_by", "created_at"),
        Index("ix_article_metadata_selections_selection_mode", "selection_mode", "selected_at"),
    )

    selection_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    article_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    selected_schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    recommended_schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    selection_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")
    selection_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recommended_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    selection_reason: Mapped[str | None] = mapped_column(String(255))
    recommended_reason: Mapped[str | None] = mapped_column(String(255))
    selected_by: Mapped[str | None] = mapped_column(String(64))
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    candidate_versions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """返回可直接给 Web 使用的字典。"""
        return {
            "selection_id": self.selection_id,
            "article_id": str(self.article_id),
            "selected_schema_version": self.selected_schema_version,
            "recommended_schema_version": self.recommended_schema_version,
            "selection_mode": self.selection_mode,
            "selection_score": float(self.selection_score) if self.selection_score is not None else None,
            "recommended_score": float(self.recommended_score) if self.recommended_score is not None else None,
            "selection_reason": self.selection_reason,
            "recommended_reason": self.recommended_reason,
            "selected_by": self.selected_by,
            "selected_at": self.selected_at.isoformat() if self.selected_at else None,
            "candidate_versions_json": self.candidate_versions_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
