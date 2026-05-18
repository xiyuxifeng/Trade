"""rule_pool Pydantic schemas - 规则池相关的数据验证模型"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.backtest.schemas import RegimeBacktestMetric


class RuleSourceType(StrEnum):
    """规则来源类型"""
    STANDALONE = "standalone"    # 规则型文章提取
    DERIVED = "derived"          # 交易记录反推
    EXPERIENCE = "experience"    # 经验规则


class MappingStatus(StrEnum):
    """映射状态"""
    UNMAPPED = "unmapped"
    PENDING = "pending"
    MAPPED = "mapped"
    UNMAPPABLE = "unmappable"


class ReviewStatus(StrEnum):
    """审核状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ArticleType(StrEnum):
    """文章类型"""
    RULE = "rule"
    RECORD = "record"
    CONCEPT = "concept"
    MIXED = "mixed"
    NOISE = "noise"


class RuleBacktestResult(BaseModel):
    """回测结果"""
    run_id: str
    run_at: datetime
    start_date: date
    end_date: date
    rule_id: str | None = None
    regime_version: str | None = None
    source_feature_version: str | None = None
    total_trades: int = 0
    hit_trades: int = 0
    miss_trades: int = 0
    hit_rate: float = 0.0
    avg_return: float = 0.0
    avg_win_return: float | None = None
    avg_loss_return: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    sample_count: int = 0
    regime_metrics: list[RegimeBacktestMetric] = Field(default_factory=list)


class RawCondition(BaseModel):
    """提取层的原始条件"""
    raw_text: str = ""
    indicators: list[str] = Field(default_factory=list)
    description: str = ""


class ExtractionLayer(BaseModel):
    """提取层"""
    rule_type: str
    instrument_focus: str = "mixed"
    raw_condition: RawCondition = Field(default_factory=RawCondition)
    mapped_condition: dict[str, Any] | None = None
    action: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    quoted_text: str | None = None


class RulePoolItem(BaseModel):
    """规则池条目"""
    id: UUID | None = None
    rule_id: str
    source_article_ids: list[str]
    source_type: RuleSourceType
    rule_type: str
    instrument_focus: str = "mixed"
    extraction_layer: ExtractionLayer
    mapping_status: MappingStatus = MappingStatus.UNMAPPED
    mapped_by: str | None = None
    mapped_at: datetime | None = None
    initial_confidence: float
    validated_confidence: float | None = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    backtest_triggered_at: datetime | None = None
    backtest_result: RuleBacktestResult | None = None
    backtest_hits: int = 0
    backtest_misses: int = 0
    backtest_samples: int = 0
    used_in_prediction: bool = False
    prediction_count: int = 0
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TradeSampleItem(BaseModel):
    """交易样本条目"""
    id: UUID | None = None
    sample_id: str
    article_id: str | None = None
    rule_id: str | None = None
    symbol: str
    side: str  # BUY, SELL
    entry_price: float
    exit_price: float | None = None
    quantity: float
    entry_at: datetime
    exit_at: datetime | None = None
    pnl: float | None = None
    pnl_pct: float | None = None
    holding_period: int | None = None  # 持仓周期（天）
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime | None = None


class ArticleClassificationItem(BaseModel):
    """文章分类条目"""
    id: UUID | None = None
    article_id: str
    article_type: ArticleType
    confidence: float
    classified_by: str | None = None
    classified_at: datetime | None = None
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
