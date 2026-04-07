from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class EntityStats:
    """单个数据类型的统计信息"""
    total: int = 0
    today_new: int = 0
    last_crawled_at: datetime | None = None
    freshness_hours: float | None = None  # 距离现在多少小时


@dataclass(slots=True)
class DashboardStats:
    """Dashboard 统计汇总"""
    articles: EntityStats = field(default_factory=EntityStats)
    trades: EntityStats = field(default_factory=EntityStats)
    market_data: EntityStats = field(default_factory=EntityStats)
    generated_at: datetime | None = None


@dataclass(slots=True)
class QualityMetrics:
    """数据质量指标"""
    total_issues: int = 0
    by_severity: dict[str, int] = field(default_factory=dict)  # error/warning/info count
    by_code: dict[str, int] = field(default_factory=dict)     # 各 issue code 数量
    article_dup_count: int = 0
    article_missing_count: int = 0
    market_missing_count: int = 0
    trade_missing_count: int = 0
    anomaly_details: list[dict[str, Any]] = field(default_factory=list)  # 前 N 条详情
    generated_at: datetime | None = None


@dataclass(slots=True)
class DashboardReport:
    """完整的 Dashboard 报告"""
    stats: DashboardStats = field(default_factory=DashboardStats)
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    alerts: list[str] = field(default_factory=list)
    generated_at: datetime | None = None


@dataclass(slots=True)
class QualityTrend:
    """数据质量趋势（过去 N 天）。"""
    days: list[str]  # 日期列表 "YYYY-MM-DD"
    issue_counts: list[int]  # 每日问题数
    anomaly_rates: list[float]  # 每日异常率（%）
    completeness_rates: list[float]  # 每日完整性（%）


@dataclass(slots=True)
class DataSourceFreshness:
    """各数据源的新鲜度。"""
    source: str
    entity_type: str  # article / trade / market
    last_updated: datetime | None
    freshness_hours: float | None
    is_stale: bool  # 是否超过阈值


@dataclass(slots=True)
class TraderStats:
    """交易员级别统计。"""
    trader_id: str
    total_trades: int
    trades_today: int
    unique_symbols: int  # 标的多样性
    hhi: float  # Herfindahl 集中度指数（0=完全分散，1=完全集中）
    buy_ratio: float  # 买入比例 0.0~1.0
    avg_holding_minutes: float | None
    pnl_positive_ratio: float | None  # 盈利交易占比
    alerts: list[str]  # 该交易员的告警
