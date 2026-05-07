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


class StrategyVersionType(StrEnum):
    """策略版本类型，区分创建来源

    - manual: 手动创建的初始草稿版本，由 build_and_save_draft() 生成
    - candidate: 优化流程生成的候选版本，由 create_candidate_version() 生成
    """
    manual = "manual"
    candidate = "candidate"


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
    volume: int | None = None  # 建议交易量（股），A股买入需为100的整数倍
    rationale: str | None = None  # 理由（可选）
    evidence_refs: list[str] = field(default_factory=list)  # 证据引用列表


@dataclass(frozen=True)
class StrategyAdjustment:
    """策略调整建议（S7-002/S7-003）。

    由优化流程生成，用于指导候选版本的创建。
    """
    trader_id: str  # 交易员 ID
    rule_id: str  # 规则 ID
    current_status: str  # 当前状态，如 "hit_rate_too_low" / "return_negative"
    suggestion: str  # 调整建议
    confidence: float  # 建议置信度 0-1
    依据: str  # 具体的指标数值依据


@dataclass(frozen=True)
class StrategyVersion:
    """策略版本聚合（不可变）

    版本类型说明：
    - manual (默认): 手动创建的初始草稿，由 build_and_save_draft() 生成
    - candidate: 优化流程生成的候选版本，由 create_candidate_version() 生成，
      需人工 review 后才能通过 release_version() 晋升为 released
    """
    version_id: str  # 版本 ID
    trader_id: str  # 交易员 ID
    strategy_date: date  # 策略日期
    status: StrategyVersionStatus  # 版本状态

    def __post_init__(self) -> None:
        """自动将 strategy_date 的 str 格式转换为 date 对象（兼容 JSON 反序列化）。"""
        if isinstance(self.strategy_date, str):
            object.__setattr__(self, "strategy_date", date.fromisoformat(self.strategy_date))
    version_type: StrategyVersionType = StrategyVersionType.manual  # 版本类型（S7-003 新增）
    parent_version_id: str | None = None  # 父版本 ID，用于候选版本追溯正式版本（S7-003 新增）
    recommendations: list[StrategyRecommendation] = field(default_factory=list)  # 建议列表
    source_article_ids: list[str] = field(default_factory=list)  # 来源文章 ID 列表
    evidence_refs: list[str] = field(default_factory=list)  # 证据引用列表
    notes: str | None = None  # 备注（可选）
    released_at: datetime | None = None  # 发布时间（可选）
    # 版本化规则快照（NTL-S4-003）：用于 StrategyAgent 评估的规则集合
    # 每条规则通常包含 rule_id / condition / action / confidence / rule_pool_id 等字段
    rules_snapshot: list[dict] = field(default_factory=list)
