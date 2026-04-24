"""EvidencePack ORM 模型。

将盘后评估证据包持久化到数据库，供归因分析和 ranking 使用。

存储方式：pack_data JSONB 列存储完整 EvidencePack 结构（trade_idea / signal_context /
market_data / strategy_version_snapshot），外键列保留关键索引字段。

NTL-S5-001 / TD-003-b
"""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import Date, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class EvidencePackRecord(TimestampMixin, Base):
    """盘后评估证据包持久化记录。

    完整 EvidencePack 数据存储在 pack_data JSONB 列中，
    外键列（idea_id/trader_id/trade_date/symbol）用于高效索引和查询。
    """

    __tablename__ = "evidence_packs"
    __table_args__ = (
        UniqueConstraint(
            "idea_id",
            name="uq_evidence_packs_idea_id",
        ),
        Index("ix_evidence_packs_trader_date", "trader_id", "trade_date"),
        Index("ix_evidence_packs_symbol", "symbol"),
        Index("ix_evidence_packs_strategy_version_id", "strategy_version_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # 外部引用键（索引用）
    idea_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, unique=True)
    trader_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trade_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # 策略版本追溯
    strategy_version_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # 完整证据包（JSONB）
    # 包含: trade_idea / signal_context / market_data / strategy_version_snapshot / created_at / extra
    pack_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def to_dict(self) -> dict:
        """将 ORM 记录转为字典（主要用于跨接口传输）。"""
        return {
            "id": str(self.id),
            "idea_id": str(self.idea_id) if self.idea_id else None,
            "trader_id": self.trader_id,
            "trade_date": str(self.trade_date) if self.trade_date else None,
            "symbol": self.symbol,
            "strategy_version_id": self.strategy_version_id,
            "pack_data": self.pack_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_pack_dict(
        cls,
        pack_dict: dict,
        trader_id: str | None = None,
        trade_date: date | None = None,
        symbol: str | None = None,
    ) -> "EvidencePackRecord":
        """从 EvidencePack.to_dict() 结果创建 ORM 记录。

        Args:
            pack_dict: EvidencePack.to_dict() 的输出
            trader_id: 交易员 ID（可选，从 pack_dict.trade_idea.trader_id 提取）
            trade_date: 交易日期（可选，从 pack_dict.trade_date 提取）
            symbol: 标的代码（可选，从 pack_dict.trade_idea.symbol 提取）
        """
        from src.evaluation.evidence_pack import EvidencePack

        idea_id = pack_dict.get("idea_id")
        if idea_id and isinstance(idea_id, str):
            idea_id = UUID(idea_id)

        sv_id = pack_dict.get("strategy_version_id")

        return cls(
            idea_id=idea_id,
            trader_id=trader_id,
            trade_date=trade_date,
            symbol=symbol,
            strategy_version_id=sv_id,
            pack_data=pack_dict,
        )
