"""
Trading Pattern Library — 交易模式库。

Schema 版本: v1 (2026-04-07)

设计思路：
  - ArticlePattern（主）：从文章提炼，真实交易员正在用的策略模式
  - CanonicalPattern（辅）：教科书经典形态，作为参考对照

数据流：
  BlogArticle
    → LLM 提取 strategy_rules / preconditions
    → ArticlePattern（提炼）
    → Backtest 验证（历史 K 线匹配）
    → ValidatedPattern（有效模式）
         ↓
  CanonicalPattern（教科书参考骨架）
         ↓
  UnifiedPatternLibrary（统一模式库）

---

## ArticlePattern

从文章提炼的交易模式，反映真实交易员的实际操作方法。
来源：LLM 提取 → strategy_rules / preconditions 聚合

## CanonicalPattern

教科书经典 K 线形态，作为参考骨架。
来源：技术分析文献（Edwards & Magee、Bulkowski 等）
用途：对照验证、补充缺失模式

## ValidatedPattern

经过历史 K 线验证有效的 ArticlePattern。
验证条件：
  1. 在历史数据中出现次数 ≥ N（可配置）
  2. 后续收益率符合预期（胜率/盈亏比 ≥ 阈值）
  3. 由人工确认（可选）

---

## 模式结构

每个模式包含：
  - pattern_id: 唯一标识
  - name_zh / name_en: 中英文名称
  - pattern_type: trend_following | reversal | breakout | range | scalp | ...
  - conditions: 触发条件列表（AND 关系）
  - entry_signal: 入场信号描述
  - exit_signal: 出场信号描述
  - stop_loss: 止损规则
  - take_profit: 止盈规则
  - timeframe: 适用周期（intraday / daily / swing）
  - source: article | canonical
  - evidence_refs: 来源证据列表
  - validation_stats: 验证统计（ValidatedPattern 专用）
  - schema_version: v1
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PatternType(StrEnum):
    """模式类型分类。"""

    # 趋势/延续类
    TREND_FOLLOWING = "trend_following"       # 趋势跟踪
    BREAKOUT = "breakout"                    # 突破
    MOMENTUM = "momentum"                    # 动量
    CONTINUATION = "continuation"            # 延续/盘整

    # 反转类
    MEAN_REVERSION = "mean_reversion"       # 均值回归
    REVERSAL = "reversal"                    # 反转
    BOTTOM_FISH = "bottom_fish"             # 抄底

    # 区间类
    RANGE_PLAY = "range_play"               # 区间操作
    SCALP = "scalp"                          # 超短线

    # 形态类（主要用于 CanonicalPattern）
    CHART_PATTERN = "chart_pattern"         # K 线形态

    # 其他
    UNKNOWN = "unknown"


class Timeframe(StrEnum):
    """适用周期。"""
    INTRADAY = "intraday"   # 日内（分钟级）
    DAILY = "daily"         # 日线
    SWING = "swing"         # 波段（2~10 天）
    POSITION = "position"   # 持仓（>10 天）


# ---------------------------------------------------------------------------
# 模式条件 — 描述触发条件的结构化表达
# ---------------------------------------------------------------------------


class Condition(BaseModel):
    """模式触发条件。"""

    field: str  # 如 "close", "volume", "rsi", "ma_20"
    op: str  # "cross_above" | "cross_below" | "gt" | "lt" | "eq" | "in_range"
    value: Any | None = None  # 具体值或引用（可选，描述性条件可为空）

    # 描述文本（人可读）
    description_zh: str | None = None

    schema_version: str = "v1"


# ---------------------------------------------------------------------------
# 模式证据引用
# ---------------------------------------------------------------------------


class EvidenceRef(BaseModel):
    """模式来源证据。"""

    source: str  # "article" | "canonical"
    source_id: str | None = None  # 文章 URL 或书籍名称
    quoted_text: str | None = None  # 原文引用
    author: str | None = None  # 作者/来源
    rule_ref: str | None = None  # 关联的 strategy_rule UUID

    schema_version: str = "v1"


# ---------------------------------------------------------------------------
# 验证统计
# ---------------------------------------------------------------------------


class ValidationStats(BaseModel):
    """模式验证统计。"""

    # 在历史数据中出现次数
    occurrences: int = 0

    # 胜率（收盘价 > 入场价的比例）
    win_rate: float | None = None  # 0.0 ~ 1.0

    # 盈亏比（平均盈利 / 平均亏损）
    profit_loss_ratio: float | None = None

    # 平均持仓时长（bars）
    avg_hold_bars: int | None = None

    # 夏普比
    sharpe_ratio: float | None = None

    # 最大回撤
    max_drawdown: float | None = None

    # 验证时间
    validated_at: datetime | None = None

    # 数据范围（用于追溯）
    data_range_start: str | None = None
    data_range_end: str | None = None

    schema_version: str = "v1"


# ---------------------------------------------------------------------------
# 核心模式模型
# ---------------------------------------------------------------------------


class BasePattern(BaseModel):
    """所有模式的基类。"""

    pattern_id: str = Field(default_factory=lambda: str(uuid4()))
    name_zh: str
    name_en: str
    pattern_type: PatternType
    timeframe: Timeframe = Timeframe.DAILY

    # 触发条件
    conditions: list[Condition] = Field(default_factory=list)

    # 入场/出场信号
    entry_signal: str | None = None  # 人可读描述
    exit_signal: str | None = None
    stop_loss: str | None = None
    take_profit: str | None = None

    # 来源
    source: str  # "article" | "canonical"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    # 描述
    description_zh: str | None = None

    # 置信度（0.0 ~ 1.0）
    confidence: float | None = None

    schema_version: str = "v1"


class ArticlePattern(BasePattern):
    """从文章提炼的交易模式（主来源）。

    来源：LLM 提取 strategy_rules / preconditions → 聚合 → ArticlePattern
    """

    source: str = "article"

    # 提炼来源
    article_ids: list[str] = Field(default_factory=list)  # 来源文章 ID 列表
    extraction_method: str = "llm"  # "llm" | "rule_based"

    # 是否已验证
    is_validated: bool = False
    validation_stats: ValidationStats | None = None

    # 关联的 style_cluster_id（可选）
    style_cluster_id: str | None = None

    schema_version: str = "v1"


class CanonicalPattern(BasePattern):
    """教科书经典形态（辅助参考）。

    来源：技术分析文献（Edwards & Magee、Bulkowski、Kline 等）
    用途：对照验证、补充缺失模式
    """

    source: str = "canonical"

    # 教科书来源
    book_title: str | None = None  # 如 "Technical Analysis of Stock Trends"
    author: str | None = None      # 如 "Edwards & Magee"
    page_ref: str | None = None    # 页码引用

    # 历史验证统计（文献中已有的统计）
    literature_stats: ValidationStats | None = None

    schema_version: str = "v1"


class ValidatedPattern(BasePattern):
    """经过验证有效的 ArticlePattern。

    来源：ArticlePattern + 历史 K 线回测验证
    """

    source: str = "validated"

    # 原始 ArticlePattern ID
    article_pattern_id: str | None = None

    # 验证统计
    validation_stats: ValidationStats

    # 验证方法
    validation_method: str = "backtest"  # "backtest" | "manual" | "both"

    # 人工确认
    human_confirmed: bool = False
    confirmed_by: str | None = None  # 确认人

    schema_version: str = "v1"


# ---------------------------------------------------------------------------
# 统一模式库
# ---------------------------------------------------------------------------


class PatternLibrary(BaseModel):
    """统一模式库容器 — 包含三种来源的模式。"""

    library_id: str
    updated_at: datetime = Field(default_factory=datetime.now)

    # 各来源模式
    article_patterns: list[ArticlePattern] = Field(default_factory=list)
    canonical_patterns: list[CanonicalPattern] = Field(default_factory=list)
    validated_patterns: list[ValidatedPattern] = Field(default_factory=list)

    # 元数据
    total_patterns: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)

    schema_version: str = "v1"
