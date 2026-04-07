"""
Trading Behavior Classification — 交易行为分类体系。

Schema 版本: v1 (2026-04-07)

行为分类用于从历史交易记录（TradeLog）中识别交易员的行为模式。

分类维度：
  - 时间偏好：开盘/盘中/尾盘
  - 空间偏好：追涨/抄底/突破/震荡
  - 风险偏好：激进/保守
  - 持仓周期：日内/波段/趋势
"""

from __future__ import annotations

from enum import StrEnum


class BehaviorLabel(StrEnum):
    """顶层行为分类标签。"""

    # 追涨类
    CHASE_RALLY = "chase_rally"           # 追涨（突破后追入）
    CHASE_GAP = "chase_gap"               # 追缺口

    # 抄底类
    BOTTOM_FISH = "bottom_fish"            # 抄底（均值回归左侧）
    CATCH_FALLING_KNIFE = "catch_falling_knife"  # 接飞刀（激进抄底）

    # 趋势类
    TREND_FOLLOW = "trend_follow"         # 趋势跟踪
    BREAKOUT = "breakout"                  # 突破交易

    # 震荡类
    RANGE_PLAY = "range_play"              # 区间操作（高抛低吸）
    SCALP = "scalp"                       # scalp / 超短线

    # 套利/对冲类
    ARBITRAGE = "arbitrage"               # 套利
    HEDGE = "hedge"                       # 对冲

    # 风控类
    STOP_LOSS_CUT = "stop_loss_cut"       # 止损
    PROFIT_TAKING = "profit_taking"       # 止盈
    POSITION_ADJUST = "position_adjust"  # 调仓

    # 其他
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Behavior pattern — rule-based scoring
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field


class BehaviorPattern(BaseModel):
    """一个可被识别的行为模式。

    用于识别规则打分。
    """

    label: BehaviorLabel
    confidence: float = Field(ge=0.0, le=1.0)

    # 触发信号（可以是指标名、事件类型等）
    signals: list[str] = Field(default_factory=list)

    # 上下文
    context: str | None = None

    schema_version: str = "v1"


class BehaviorProfile(BaseModel):
    """一个交易员的行为特征画像。

    基于历史 TradeLog 聚合统计生成。
    """

    trader_id: str

    # 各行为标签的出现频率（0.0~1.0）
    label_distribution: dict[str, float] = Field(default_factory=dict)

    # 平均持仓时长（分钟）
    avg_hold_minutes: float | None = None

    # 主要行为标签
    dominant_behavior: BehaviorLabel | None = None

    # 行为标签列表（按频率排序）
    ranked_labels: list[str] = Field(default_factory=list)

    schema_version: str = "v1"


# ---------------------------------------------------------------------------
# 行为分类自动优化监控（P2-008 后续实现）
# ---------------------------------------------------------------------------


class BehaviorStats(BaseModel):
    """行为标签的聚合统计 — 用于监控和优化触发。

    每次 TradeLog 分类后更新，用于：
    - 检测 unknown 率是否过高
    - 发现新的行为模式候选
    - 触发人工审核建议
    """

    trader_id: str | None = None  # None 表示全局统计

    # 各标签出现次数
    label_counts: dict[str, int] = Field(default_factory=dict)

    # 总交易次数
    total_trades: int = 0

    # unknown 标签占比（0.0~1.0）
    unknown_rate: float = 0.0

    # unknown 率是否超过告警阈值（由配置决定）
    unknown_rate_alert: bool = False

    # 新模式候选（UNKNOW 聚集的上下文特征）
    new_pattern_candidates: list[str] = Field(default_factory=list)

    schema_version: str = "v1"


class BehaviorOptimizationAlert(BaseModel):
    """行为分类优化告警 — 触发人工审核。"""

    alert_type: str  # "high_unknown_rate" | "new_pattern_candidate"
    trader_id: str | None = None
    message: str
    unknown_rate: float | None = None
    new_pattern_candidates: list[str] = Field(default_factory=list)
    suggested_label: BehaviorLabel | None = None
    schema_version: str = "v1"
