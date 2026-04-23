"""策略库数据类型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class StrategyVersionStatus(StrEnum):
    """策略版本状态"""
    draft = "draft"
    released = "released"
    archived = "archived"


@dataclass
class StrategyIdea:
    """单个标的的策略想法（未确认状态）"""
    symbol: str  # 标的代码，如 "000001"
    side: str  # BUY / SELL / HOLD
    confidence: float  # 0-1 置信度
    entry_price: float | None = None  # 入场价（可选）
    target_price: float | None = None  # 目标价（可选）
    stop_loss_price: float | None = None  # 止损价（可选）
    rationale: str | None = None  # 理由（可选）
    invalidation: str | None = None  # 失效条件（可选）
    source_article_ids: list[str] = field(default_factory=list)  # 来源文章 ID 列表


@dataclass
class StrategyRecommendation:
    """单个标的的策略建议（已确认，可执行）"""
    symbol: str  # 标的代码
    decision: str  # buy / sell / hold
    confidence: float  # 0-1 置信度
    entry_price: float | None = None  # 入场价（可选）
    target_price: float | None = None  # 目标价（可选）
    stop_loss_price: float | None = None  # 止损价（可选）
    rationale: str | None = None  # 理由（可选）
    evidence_refs: list[str] = field(default_factory=list)  # 证据引用列表


@dataclass(frozen=True)
class StrategyVersion:
    """策略版本聚合（不可变）"""
    version_id: str  # 版本 ID
    trader_id: str  # 交易员 ID
    strategy_date: date  # 策略日期
    status: StrategyVersionStatus  # 版本状态
    recommendations: list[StrategyRecommendation] = field(default_factory=list)  # 建议列表
    source_article_ids: list[str] = field(default_factory=list)  # 来源文章 ID 列表
    evidence_refs: list[str] = field(default_factory=list)  # 证据引用列表
    notes: str | None = None  # 备注（可选）
    released_at: datetime | None = None  # 发布时间（可选）
