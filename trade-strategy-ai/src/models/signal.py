"""Signal ORM 模型"""
from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID, JSONB
from src.models.base import Base
from src.domain.enums import SignalState
from src.models.stage2_canonical import _enum


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
    legacy_strategy_version_id = Column(String(128), nullable=True)
    strategy_version_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("strategy_versions.strategy_version_id", name="fk_signals_strategy_version", ondelete="SET NULL"),
        nullable=True,
    )
    trading_day_plan_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("trading_day_plans.trading_day_plan_id", name="fk_signals_plan", ondelete="SET NULL"),
        nullable=True,
    )
    daily_strategy_instance_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "daily_strategy_instances.daily_strategy_instance_id",
            name="fk_signals_daily_instance",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    rule_version_ids = Column(ARRAY(PGUUID(as_uuid=True)), nullable=False, default=list)
    signal_state = Column(_enum(SignalState, "signal_state"), nullable=False, default=SignalState.proposed)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    available_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
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
            "legacy_strategy_version_id": self.legacy_strategy_version_id,
            "trading_day_plan_id": self.trading_day_plan_id,
            "daily_strategy_instance_id": self.daily_strategy_instance_id,
            "rule_version_ids": self.rule_version_ids,
            "signal_state": getattr(self.signal_state, "value", self.signal_state),
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
