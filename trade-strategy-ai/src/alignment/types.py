"""
对齐分析框架数据类型 — P3-001~P3-004。

定义核心数据结构和结果类型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from src.persona.behavior import BehaviorLabel


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

@dataclass
class StrategyRule:
    """策略规则。

    表示从文章中提取的交易规则。

    Attributes:
        rule_id: 规则唯一标识
        rule_type: 规则类型（entry/exit/filter/sizing/risk）
        instrument_focus: 标的类型（stock/etf/cb/mixed）
        condition: 条件表达式（dict）
        action: 动作规格
        confidence: 置信度（0-1）
        source_url: 来源文章 URL
    """
    rule_id: str
    rule_type: str
    instrument_focus: str = "mixed"
    condition: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    source_url: str | None = None


@dataclass
class TradeRecord:
    """交易记录。

    表示实际发生的交易。

    Attributes:
        trade_id: 交易唯一标识
        symbol: 标的代码
        side: 方向（buy/sell）
        price: 成交价格
        quantity: 成交数量
        executed_at: 成交时间
        pnl: 盈亏（可选）
        behavior_label: 行为标签
    """
    trade_id: str
    symbol: str
    side: str
    price: float
    quantity: float
    executed_at: datetime
    pnl: float | None = None
    behavior_label: BehaviorLabel | None = None


@dataclass
class BehaviorProfile:
    """交易者行为画像。

    聚合交易记录得到的行为特征。
    """
    trader_id: str
    label_distribution: dict[str, float] = field(default_factory=dict)
    avg_hold_minutes: float | None = None
    win_rate: float = 0.0
    expected_value: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0


# ---------------------------------------------------------------------------
# 评分结果
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    """单条规则与单笔交易的匹配结果。"""
    rule_id: str
    trade_id: str
    matched: bool
    score: float = 0.0  # 0-1，匹配程度
    reason: str = ""


@dataclass
class RuleMatchScore:
    """规则匹配评分结果（P3-001）。"""
    rule_id: str
    # 匹配的交易数量
    matched_trades: int = 0
    # 总交易数量
    total_trades: int = 0
    # 匹配率
    match_rate: float = 0.0
    # 平均匹配分数
    avg_score: float = 0.0
    # 匹配详情
    match_results: list[MatchResult] = field(default_factory=list)


@dataclass
class BehaviorFitScore:
    """行为适配度评分结果（P3-002）。"""
    trader_id: str
    # 行为适配度（0-1）
    fit_score: float = 0.0
    # 各维度分数
    dimension_scores: dict[str, float] = field(default_factory=dict)
    # 差距分析
    gaps: list[str] = field(default_factory=list)


class ConflictType(StrEnum):
    """冲突类型。"""
    # 规则之间的冲突
    RULE_CONTRADICTION = "rule_contradiction"      # 互相排斥的规则
    RULE_OVERLAP = "rule_overlap"                  # 规则重叠
    # 规则与行为的冲突
    BEHAVIOR_DEVIATION = "behavior_deviation"      # 行为偏离规则
    # 参数冲突
    PARAMETER_MISMATCH = "parameter_mismatch"      # 参数不一致
    # 时序冲突
    TEMPORAL_CONFLICT = "temporal_conflict"       # 时序矛盾


@dataclass
class ConflictDetectionResult:
    """冲突检测结果（P3-003）。"""
    conflict_type: ConflictType
    severity: str = "major"  # critical/major/minor
    message: str = ""
    involved_rules: list[str] = field(default_factory=list)
    involved_trades: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictDetection:
    """冲突检测汇总。"""
    trader_id: str
    total_conflicts: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)
    conflicts: list[ConflictDetectionResult] = field(default_factory=list)


@dataclass
class ConfidenceScore:
    """综合可信度评分结果（P3-004）。"""
    trader_id: str
    # 综合可信度（0-1）
    overall_score: float = 0.0
    # 各维度分数
    rule_match_score: float = 0.0
    behavior_fit_score: float = 0.0
    conflict_penalty: float = 0.0  # 冲突扣分
    # 加权明细
    score_breakdown: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 综合报告
# ---------------------------------------------------------------------------

@dataclass
class AlignmentReport:
    """对齐分析综合报告。"""
    trader_id: str
    generated_at: datetime = field(default_factory=datetime.now)

    # 规则匹配
    rule_match_scores: list[RuleMatchScore] = field(default_factory=list)
    overall_rule_match_rate: float = 0.0

    # 行为适配度
    behavior_fit: BehaviorFitScore | None = None

    # 冲突检测
    conflicts: ConflictDetection | None = None

    # 综合可信度
    confidence: ConfidenceScore | None = None

    # 元数据
    rules_analyzed: int = 0
    trades_analyzed: int = 0
