"""Ranking Entry ORM 模型。

将每笔交易的想法和对应的 ranking 结果持久化到数据库。
支持嵌套分组（trader → strategy_version → symbol）和版本淘汰（is_latest）。

NTL-S5-004
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Boolean, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class RankingEntryRecord(TimestampMixin, Base):
    """ranking 条目持久化模型。

    存储结构：trade_date + trader_id + strategy_version_id + symbol 为唯一键，
    通过 is_latest 标记当前有效条目，历史条目保留用于追溯。

    索引设计：
      - trade_date：按日期查询
      - (trader_id, strategy_version_id)：嵌套分组查询
      - (trade_date, strategy_version_id, symbol) 唯一约束：防止并发重复写入
    """

    __tablename__ = "ranking_entries"
    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "strategy_version_id",
            "symbol",
            name="uq_ranking_entry",
        ),
        Index("ix_ranking_trader_version", "trader_id", "strategy_version_id"),
        Index("ix_ranking_trade_date", "trade_date"),
    )

    # 主键
    entry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # 分组键
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    trader_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    strategy_version_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)

    # 排序指标（可空，表示尚无评分）
    return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    mfe: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 排名（generate_ranking 时批量回填）
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 版本状态：True = 该 (trade_date, version, symbol) 组合的最新条目
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 来源追踪
    idea_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    attribution_source: Mapped[str] = mapped_column(String(32), nullable=False, default="auto")

    # 扩展字段
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def to_dict(self) -> dict:
        """转为字典。"""
        return {
            "entry_id": str(self.entry_id),
            "trade_date": self.trade_date,
            "trader_id": self.trader_id,
            "strategy_version_id": self.strategy_version_id,
            "symbol": self.symbol,
            "return_pct": self.return_pct,
            "mfe": self.mfe,
            "mae": self.mae,
            "composite_score": self.composite_score,
            "rank": self.rank,
            "is_latest": self.is_latest,
            "idea_id": str(self.idea_id) if self.idea_id else None,
            "attribution_source": self.attribution_source,
            "extra": self.extra,
        }