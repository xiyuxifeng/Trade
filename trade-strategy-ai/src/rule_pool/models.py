"""rule_pool SQLAlchemy ORM models - 规则池相关的数据库模型"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class RulePool(Base, TimestampMixin):
    """规则池表 - 存储从文章中提取的交易规则"""
    __tablename__ = 'rule_pool'

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    rule_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    source_article_ids: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    rule_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    instrument_focus: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default='mixed',
    )
    # extraction_layer 存储提取层的完整信息
    extraction_layer: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    mapping_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default='unmapped',
    )
    mapped_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    mapped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    initial_confidence: Mapped[float] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    validated_confidence: Mapped[float | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default='pending',
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    backtest_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    backtest_result: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    backtest_hits: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    backtest_misses: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    backtest_samples: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    used_in_prediction: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    prediction_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("rule_id", name="uq_rule_pool_rule_id"),
        Index('ix_rule_pool_rule_type', 'rule_type'),
        Index('ix_rule_pool_mapping_status', 'mapping_status'),
        Index('ix_rule_pool_review_status', 'review_status'),
        Index('ix_rule_pool_created_at', 'created_at'),
    )


class TradeSample(Base, TimestampMixin):
    """交易样本表 - 存储从文章或规则中提取的交易记录"""
    __tablename__ = 'trade_sample'

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    sample_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    article_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", ondelete="SET NULL"),
        nullable=True,
    )
    rule_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    symbol: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    side: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    entry_price: Mapped[float] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )
    exit_price: Mapped[float | None] = mapped_column(
        Numeric(18, 6),
        nullable=True,
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )
    entry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    exit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    pnl: Mapped[float | None] = mapped_column(
        Numeric(18, 4),
        nullable=True,
    )
    pnl_pct: Mapped[float | None] = mapped_column(
        Numeric(8, 4),
        nullable=True,
    )
    holding_period: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    tags: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("sample_id", name="uq_trade_sample_sample_id"),
        Index('ix_trade_sample_symbol', 'symbol'),
        Index('ix_trade_sample_entry_at', 'entry_at'),
        Index('ix_trade_sample_article_id', 'article_id'),
        Index('ix_trade_sample_rule_id', 'rule_id'),
    )


class ArticleClassification(Base, TimestampMixin):
    """文章分类表 - 存储文章的类型分类结果"""
    __tablename__ = 'article_classification'

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    article_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    classified_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    classified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reasons: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    # 使用 extra_metadata 而非 metadata，因 metadata 是 SQLAlchemy 保留字
    extra_metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    __table_args__ = (
        UniqueConstraint("article_id", name="uq_article_classification_article_id"),
        Index('ix_article_classification_article_id', 'article_id'),
        Index('ix_article_classification_article_type', 'article_type'),
        Index('ix_article_classification_confidence', 'confidence'),
    )
