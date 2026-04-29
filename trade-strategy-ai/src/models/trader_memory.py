# src/models/trader_memory.py
"""TraderMemory 模型 - 交易员记忆数据

存储交易员的经验笔记、复盘结论等记忆数据，替代原来的 JSONL 文件存储。
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Float, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class TraderMemory(Base, TimestampMixin):
    """交易员记忆表

    存储交易员的成功/失败案例、复盘笔记、策略调整建议等。
    替代原来的 trader_memory.jsonl 文件存储。
    """

    __tablename__ = "trader_memory"
    __table_args__ = (
        UniqueConstraint(
            "trader_id", "memory_type", "as_of_date", "symbol", "title",
            name="uq_memory_ctx",
        ),
        Index("ix_memory_trader_id", "trader_id"),
        Index("ix_memory_trader_archived", "trader_id", "archived"),
        Index("ix_memory_trade_date", "as_of_date"),
        Index("ix_memory_symbol", "symbol"),
        Index("ix_memory_type", "memory_type"),
        Index("ix_memory_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    # 交易员 ID
    trader_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # 记忆类型
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # 关联交易日期
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 关联股票代码（可选）
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 记忆标题
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    # 记忆内容
    content: Mapped[str] = mapped_column(String(4096), nullable=False)
    # 来源
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manager")
    # 来源引用
    source_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # 标签列表
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    # 重要性
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    # 软删除标记
    archived: Mapped[bool] = mapped_column(nullable=False, default=False)
    # 归档时间
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 关联的交易想法 ID
    idea_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # 关联的策略版本 ID
    strategy_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 关联的 ranking 条目 ID
    ranking_entry_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # Topic 来源
    topic_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Raw topic IDs
    raw_topic_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # 盘后评估数据
    postmortem_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # 策略调整数据
    strategy_adjustment_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # 市场状态数据
    market_regime_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # 附加数据
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)