"""
Strategy Concept Taxonomy — 策略概念分类体系。

Schema 版本: v1 (2026-04-07)

三层分类：
  1. 维度（Dimension）：主动性 / 被动性 / 量态
  2. 类别（Category）：维度下的具体分类
  3. 标签（Tag）：具体概念标签

维度说明：
  - 主动性（Proactive）：交易者主动选择时机/标的，不依赖外部信号触发
  - 被动性（Reactive）：需要特定市场状态或信号才介入
  - 量态（Quantitative）：仓位/资金管理相关的量化维度

---

## ConceptCategory 类别定义

### 主动性维度
  trend_following       趋势跟踪（追涨）
  breakout_chasing      突破追涨
  momentum_playing      动量策略
  opportunistic         机会主义（随机应变）

### 被动性维度
  mean_reversion        均值回归（抄底/摸顶）
  range_bound           区间震荡策略
  event_driven          事件驱动
  signal_dependent     信号依赖（指标触发）

### 量态维度
  position_sizing       仓位管理
  risk_control          风险控制
  capital_allocation    资金分配
  drawdown_protection   回撤保护
"""

from __future__ import annotations

from enum import StrEnum


class ConceptDimension(StrEnum):
    """概念分类的顶层维度。"""
    PROACTIVE = "proactive"       # 主动性
    REACTIVE = "reactive"         # 被动性
    QUANTITATIVE = "quantitative" # 量态


class ConceptCategory(StrEnum):
    """中层分类 — 跨维度复用。"""

    # 主动性
    TREND_FOLLOWING = "trend_following"       # 趋势跟踪
    BREAKOUT_CHASING = "breakout_chasing"     # 突破追涨
    MOMENTUM_PLAYING = "momentum_playing"     # 动量策略
    OPPORTUNISTIC = "opportunistic"           # 机会主义

    # 被动性
    MEAN_REVERSION = "mean_reversion"         # 均值回归
    RANGE_BOUND = "range_bound"               # 区间震荡
    EVENT_DRIVEN = "event_driven"             # 事件驱动
    SIGNAL_DEPENDENT = "signal_dependent"     # 信号依赖

    # 量态
    POSITION_SIZING = "position_sizing"       # 仓位管理
    RISK_CONTROL = "risk_control"             # 风险控制
    CAPITAL_ALLOCATION = "capital_allocation"  # 资金分配
    DRAWDOWN_PROTECTION = "drawdown_protection"  # 回撤保护


# 维度 ↔ 类别映射
DIMENSION_CATEGORIES: dict[ConceptDimension, list[ConceptCategory]] = {
    ConceptDimension.PROACTIVE: [
        ConceptCategory.TREND_FOLLOWING,
        ConceptCategory.BREAKOUT_CHASING,
        ConceptCategory.MOMENTUM_PLAYING,
        ConceptCategory.OPPORTUNISTIC,
    ],
    ConceptDimension.REACTIVE: [
        ConceptCategory.MEAN_REVERSION,
        ConceptCategory.RANGE_BOUND,
        ConceptCategory.EVENT_DRIVEN,
        ConceptCategory.SIGNAL_DEPENDENT,
    ],
    ConceptDimension.QUANTITATIVE: [
        ConceptCategory.POSITION_SIZING,
        ConceptCategory.RISK_CONTROL,
        ConceptCategory.CAPITAL_ALLOCATION,
        ConceptCategory.DRAWDOWN_PROTECTION,
    ],
}


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

from typing import Any

from pydantic import BaseModel, Field


class ConceptTag(BaseModel):
    """一个具体的策略概念标签。"""

    # 标签名称（英文 key）
    tag: str

    # 标签中文描述
    label_zh: str

    # 所属维度
    dimension: ConceptDimension

    # 所属类别
    category: ConceptCategory

    # 扩展元数据
    metadata: dict[str, Any] = Field(default_factory=dict)

    # 置信度（LLM 判定时的置信度）
    confidence: float | None = None

    # 来源证据
    evidence: str | None = None

    # schema 版本
    schema_version: str = "v1"


# ---------------------------------------------------------------------------
# 概念库自动优化监控（P2-002 后续实现）
# ---------------------------------------------------------------------------


class ConceptStats(BaseModel):
    """概念标签的聚合统计 — 用于监控和优化触发。

    每次 LLM 提取后更新，用于：
    - 检测长尾标签（置信度低、出现次数少）
    - 检测类别失衡
    - 触发人工审核建议
    """

    tag: str
    category: ConceptCategory
    dimension: ConceptDimension

    # 提取次数
    total_extractions: int = 0

    # 成功提取次数（LLM 返回该标签）
    successful_extractions: int = 0

    # 平均置信度（加权）
    avg_confidence: float | None = None

    # 最近一次提取时间
    last_seen_at: str | None = None  # ISO datetime

    schema_version: str = "v1"


class ConceptOptimizationAlert(BaseModel):
    """概念库优化告警 — 触发人工审核。"""

    alert_type: str  # "low_confidence_tag" | "new_candidate_tag" | "category_imbalance"
    tag: str | None = None
    message: str
    stats: ConceptStats | None = None
    suggested_category: ConceptCategory | None = None
    suggested_dimension: ConceptDimension | None = None
    schema_version: str = "v1"
