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
