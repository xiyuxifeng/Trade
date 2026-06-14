"""Signal ORM 模型"""
from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from src.models.base import Base


class Signal(Base):
    """交易信号 ORM"""
    __tablename__ = 'signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL, HOLD, REJECTED
    confidence = Column(Float, nullable=True)
    triggered_rules = Column(JSONB, nullable=True)
    synthesis_mode = Column(String(20), nullable=True)
    entry_price = Column(JSONB, nullable=True)
    position_size = Column(JSONB, nullable=True)
    stop_loss = Column(JSONB, nullable=True)
    take_profit = Column(JSONB, nullable=True)
    trader_id = Column(String(64), nullable=True)
    strategy_version_id = Column(String(128), nullable=True)
    source_topic_ids = Column(JSONB, nullable=True)
    evidence_refs = Column(JSONB, nullable=True)
    decision_mode = Column(String(32), nullable=True)
    evaluation_result_id = Column(String(128), nullable=True)
    rejected = Column(Boolean, default=False)
    rejection_reason = Column(Text, nullable=True)
    degraded = Column(Boolean, default=False)
    degradation_reason = Column(Text, nullable=True)
    version = Column(String(10), nullable=True)
    signal_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_signals_created_at', 'created_at'),
        Index('idx_signals_signal_id', 'signal_id'),
        Index('idx_signals_symbol', 'symbol'),
    )

    def to_dict(self) -> dict:
        return {
            "signal_id": str(self.signal_id),
            "symbol": self.symbol,
            "side": self.side,
            "confidence": self.confidence,
            "triggered_rules": self.triggered_rules,
            "synthesis_mode": self.synthesis_mode,
            "entry_price": self.entry_price,
            "position_size": self.position_size,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "trader_id": self.trader_id,
            "strategy_version_id": self.strategy_version_id,
            "source_topic_ids": self.source_topic_ids,
            "evidence_refs": self.evidence_refs,
            "decision_mode": self.decision_mode,
            "evaluation_result_id": self.evaluation_result_id,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
            "degraded": self.degraded,
            "degradation_reason": self.degradation_reason,
            "version": self.version,
            "metadata": self.signal_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
